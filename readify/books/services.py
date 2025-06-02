import os
import zipfile
import logging
import mimetypes
from typing import List, Dict, Any, Optional
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta, date
from django.db.models import Sum, Count, Avg, Q

from .models import Book, BookCategory, BatchUpload, BookContent, ReadingSession, ReadingStatistics, ReadingProgress, BookNote, NoteCollection, ParagraphSummary, BookSummary
from readify.ai_services.services import AIService
import calendar

logger = logging.getLogger(__name__)


class BookProcessingService:
    """书籍处理服务"""
    
    SUPPORTED_FORMATS = ['.pdf', '.epub', '.mobi', '.txt', '.docx', '.doc']
    
    def __init__(self, user):
        self.user = user
        self.ai_service = AIService(user=user)
    
    def process_batch_upload(self, files: List, batch_name: str = None) -> BatchUpload:
        """处理批量上传"""
        if not batch_name:
            batch_name = f"批量上传_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建批量上传记录
        batch_upload = BatchUpload.objects.create(
            user=self.user,
            upload_name=batch_name,
            total_files=len(files),
            status='processing'
        )
        
        successful_books = []
        errors = []
        
        for file in files:
            try:
                # 检查文件格式
                if not self._is_supported_format(file.name):
                    errors.append(f"不支持的文件格式: {file.name}")
                    batch_upload.failed_files += 1
                    continue
                
                # 处理单个文件
                book = self._process_single_file(file, batch_upload)
                if book:
                    successful_books.append(book)
                    batch_upload.successful_files += 1
                else:
                    batch_upload.failed_files += 1
                
                batch_upload.processed_files += 1
                batch_upload.save()
                
            except Exception as e:
                logger.error(f"处理文件 {file.name} 失败: {str(e)}")
                errors.append(f"处理文件 {file.name} 失败: {str(e)}")
                batch_upload.failed_files += 1
                batch_upload.processed_files += 1
                batch_upload.save()
        
        # 更新批量上传状态
        if batch_upload.failed_files == 0:
            batch_upload.status = 'completed'
        elif batch_upload.successful_files == 0:
            batch_upload.status = 'failed'
        else:
            batch_upload.status = 'partial'
        
        batch_upload.error_log = '\n'.join(errors)
        batch_upload.completed_at = timezone.now()
        batch_upload.save()
        
        # 异步处理AI分类
        self._process_ai_classification_batch(successful_books)
        
        return batch_upload
    
    def _process_single_file(self, file, batch_upload: BatchUpload) -> Optional[Book]:
        """处理单个文件"""
        try:
            # 提取基本信息
            title = self._extract_title_from_filename(file.name)
            file_ext = os.path.splitext(file.name)[1].lower()
            
            # 创建书籍记录
            book = Book.objects.create(
                user=self.user,
                title=title,
                file=file,
                file_size=file.size,
                format=file_ext.replace('.', ''),  # 移除点号
                processing_status='pending'
            )
            
            # 提取文本内容
            content = self._extract_text_content(book)
            if content:
                # 创建书籍内容记录
                BookContent.objects.create(
                    book=book,
                    chapter_number=1,
                    chapter_title="全文内容",
                    content=content[:50000],  # 限制长度
                    word_count=len(content)
                )
                
                book.word_count = len(content)
                book.save()
            
            return book
            
        except Exception as e:
            logger.error(f"处理单个文件失败: {str(e)}")
            return None
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """从文件名提取标题"""
        # 移除扩展名
        title = os.path.splitext(filename)[0]
        
        # 清理常见的文件名模式
        title = title.replace('_', ' ').replace('-', ' ')
        
        # 移除常见的后缀
        suffixes = ['电子书', 'ebook', 'book', '完整版', '高清版', 'PDF', 'pdf']
        for suffix in suffixes:
            title = title.replace(suffix, '').strip()
        
        return title or filename
    
    def _extract_text_content(self, book: Book) -> str:
        """提取文本内容"""
        try:
            file_path = book.file.path
            file_ext = book.get_file_extension()
            
            if file_ext == '.txt':
                return self._extract_from_txt(file_path)
            elif file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext in ['.epub', '.mobi']:
                return self._extract_from_ebook(file_path)
            elif file_ext in ['.doc', '.docx']:
                return self._extract_from_word(file_path)
            else:
                return ""
                
        except Exception as e:
            logger.error(f"提取文本内容失败: {str(e)}")
            return ""
    
    def _extract_from_txt(self, file_path: str) -> str:
        """从TXT文件提取内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except:
                    continue
        return ""
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """从PDF文件提取内容"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            logger.warning("PyPDF2未安装，无法处理PDF文件")
            return ""
        except Exception as e:
            logger.error(f"PDF提取失败: {str(e)}")
            return ""
    
    def _extract_from_ebook(self, file_path: str) -> str:
        """从电子书文件提取内容"""
        try:
            import ebooklib
            from ebooklib import epub
            from bs4 import BeautifulSoup
            
            book = epub.read_epub(file_path)
            text = ""
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text += soup.get_text() + "\n"
            
            return text
        except ImportError:
            logger.warning("ebooklib未安装，无法处理EPUB文件")
            return ""
        except Exception as e:
            logger.error(f"电子书提取失败: {str(e)}")
            return ""
    
    def _extract_from_word(self, file_path: str) -> str:
        """从Word文件提取内容"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            logger.warning("python-docx未安装，无法处理Word文件")
            return ""
        except Exception as e:
            logger.error(f"Word提取失败: {str(e)}")
            return ""
    
    def _is_supported_format(self, filename: str) -> bool:
        """检查是否为支持的文件格式"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.SUPPORTED_FORMATS
    
    def _process_ai_classification_batch(self, books: List[Book]):
        """批量处理AI分类"""
        for book in books:
            try:
                self.classify_book_with_ai(book)
            except Exception as e:
                logger.error(f"AI分类失败 {book.title}: {str(e)}")
    
    def classify_book_with_ai(self, book: Book) -> Dict[str, Any]:
        """使用AI对书籍进行分类"""
        try:
            # 获取书籍内容
            content = self._get_book_text_for_classification(book)
            if not content:
                return {'success': False, 'error': '无法获取书籍内容'}
            
            # 构建分类提示
            categories = BookCategory.CATEGORY_TYPES
            category_list = [f"{code}: {name}" for code, name in categories]
            category_text = "\n".join(category_list)
            
            prompt = f"""
请根据以下书籍信息，将其分类到最合适的学科领域。

书名：{book.title}
作者：{book.author or '未知'}
内容摘要：{content[:2000]}

可选分类：
{category_text}

请返回JSON格式的结果，包含以下字段：
- category_code: 分类代码
- confidence: 置信度(0-1)
- reason: 分类理由
- keywords: 提取的关键词列表
- summary: 书籍简要摘要

示例格式：
{{
    "category_code": "computer",
    "confidence": 0.95,
    "reason": "这是一本关于计算机科学的技术书籍",
    "keywords": ["编程", "算法", "数据结构"],
    "summary": "这本书介绍了..."
}}
"""
            
            # 调用AI服务
            result = self.ai_service._make_api_request(
                [{"role": "user", "content": prompt}],
                "你是一个专业的图书分类专家，能够准确识别书籍的学科领域和主题。"
            )
            
            if result['success']:
                # 解析AI响应
                import json
                try:
                    ai_result = json.loads(result['content'])
                    
                    # 更新书籍信息
                    category_code = ai_result.get('category_code')
                    if category_code:
                        try:
                            category = BookCategory.objects.get(code=category_code)
                            book.category = category
                        except BookCategory.DoesNotExist:
                            # 如果分类不存在，创建一个
                            category_name = dict(categories).get(category_code, category_code)
                            category, created = BookCategory.objects.get_or_create(
                                code=category_code,
                                defaults={'name': category_name}
                            )
                            book.category = category
                    
                    book.summary = ai_result.get('summary', '')
                    book.keywords = ai_result.get('keywords', [])
                    book.processing_status = 'completed'
                    book.save()
                    
                    return {
                        'success': True,
                        'category': category_code,
                        'confidence': ai_result.get('confidence', 0.0),
                        'summary': ai_result.get('summary', '')
                    }
                    
                except json.JSONDecodeError:
                    # 如果JSON解析失败，尝试简单的文本解析
                    content = result['content']
                    book.summary = content[:500]
                    book.processing_status = 'completed'
                    book.save()
                    
                    return {
                        'success': True,
                        'summary': content[:500]
                    }
            else:
                book.processing_status = 'failed'
                book.save()
                return result
                
        except Exception as e:
            logger.error(f"AI分类失败: {str(e)}")
            book.processing_status = 'failed'
            book.save()
            return {'success': False, 'error': str(e)}
    
    def _get_book_text_for_classification(self, book: Book) -> str:
        """获取用于分类的书籍文本"""
        try:
            # 优先使用书籍内容
            content = BookContent.objects.filter(book=book).first()
            if content:
                return content.content[:3000]  # 限制长度
            
            # 如果没有内容，使用书籍描述和标题
            text = f"书名：{book.title}\n"
            if book.author:
                text += f"作者：{book.author}\n"
            if book.description:
                text += f"描述：{book.description}\n"
            
            return text
            
        except Exception as e:
            logger.error(f"获取书籍文本失败: {str(e)}")
            return f"书名：{book.title}"


