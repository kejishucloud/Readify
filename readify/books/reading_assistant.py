import json
import time
import logging
from typing import Dict, Any, Optional, List
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from .models import (
    Book, BookContent, ReadingAssistant, ReadingQA, ChapterSummary,
    ReadingTimeTracker, ReadingProgress
)
from readify.ai_services.services import AIService
from readify.user_management.models import UserPreferences

logger = logging.getLogger(__name__)


class ReadingAssistantService:
    """阅读助手服务类"""
    
    def __init__(self, user: User, book: Book):
        self.user = user
        self.book = book
        self.ai_service = AIService(user)
        self.assistant = self._get_or_create_assistant()
    
    def _get_or_create_assistant(self) -> ReadingAssistant:
        """获取或创建阅读助手实例"""
        assistant, created = ReadingAssistant.objects.get_or_create(
            user=self.user,
            book=self.book,
            defaults={
                'session_name': f'{self.book.title} 阅读助手',
                'is_enabled': True,
            }
        )
        
        if created:
            logger.info(f"为用户 {self.user.username} 创建了新的阅读助手: {self.book.title}")
        
        return assistant
    
    def toggle_assistant(self, enabled: bool) -> Dict[str, Any]:
        """启用/禁用AI助手"""
        try:
            self.assistant.is_enabled = enabled
            self.assistant.save()
            
            return {
                'success': True,
                'enabled': enabled,
                'message': f'AI助手已{"启用" if enabled else "禁用"}'
            }
        except Exception as e:
            logger.error(f"切换AI助手状态失败: {str(e)}")
            return {
                'success': False,
                'error': f'操作失败: {str(e)}'
            }
    
    def ask_question(self, question: str, question_type: str = 'text', 
                    selected_text: str = '', chapter_number: int = None,
                    position_start: int = None, position_end: int = None) -> Dict[str, Any]:
        """向AI助手提问"""
        if not self.assistant.is_enabled:
            return {
                'success': False,
                'error': 'AI助手未启用'
            }
        
        try:
            start_time = time.time()
            
            # 构建上下文
            context = self._build_context(question_type, selected_text, chapter_number)
            
            # 构建提示词
            prompt = self._build_question_prompt(question, question_type, selected_text, context)
            
            # 调用AI服务
            ai_response = self.ai_service._make_api_request(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self._get_system_prompt()
            )
            
            if not ai_response['success']:
                return ai_response
            
            processing_time = time.time() - start_time
            
            # 保存问答记录
            qa_record = ReadingQA.objects.create(
                assistant=self.assistant,
                question_type=question_type,
                question=question,
                selected_text=selected_text,
                chapter_number=chapter_number,
                position_start=position_start,
                position_end=position_end,
                answer=ai_response['content'],
                context_used=context[:1000],  # 限制长度
                ai_model_used=self.ai_service.config['model_id'],
                processing_time=processing_time,
                tokens_used=ai_response.get('tokens_used', 0)
            )
            
            # 更新助手活跃时间
            self.assistant.update_activity()
            
            # 更新上下文记忆
            self._update_context_memory(question, ai_response['content'])
            
            return {
                'success': True,
                'answer': ai_response['content'],
                'qa_id': qa_record.id,
                'processing_time': processing_time,
                'tokens_used': ai_response.get('tokens_used', 0)
            }
            
        except Exception as e:
            logger.error(f"AI问答失败: {str(e)}")
            return {
                'success': False,
                'error': f'问答失败: {str(e)}'
            }
    
    def generate_chapter_summary(self, chapter_number: int, 
                               summary_type: str = 'auto') -> Dict[str, Any]:
        """生成章节总结"""
        try:
            # 检查是否已存在总结
            existing_summary = ChapterSummary.objects.filter(
                book=self.book,
                chapter_number=chapter_number,
                summary_type=summary_type
            ).first()
            
            if existing_summary:
                return {
                    'success': True,
                    'summary': existing_summary.summary_content,
                    'key_points': existing_summary.key_points,
                    'summary_id': existing_summary.id,
                    'cached': True
                }
            
            # 获取章节内容
            chapter_content = self._get_chapter_content(chapter_number)
            if not chapter_content:
                return {
                    'success': False,
                    'error': f'未找到第{chapter_number}章内容'
                }
            
            # 构建总结提示词
            prompt = self._build_summary_prompt(chapter_content, summary_type)
            
            # 调用AI服务
            ai_response = self.ai_service._make_api_request(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一个专业的文本总结助手，擅长提取关键信息和要点。"
            )
            
            if not ai_response['success']:
                return ai_response
            
            # 解析AI响应，提取总结和关键点
            summary_data = self._parse_summary_response(ai_response['content'])
            
            # 保存总结
            chapter_summary = ChapterSummary.objects.create(
                book=self.book,
                chapter_number=chapter_number,
                chapter_title=chapter_content.get('title', f'第{chapter_number}章'),
                summary_type=summary_type,
                summary_content=summary_data['summary'],
                key_points=summary_data['key_points'],
                word_count=len(summary_data['summary']),
                original_word_count=len(chapter_content['content']),
                ai_model_used=self.ai_service.config['model_id'],
                created_by=self.user
            )
            
            # 计算压缩比
            chapter_summary.calculate_compression_ratio()
            chapter_summary.save()
            
            return {
                'success': True,
                'summary': summary_data['summary'],
                'key_points': summary_data['key_points'],
                'summary_id': chapter_summary.id,
                'compression_ratio': chapter_summary.compression_ratio,
                'cached': False
            }
            
        except Exception as e:
            logger.error(f"生成章节总结失败: {str(e)}")
            return {
                'success': False,
                'error': f'生成总结失败: {str(e)}'
            }
    
    def start_reading_session(self, chapter_number: int) -> Dict[str, Any]:
        """开始阅读会话"""
        try:
            # 结束之前的活跃会话
            ReadingTimeTracker.objects.filter(
                user=self.user,
                book=self.book,
                is_active=True
            ).update(is_active=False)
            
            # 创建新的阅读追踪
            tracker = ReadingTimeTracker.objects.create(
                user=self.user,
                book=self.book,
                chapter_number=chapter_number
            )
            
            # 更新阅读进度
            progress, created = ReadingProgress.objects.get_or_create(
                user=self.user,
                book=self.book,
                defaults={'current_chapter': chapter_number}
            )
            
            if not created and progress.current_chapter != chapter_number:
                progress.current_chapter = chapter_number
                progress.last_read_at = timezone.now()
                progress.save()
            
            # 更新助手状态
            self.assistant.current_chapter = chapter_number
            self.assistant.status = 'active'
            self.assistant.save()
            
            return {
                'success': True,
                'tracker_id': tracker.id,
                'chapter_number': chapter_number,
                'message': f'开始阅读第{chapter_number}章'
            }
            
        except Exception as e:
            logger.error(f"开始阅读会话失败: {str(e)}")
            return {
                'success': False,
                'error': f'开始阅读失败: {str(e)}'
            }
    
    def end_reading_session(self, tracker_id: int, words_read: int = 0) -> Dict[str, Any]:
        """结束阅读会话"""
        try:
            tracker = ReadingTimeTracker.objects.get(
                id=tracker_id,
                user=self.user,
                is_active=True
            )
            
            tracker.words_read = words_read
            tracker.end_tracking()
            
            # 更新阅读进度
            progress = ReadingProgress.objects.get(user=self.user, book=self.book)
            progress.reading_time += tracker.duration_seconds
            progress.save()
            
            # 检查是否需要自动生成章节总结
            if self.assistant.auto_summary:
                self.generate_chapter_summary(tracker.chapter_number)
            
            return {
                'success': True,
                'duration': tracker.duration_seconds,
                'words_read': words_read,
                'reading_speed': tracker.reading_speed,
                'message': f'阅读会话结束，用时{tracker.duration_seconds}秒'
            }
            
        except ReadingTimeTracker.DoesNotExist:
            return {
                'success': False,
                'error': '未找到活跃的阅读会话'
            }
        except Exception as e:
            logger.error(f"结束阅读会话失败: {str(e)}")
            return {
                'success': False,
                'error': f'结束阅读失败: {str(e)}'
            }
    
    def get_reading_statistics(self) -> Dict[str, Any]:
        """获取阅读统计"""
        try:
            # 获取总阅读时间
            total_time = ReadingTimeTracker.objects.filter(
                user=self.user,
                book=self.book
            ).aggregate(
                total_seconds=models.Sum('duration_seconds'),
                total_words=models.Sum('words_read'),
                session_count=models.Count('id')
            )
            
            # 获取阅读进度
            progress = ReadingProgress.objects.filter(
                user=self.user,
                book=self.book
            ).first()
            
            # 获取问答统计
            qa_stats = ReadingQA.objects.filter(
                assistant=self.assistant
            ).aggregate(
                total_questions=models.Count('id'),
                helpful_answers=models.Count('id', filter=models.Q(is_helpful=True))
            )
            
            # 计算平均阅读速度
            avg_speed = 0
            if total_time['total_seconds'] and total_time['total_words']:
                avg_speed = (total_time['total_words'] / total_time['total_seconds']) * 60
            
            return {
                'success': True,
                'statistics': {
                    'total_reading_time': total_time['total_seconds'] or 0,
                    'total_words_read': total_time['total_words'] or 0,
                    'session_count': total_time['session_count'] or 0,
                    'average_reading_speed': round(avg_speed, 2),
                    'current_chapter': progress.current_chapter if progress else 1,
                    'progress_percentage': progress.progress_percentage if progress else 0,
                    'total_questions': qa_stats['total_questions'] or 0,
                    'helpful_answers': qa_stats['helpful_answers'] or 0,
                }
            }
            
        except Exception as e:
            logger.error(f"获取阅读统计失败: {str(e)}")
            return {
                'success': False,
                'error': f'获取统计失败: {str(e)}'
            }
    
    def _build_context(self, question_type: str, selected_text: str, 
                      chapter_number: int) -> str:
        """构建问答上下文"""
        context_parts = []
        
        # 添加书籍基本信息
        context_parts.append(f"书名：{self.book.title}")
        if self.book.author:
            context_parts.append(f"作者：{self.book.author}")
        
        # 根据问题类型添加相关内容
        if question_type == 'chapter' and chapter_number:
            chapter_content = self._get_chapter_content(chapter_number)
            if chapter_content:
                context_parts.append(f"第{chapter_number}章内容：\n{chapter_content['content'][:2000]}")
        
        elif question_type == 'text' and selected_text:
            context_parts.append(f"选中文本：\n{selected_text}")
            
        elif question_type == 'book':
            # 添加书籍摘要
            if self.book.summary:
                context_parts.append(f"书籍摘要：\n{self.book.summary}")
        
        # 添加上下文记忆
        if self.assistant.context_memory:
            memory_items = list(self.assistant.context_memory.items())[-3:]  # 最近3条
            if memory_items:
                context_parts.append("最近的对话记录：")
                for q, a in memory_items:
                    context_parts.append(f"Q: {q[:100]}...")
                    context_parts.append(f"A: {a[:200]}...")
        
        return "\n\n".join(context_parts)
    
    def _build_question_prompt(self, question: str, question_type: str, 
                             selected_text: str, context: str) -> str:
        """构建问题提示词"""
        prompt_parts = []
        
        # 添加上下文
        if context:
            prompt_parts.append(f"上下文信息：\n{context}")
        
        # 根据问题类型添加特定指导
        type_instructions = {
            'text': '请基于选中的文本回答问题，如果文本内容不足以回答问题，请说明需要更多信息。',
            'paragraph': '请分析这个段落的内容，提供详细的解释和分析。',
            'chapter': '请基于整个章节的内容回答问题，可以引用具体的段落或句子。',
            'book': '请基于整本书的内容回答问题，可以跨章节进行分析和总结。',
            'concept': '请详细解释这个概念，包括定义、特点、应用等方面。',
            'summary': '请对指定的内容进行总结，突出关键要点。'
        }
        
        instruction = type_instructions.get(question_type, '请回答以下问题：')
        prompt_parts.append(instruction)
        
        # 添加问题
        prompt_parts.append(f"问题：{question}")
        
        # 添加回答要求
        prompt_parts.append("\n请用中文回答，回答要准确、清晰、有条理。如果无法确定答案，请诚实说明。")
        
        return "\n\n".join(prompt_parts)
    
    def _build_summary_prompt(self, chapter_content: Dict[str, str], 
                            summary_type: str) -> str:
        """构建总结提示词"""
        content = chapter_content['content']
        title = chapter_content.get('title', '章节')
        
        type_instructions = {
            'auto': '请对以下章节内容进行简洁的总结，突出主要观点和关键信息。',
            'key_points': '请提取以下章节内容的关键要点，以条目形式列出。',
            'detailed': '请对以下章节内容进行详细的总结和分析，包括主要观点、论证过程和结论。'
        }
        
        instruction = type_instructions.get(summary_type, type_instructions['auto'])
        
        prompt = f"""
{instruction}

章节标题：{title}

章节内容：
{content}

请按以下格式回答：
总结：[章节总结内容]

关键要点：
1. [要点1]
2. [要点2]
3. [要点3]
...

请确保总结准确、简洁、有条理。
"""
        return prompt
    
    def _parse_summary_response(self, response: str) -> Dict[str, Any]:
        """解析总结响应"""
        lines = response.strip().split('\n')
        summary = ""
        key_points = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('总结：'):
                current_section = 'summary'
                summary = line[3:].strip()
            elif line.startswith('关键要点：'):
                current_section = 'key_points'
            elif current_section == 'summary':
                summary += " " + line
            elif current_section == 'key_points' and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '-', '•'))):
                # 移除序号和符号
                point = line.lstrip('123456789.-• ').strip()
                if point:
                    key_points.append(point)
        
        return {
            'summary': summary.strip(),
            'key_points': key_points
        }
    
    def _get_chapter_content(self, chapter_number: int) -> Optional[Dict[str, str]]:
        """获取章节内容"""
        try:
            chapter = BookContent.objects.get(
                book=self.book,
                chapter_number=chapter_number
            )
            return {
                'title': chapter.chapter_title,
                'content': chapter.content
            }
        except BookContent.DoesNotExist:
            return None
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return f"""你是一个专业的阅读助手，正在帮助用户阅读《{self.book.title}》这本书。

你的职责包括：
1. 回答用户关于书籍内容的问题
2. 解释难懂的概念和术语
3. 提供章节总结和要点提取
4. 帮助用户更好地理解和记忆书籍内容

请遵循以下原则：
- 回答要准确、客观、有帮助
- 基于提供的上下文信息回答问题
- 如果信息不足，请诚实说明
- 使用简洁清晰的中文表达
- 适当引用原文支持你的回答
"""
    
    def _update_context_memory(self, question: str, answer: str):
        """更新上下文记忆"""
        try:
            if not self.assistant.context_memory:
                self.assistant.context_memory = {}
            
            # 限制记忆条数，保留最近的10条
            memory = self.assistant.context_memory
            if len(memory) >= 10:
                # 删除最旧的记录
                oldest_key = list(memory.keys())[0]
                del memory[oldest_key]
            
            # 添加新记录
            timestamp = timezone.now().isoformat()
            memory[f"{timestamp}_{question[:50]}"] = {
                'question': question,
                'answer': answer[:500],  # 限制答案长度
                'timestamp': timestamp
            }
            
            self.assistant.context_memory = memory
            self.assistant.save()
            
        except Exception as e:
            logger.error(f"更新上下文记忆失败: {str(e)}")


# 导入Django模型相关
from django.db import models
from django.db.models import Sum, Count, Q 