class CategoryService:
    """分类服务"""
    
    @staticmethod
    def initialize_default_categories():
        """初始化默认分类"""
        categories = BookCategory.CATEGORY_TYPES
        
        for code, name in categories:
            BookCategory.objects.get_or_create(
                code=code,
                defaults={'name': name}
            )
    
    @staticmethod
    def get_category_statistics(user=None):
        """获取分类统计"""
        from django.db.models import Count
        
        query = Book.objects.all()
        if user:
            query = query.filter(user=user)
        
        stats = query.values('category__code', 'category__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(stats)
    
    @staticmethod
    def get_books_by_category(category_code: str, user=None):
        """根据分类获取书籍"""
        query = Book.objects.filter(category__code=category_code)
        if user:
            query = query.filter(user=user)
        
        return query.order_by('-uploaded_at')


class ReadingStatisticsService:
    """阅读统计服务"""
    
    @staticmethod
    def start_reading_session(user, book, chapter_number=None):
        """开始阅读会话"""
        # 结束之前的活跃会话
        ReadingSession.objects.filter(
            user=user, 
            is_active=True
        ).update(
            end_time=timezone.now(),
            is_active=False
        )
        
        # 创建新会话
        session = ReadingSession.objects.create(
            user=user,
            book=book,
            chapter_number=chapter_number
        )
        return session
    
    @staticmethod
    def end_reading_session(user, book=None):
        """结束阅读会话"""
        query = Q(user=user, is_active=True)
        if book:
            query &= Q(book=book)
            
        sessions = ReadingSession.objects.filter(query)
        for session in sessions:
            session.end_session()
        
        return sessions.count()
    
    @staticmethod
    def get_reading_time_stats(user, period_type='daily', start_date=None, end_date=None):
        """获取阅读时间统计"""
        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date
            
        # 根据周期类型调整日期范围
        if period_type == 'weekly':
            start_date = start_date - timedelta(days=start_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif period_type == 'monthly':
            start_date = start_date.replace(day=1)
            end_date = start_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        elif period_type == 'yearly':
            start_date = start_date.replace(month=1, day=1)
            end_date = start_date.replace(month=12, day=31)
        
        # 查询阅读会话
        sessions = ReadingSession.objects.filter(
            user=user,
            start_time__date__range=[start_date, end_date],
            end_time__isnull=False
        )
        
        # 计算统计数据
        total_time = sessions.aggregate(
            total=Sum('duration_seconds')
        )['total'] or 0
        
        books_read = sessions.values('book').distinct().count()
        sessions_count = sessions.count()
        avg_session_time = sessions.aggregate(
            avg=Avg('duration_seconds')
        )['avg'] or 0
        
        return {
            'period_type': period_type,
            'start_date': start_date,
            'end_date': end_date,
            'total_reading_time': total_time,
            'books_read': books_read,
            'sessions_count': sessions_count,
            'average_session_time': int(avg_session_time),
            'formatted_time': ReadingStatisticsService.format_duration(total_time)
        }
    
    @staticmethod
    def format_duration(seconds):
        """格式化时长显示"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}小时{minutes}分钟"
    
    @staticmethod
    def get_reading_trends(user, days=30):
        """获取阅读趋势数据"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # 按日期分组统计
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            sessions = ReadingSession.objects.filter(
                user=user,
                start_time__date=current_date,
                end_time__isnull=False
            )
            
            total_time = sessions.aggregate(
                total=Sum('duration_seconds')
            )['total'] or 0
            
            daily_stats.append({
                'date': current_date,
                'reading_time': total_time,
                'sessions_count': sessions.count(),
                'books_count': sessions.values('book').distinct().count()
            })
            
            current_date += timedelta(days=1)
        
        return daily_stats
    
    @staticmethod
    def update_reading_statistics(user):
        """更新用户阅读统计"""
        today = timezone.now().date()
        
        # 更新各个周期的统计
        periods = [
            ('daily', today, today),
            ('weekly', today - timedelta(days=today.weekday()), 
             today - timedelta(days=today.weekday()) + timedelta(days=6)),
            ('monthly', today.replace(day=1), 
             today.replace(day=calendar.monthrange(today.year, today.month)[1])),
            ('yearly', today.replace(month=1, day=1), 
             today.replace(month=12, day=31))
        ]
        
        for period_type, start_date, end_date in periods:
            stats_data = ReadingStatisticsService.get_reading_time_stats(
                user, period_type, start_date, end_date
            )
            
            ReadingStatistics.objects.update_or_create(
                user=user,
                period_type=period_type,
                period_start=start_date,
                defaults={
                    'period_end': end_date,
                    'total_reading_time': stats_data['total_reading_time'],
                    'books_read': stats_data['books_read'],
                    'sessions_count': stats_data['sessions_count'],
                    'average_session_time': stats_data['average_session_time']
                }
            )


class BookNoteService:
    """书籍笔记服务"""
    
    @staticmethod
    def create_note(user, book, chapter_number, position_start, position_end, 
                   selected_text, note_content='', note_type='note', color='yellow', tags=''):
        """创建笔记"""
        note = BookNote.objects.create(
            user=user,
            book=book,
            chapter_number=chapter_number,
            position_start=position_start,
            position_end=position_end,
            selected_text=selected_text,
            note_content=note_content,
            note_type=note_type,
            color=color,
            tags=tags
        )
        return note
    
    @staticmethod
    def get_book_notes(user, book, note_type=None, chapter_number=None):
        """获取书籍笔记"""
        query = Q(user=user, book=book)
        
        if note_type:
            query &= Q(note_type=note_type)
        if chapter_number is not None:
            query &= Q(chapter_number=chapter_number)
        
        return BookNote.objects.filter(query).order_by('chapter_number', 'position_start')
    
    @staticmethod
    def search_notes(user, keyword, book=None):
        """搜索笔记"""
        query = Q(user=user) & (
            Q(note_content__icontains=keyword) | 
            Q(selected_text__icontains=keyword) |
            Q(tags__icontains=keyword)
        )
        
        if book:
            query &= Q(book=book)
        
        return BookNote.objects.filter(query).order_by('-created_at')
    
    @staticmethod
    def create_note_collection(user, name, description='', note_ids=None):
        """创建笔记集合"""
        collection = NoteCollection.objects.create(
            user=user,
            name=name,
            description=description
        )
        
        if note_ids:
            notes = BookNote.objects.filter(id__in=note_ids, user=user)
            collection.notes.set(notes)
        
        return collection
    
    @staticmethod
    def export_notes(user, book=None, format='json'):
        """导出笔记"""
        query = Q(user=user)
        if book:
            query &= Q(book=book)
        
        notes = BookNote.objects.filter(query).select_related('book')
        
        if format == 'json':
            return [
                {
                    'book_title': note.book.title,
                    'chapter_number': note.chapter_number,
                    'selected_text': note.selected_text,
                    'note_content': note.note_content,
                    'note_type': note.note_type,
                    'color': note.color,
                    'tags': note.tags,
                    'created_at': note.created_at.isoformat()
                }
                for note in notes
            ]
        
        return notes


class AISummaryService:
    """AI总结服务"""
    
    @staticmethod
    def create_paragraph_summary(book, chapter_number, paragraph_start, paragraph_end, 
                               original_text, summary_type='brief'):
        """创建段落总结"""
        from readify.ai_services.services import AIService
        
        # 调用AI服务生成总结
        prompt = f"""
        请对以下段落进行{summary_type}总结：
        
        原文：
        {original_text}
        
        要求：
        - 保持原文的核心意思
        - 语言简洁明了
        - 突出重点信息
        """
        
        ai_response = AIService.generate_summary(prompt)
        
        summary = ParagraphSummary.objects.create(
            book=book,
            chapter_number=chapter_number,
            paragraph_start=paragraph_start,
            paragraph_end=paragraph_end,
            original_text=original_text,
            summary_text=ai_response.get('summary', ''),
            summary_type=summary_type,
            ai_model_used=ai_response.get('model', '')
        )
        
        return summary
    
    @staticmethod
    def create_book_summary(book, summary_type='overview', user=None):
        """创建全书总结"""
        from readify.ai_services.services import AIService
        
        # 获取书籍内容
        contents = book.contents.all().order_by('chapter_number')
        
        if summary_type == 'overview':
            # 概览总结
            full_text = '\n\n'.join([content.content for content in contents[:5]])  # 前5章
            prompt = f"""
            请为《{book.title}》这本书写一个概览总结。
            
            书籍信息：
            - 作者：{book.author}
            - 描述：{book.description}
            
            部分内容：
            {full_text[:5000]}...
            
            要求：
            1. 总结书籍的主要内容和观点
            2. 提取核心主题和关键信息
            3. 分析书籍的价值和意义
            4. 字数控制在500-800字
            """
            
        elif summary_type == 'chapter_wise':
            # 分章总结
            chapter_summaries = []
            for content in contents:
                chapter_prompt = f"""
                请总结第{content.chapter_number}章的主要内容：
                
                章节标题：{content.chapter_title}
                内容：{content.content[:2000]}...
                
                要求：简洁明了，突出重点，100-200字。
                """
                chapter_summary = AIService.generate_summary(chapter_prompt)
                chapter_summaries.append(f"第{content.chapter_number}章：{chapter_summary.get('summary', '')}")
            
            prompt = f"""
            基于以下各章节总结，为《{book.title}》生成完整的分章总结：
            
            {chr(10).join(chapter_summaries)}
            
            要求：
            1. 整合各章节内容
            2. 突出章节间的逻辑关系
            3. 提供整体结构分析
            """
        
        elif summary_type == 'thematic':
            # 主题总结
            full_text = '\n'.join([content.content for content in contents])
            prompt = f"""
            请对《{book.title}》进行主题分析和总结：
            
            内容：{full_text[:8000]}...
            
            要求：
            1. 识别书籍的主要主题
            2. 分析各主题的内容和观点
            3. 探讨主题间的关联性
            4. 提供深度见解
            """
        
        elif summary_type == 'key_insights':
            # 核心洞察
            full_text = '\n'.join([content.content for content in contents])
            prompt = f"""
            请提取《{book.title}》的核心洞察和要点：
            
            内容：{full_text[:8000]}...
            
            要求：
            1. 提取最重要的观点和结论
            2. 分析作者的核心思想
            3. 总结可行动的建议
            4. 突出独特见解
            """
        
        # 调用AI服务
        ai_response = AIService.generate_summary(prompt)
        
        # 提取关键要点和主题
        key_points = AIService.extract_key_points(ai_response.get('summary', ''))
        themes = AIService.extract_themes(ai_response.get('summary', ''))
        
        summary = BookSummary.objects.create(
            book=book,
            summary_type=summary_type,
            title=f"《{book.title}》{dict(BookSummary.SUMMARY_TYPES)[summary_type]}",
            content=ai_response.get('summary', ''),
            key_points=key_points,
            themes=themes,
            word_count=len(ai_response.get('summary', '')),
            ai_model_used=ai_response.get('model', ''),
            created_by=user
        )
        
        return summary
    
    @staticmethod
    def get_book_summaries(book, summary_type=None):
        """获取书籍总结"""
        query = Q(book=book)
        if summary_type:
            query &= Q(summary_type=summary_type)
        
        return BookSummary.objects.filter(query).order_by('-created_at')
    
    @staticmethod
    def get_paragraph_summaries(book, chapter_number=None):
        """获取段落总结"""
        query = Q(book=book)
        if chapter_number is not None:
            query &= Q(chapter_number=chapter_number)
        
        return ParagraphSummary.objects.filter(query).order_by('chapter_number', 'paragraph_start') 