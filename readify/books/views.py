from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import models
import os
import logging
from datetime import timedelta

from .models import Book, BookContent, ReadingProgress, BookNote, BookQuestion, BookCategory, BatchUpload, ReadingSession, ReadingStatistics, NoteCollection, ParagraphSummary, BookSummary, ReadingAssistant, ReadingQA, ChapterSummary, ReadingTimeTracker
from .services import BookProcessingService, CategoryService, ReadingStatisticsService, BookNoteService, AISummaryService
from .reading_assistant import ReadingAssistantService
from .renderers import OptimizedBookRenderer, RendererFactory

logger = logging.getLogger(__name__)


def home(request):
    """首页视图"""
    context = {}
    
    if request.user.is_authenticated:
        # 获取用户统计数据
        user_books = Book.objects.filter(user=request.user)
        
        # 计算阅读时间，处理可能的None值
        reading_progresses = ReadingProgress.objects.filter(user=request.user)
        total_reading_time = 0
        for progress in reading_progresses:
            if hasattr(progress, 'reading_time') and progress.reading_time:
                total_reading_time += progress.reading_time
        
        context['user_stats'] = {
            'total_books': user_books.count(),
            'categories_count': user_books.values('category').distinct().count(),
            'total_views': sum([book.view_count for book in user_books if hasattr(book, 'view_count') and book.view_count]),
            'notes_count': BookNote.objects.filter(user=request.user).count(),
        }
        
        # 获取最近阅读的书籍
        recent_books = user_books.filter(
            last_read_at__isnull=False
        ).order_by('-last_read_at')[:3]
        context['recent_books'] = recent_books
        
        # 获取分类统计
        context['category_stats'] = CategoryService.get_category_statistics(request.user)
    
    return render(request, 'home.html', context)


@login_required
def book_list(request):
    """书籍列表视图"""
    books = Book.objects.filter(user=request.user).order_by('-uploaded_at')
    
    # 分类筛选
    category_code = request.GET.get('category')
    if category_code:
        books = books.filter(category__code=category_code)
    
    # 搜索功能
    search_query = request.GET.get('search', '')
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    # 分页
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取所有分类
    categories = BookCategory.objects.all().order_by('name')
    
    # 获取热门分类（有书籍的分类）
    popular_categories = BookCategory.objects.filter(
        book__user=request.user
    ).distinct()[:5]
    
    context = {
        'books': page_obj,  # 模板中使用的是books变量
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'categories': categories,
        'popular_categories': popular_categories,
        'selected_category': category_code,
    }
    
    return render(request, 'books/book_list.html', context)


@login_required
def book_upload(request):
    """书籍上传视图"""
    if request.method == 'POST':
        # 处理文件上传
        title = request.POST.get('title', '')
        author = request.POST.get('author', '')
        description = request.POST.get('description', '')
        file = request.FILES.get('file')
        cover = request.FILES.get('cover')
        
        if not title or not file:
            messages.error(request, '请填写书名并选择文件')
            return render(request, 'books/book_upload.html')
        
        try:
            # 创建书籍记录
            book = Book.objects.create(
                user=request.user,
                title=title,
                author=author,
                description=description,
                file=file,
                cover=cover
            )
            
            # 处理书籍内容提取和AI分类
            processing_service = BookProcessingService(request.user)
            
            # 首先提取文本内容
            try:
                extracted_content = processing_service._extract_text_content(book)
                
                if extracted_content:
                    # 成功提取到内容，创建BookContent记录
                    BookContent.objects.create(
                        book=book,
                        chapter_number=1,
                        chapter_title="全文内容",
                        content=extracted_content[:50000],  # 限制长度
                        word_count=len(extracted_content)
                    )
                    book.word_count = len(extracted_content)
                    book.processing_status = 'processing'
                    book.save()
                    
                    # 然后进行AI分类
                    processing_service.classify_book_with_ai(book)
                    
                    messages.success(request, f'书籍《{title}》上传成功！内容已提取，正在进行AI分类...')
                else:
                    # 提取失败，创建默认内容
                    default_content = f"抱歉，无法自动解析《{book.title}》的文本内容。\n\n可能的原因：\n1. 文件格式不支持自动解析\n2. 文件内容为图片或扫描版\n3. 文件已加密或损坏\n\n请尝试：\n- 转换为TXT格式后重新上传\n- 联系管理员获取帮助"
                    
                    BookContent.objects.create(
                        book=book,
                        chapter_number=1,
                        chapter_title="内容解析说明",
                        content=default_content,
                        word_count=len(default_content)
                    )
                    book.word_count = len(default_content)
                    book.processing_status = 'failed'
                    book.save()
                    
                    messages.warning(request, f'书籍《{title}》上传成功，但无法自动解析文本内容。请查看详情页面了解更多信息。')
                    
            except Exception as content_error:
                logger.error(f"内容提取失败: {str(content_error)}")
                # 即使内容提取失败，也尝试AI分类
                processing_service.classify_book_with_ai(book)
                messages.warning(request, f'书籍《{title}》上传成功，但内容处理时出现问题：{str(content_error)}')
            
            return redirect('book_detail', book_id=book.id)
            
        except Exception as e:
            messages.error(request, f'上传失败：{str(e)}')
    
    # 获取所有分类
    categories = BookCategory.objects.all().order_by('name')
    context = {'categories': categories}
    
    return render(request, 'books/book_upload.html', context)


@login_required
def batch_upload(request):
    """批量上传视图"""
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        batch_name = request.POST.get('batch_name', '')
        
        # 检查是否为AJAX请求
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            'application/json' in request.headers.get('Accept', '') or
            request.content_type == 'application/json'
        )
        
        if not files:
            if is_ajax:
                return JsonResponse({'success': False, 'error': '请选择要上传的文件'})
            messages.error(request, '请选择要上传的文件')
            return render(request, 'books/batch_upload.html')
        
        try:
            # 处理批量上传
            processing_service = BookProcessingService(request.user)
            batch_upload = processing_service.process_batch_upload(files, batch_name)
            
            # 检查请求是否期望JSON响应
            if is_ajax:
                return JsonResponse({
                    'success': True, 
                    'batch_id': batch_upload.id,
                    'message': f'批量上传已开始，共{len(files)}个文件。批次ID：{batch_upload.id}'
                })
            
            messages.success(request, f'批量上传已开始，共{len(files)}个文件。批次ID：{batch_upload.id}')
            return redirect('batch_upload_status', batch_id=batch_upload.id)
            
        except Exception as e:
            logger.error(f"批量上传失败: {str(e)}")
            if is_ajax:
                return JsonResponse({'success': False, 'error': f'批量上传失败：{str(e)}'})
            messages.error(request, f'批量上传失败：{str(e)}')
    
    return render(request, 'books/batch_upload.html')


@login_required
def batch_upload_status(request, batch_id):
    """批量上传状态视图"""
    batch_upload = get_object_or_404(BatchUpload, id=batch_id, user=request.user)
    
    # 获取与此批量上传相关的书籍
    # 使用更精确的时间范围，考虑到批量上传可能需要一些时间
    time_buffer = timedelta(minutes=5)  # 给5分钟的缓冲时间
    start_time = batch_upload.created_at - time_buffer
    end_time = batch_upload.completed_at + time_buffer if batch_upload.completed_at else timezone.now() + time_buffer
    
    books = Book.objects.filter(
        user=request.user, 
        uploaded_at__gte=start_time,
        uploaded_at__lte=end_time
    ).order_by('-uploaded_at')
    
    context = {
        'batch_upload': batch_upload,
        'books': books
    }
    
    return render(request, 'books/batch_upload_status.html', context)


@login_required
def book_detail(request, book_id):
    """书籍详情视图"""
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    # 获取阅读进度
    try:
        progress = ReadingProgress.objects.get(user=request.user, book=book)
    except ReadingProgress.DoesNotExist:
        progress = None
    
    # 获取笔记
    notes = BookNote.objects.filter(user=request.user, book=book)[:5]
    
    # 获取问答记录
    questions = BookQuestion.objects.filter(user=request.user, book=book)[:5]
    
    # 获取章节信息
    chapters = BookContent.objects.filter(book=book).order_by('chapter_number')
    
    context = {
        'book': book,
        'progress': progress,
        'notes': notes,
        'questions': questions,
        'chapters': chapters,
        'total_chapters': chapters.count(),
    }
    
    return render(request, 'books/book_detail.html', context)


@login_required
def book_read(request, book_id):
    """阅读书籍视图"""
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    # 获取或创建阅读进度
    progress, created = ReadingProgress.objects.get_or_create(
        user=request.user,
        book=book,
        defaults={'current_chapter': 1, 'progress_percentage': 0}
    )
    
    # 获取章节内容
    chapters = BookContent.objects.filter(book=book).order_by('chapter_number')
    current_chapter = chapters.filter(chapter_number=progress.current_chapter).first()
    
    # 如果没有找到当前章节，使用第一章
    if not current_chapter and chapters.exists():
        current_chapter = chapters.first()
        progress.current_chapter = current_chapter.chapter_number
        progress.save()
    
    # 如果书籍没有任何章节内容，尝试重新处理
    if not current_chapter:
        try:
            # 使用书籍处理服务重新提取内容
            processing_service = BookProcessingService(request.user)
            content = processing_service._extract_text_content(book)
            
            if content:
                # 成功提取到内容，创建BookContent记录
                current_chapter = BookContent.objects.create(
                    book=book,
                    chapter_number=1,
                    chapter_title="全文内容",
                    content=content[:50000],  # 限制长度
                    word_count=len(content)
                )
                book.word_count = len(content)
                book.processing_status = 'completed'
                book.save()
                
                # 更新进度
                progress.current_chapter = 1
                progress.save()
            else:
                # 创建默认内容
                default_content = f"抱歉，无法自动解析《{book.title}》的文本内容。\n\n可能的原因：\n1. 文件格式不支持自动解析\n2. 文件内容为图片或扫描版\n3. 文件已加密或损坏\n\n请尝试：\n- 转换为TXT格式后重新上传\n- 联系管理员获取帮助"
                
                current_chapter = BookContent.objects.create(
                    book=book,
                    chapter_number=1,
                    chapter_title="内容解析说明",
                    content=default_content,
                    word_count=len(default_content)
                )
                book.word_count = len(default_content)
                book.processing_status = 'failed'
                book.save()
                
                # 更新进度
                progress.current_chapter = 1
                progress.save()
                
        except Exception as e:
            logger.error(f"重新处理书籍内容失败: {str(e)}")
            # 创建一个临时的章节对象，避免模板错误
            class DefaultChapter:
                def __init__(self):
                    self.chapter_number = 1
                    self.chapter_title = "内容处理中"
                    self.content = f"该书籍正在处理中，请稍后再试。\n\n错误信息：{str(e)}\n\n如果问题持续存在，请联系管理员。"
            
            current_chapter = DefaultChapter()
            # 确保进度也是合理的
            if progress.current_chapter < 1:
                progress.current_chapter = 1
                progress.save()
    
    # 重新获取章节列表（可能已经创建了新的章节）
    chapters = BookContent.objects.filter(book=book).order_by('chapter_number')
    
    context = {
        'book': book,
        'progress': progress,
        'chapters': chapters,
        'current_chapter': current_chapter,
        'total_chapters': chapters.count() if chapters.exists() else 1,
    }
    
    return render(request, 'books/book_read.html', context)


@login_required
def book_delete(request, book_id):
    """删除书籍视图"""
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    if request.method == 'POST':
        book_title = book.title
        book.delete()
        messages.success(request, f'书籍《{book_title}》已删除')
        return redirect('book_list')
    
    return render(request, 'books/book_delete.html', {'book': book})


@login_required
def category_list(request):
    """分类列表视图"""
    categories = BookCategory.objects.annotate(
        book_count=Count('book', filter=Q(book__user=request.user))
    ).order_by('-book_count', 'name')
    
    context = {
        'categories': categories,
        'category_stats': CategoryService.get_category_statistics(request.user)
    }
    
    return render(request, 'books/category_list.html', context)


@login_required
def category_books(request, category_code):
    """分类书籍视图"""
    category = get_object_or_404(BookCategory, code=category_code)
    books = CategoryService.get_books_by_category(category_code, request.user)
    
    # 分页
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj,
    }
    
    return render(request, 'books/category_books.html', context)


@login_required
def notes_list(request, book_id):
    """笔记列表视图"""
    book = get_object_or_404(Book, id=book_id, user=request.user)
    notes = BookNote.objects.filter(user=request.user, book=book).order_by('-created_at')
    
    # 分页
    paginator = Paginator(notes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'book': book,
        'page_obj': page_obj,
    }
    
    return render(request, 'books/notes_list.html', context)


@login_required
def reading_history(request):
    """阅读历史视图"""
    progress_list = ReadingProgress.objects.filter(user=request.user).order_by('-last_read_at')
    
    # 分页
    paginator = Paginator(progress_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'books/reading_history.html', context)


# API视图
@login_required
@require_http_methods(["POST"])
def save_reading_progress(request):
    """保存阅读进度API"""
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        chapter = data.get('chapter', 1)
        progress = data.get('progress', 0)
        
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        progress_obj, created = ReadingProgress.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={
                'current_chapter': chapter,
                'progress_percentage': progress
            }
        )
        
        if not created:
            progress_obj.current_chapter = chapter
            progress_obj.progress_percentage = progress
            progress_obj.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_chapter_content(request, book_id, chapter_number):
    """获取章节内容API"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        chapter = get_object_or_404(BookContent, book=book, chapter_number=chapter_number)
        
        return JsonResponse({
            'success': True,
            'content': chapter.content,
            'title': chapter.chapter_title or f'第{chapter_number}章'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def add_note(request, book_id):
    """添加笔记API"""
    try:
        data = json.loads(request.body)
        content = data.get('content', '')
        chapter_number = data.get('chapter_number', 1)
        
        if not content.strip():
            return JsonResponse({'success': False, 'error': '笔记内容不能为空'})
        
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        note = BookNote.objects.create(
            user=request.user,
            book=book,
            note_content=content,
            chapter_number=chapter_number,
            selected_text='',  # 可以为空
            position_start=0,
            position_end=0
        )
        
        return JsonResponse({
            'success': True,
            'note': {
                'id': note.id,
                'content': note.note_content,
                'chapter_number': note.chapter_number,
                'created_at': note.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def classify_book(request, book_id):
    """手动触发书籍分类API"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        processing_service = BookProcessingService(request.user)
        result = processing_service.classify_book_with_ai(book)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_batch_upload_progress(request, batch_id):
    """获取批量上传进度API"""
    try:
        batch_upload = get_object_or_404(BatchUpload, id=batch_id, user=request.user)
        
        # 获取与此批量上传相关的书籍
        time_buffer = timedelta(minutes=5)
        start_time = batch_upload.created_at - time_buffer
        end_time = batch_upload.completed_at + time_buffer if batch_upload.completed_at else timezone.now() + time_buffer
        
        books = Book.objects.filter(
            user=request.user, 
            uploaded_at__gte=start_time,
            uploaded_at__lte=end_time
        ).order_by('-uploaded_at')
        
        # 构建文件进度信息
        files_progress = []
        for book in books:
            # 计算进度百分比
            if book.processing_status == 'completed':
                progress = 100
                status = 'success'
                message = f'处理完成，字数: {book.word_count:,}'
            elif book.processing_status == 'failed':
                progress = 100
                status = 'error'
                message = '处理失败，请检查文件格式'
            elif book.processing_status == 'processing':
                progress = 60
                status = 'processing'
                message = '正在提取内容和AI分类...'
            else:  # pending
                progress = 20
                status = 'processing'
                message = '等待处理...'
            
            # 尝试构建原始文件名
            original_filename = f"{book.title}.{book.format}"
            
            files_progress.append({
                'filename': original_filename,
                'title': book.title,
                'progress': progress,
                'status': status,
                'message': message,
                'book_id': book.id,
                'format': book.format.upper(),
                'file_size': book.file_size,
                'word_count': book.word_count,
                'processing_status': book.processing_status
            })
        
        # 如果书籍数量少于总文件数，说明还有文件在处理中
        remaining_files = batch_upload.total_files - len(books)
        if remaining_files > 0 and batch_upload.status == 'processing':
            for i in range(remaining_files):
                files_progress.append({
                    'filename': f'处理中的文件_{i+1}',
                    'title': '处理中...',
                    'progress': 10,
                    'status': 'uploading',
                    'message': '正在上传和初始化...',
                    'book_id': None,
                    'format': 'UNKNOWN',
                    'file_size': 0,
                    'word_count': 0,
                    'processing_status': 'pending'
                })
        
        return JsonResponse({
            'success': True,
            'batch_upload': {
                'id': batch_upload.id,
                'upload_name': batch_upload.upload_name,
                'status': batch_upload.status,
                'total_files': batch_upload.total_files,
                'processed_files': batch_upload.processed_files,
                'successful_files': batch_upload.successful_files,
                'failed_files': batch_upload.failed_files,
                'progress_percentage': batch_upload.progress_percentage,
                'error_log': batch_upload.error_log,
                'created_at': batch_upload.created_at.isoformat(),
                'completed_at': batch_upload.completed_at.isoformat() if batch_upload.completed_at else None
            },
            'files': files_progress
        })
        
    except Exception as e:
        logger.error(f"获取批量上传进度失败: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_category_stats(request):
    """获取分类统计API"""
    try:
        stats = CategoryService.get_category_statistics(request.user)
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def reading_statistics(request):
    """阅读统计页面"""
    user = request.user
    period_type = request.GET.get('period', 'weekly')
    
    # 获取统计数据
    stats = ReadingStatisticsService.get_reading_time_stats(user, period_type)
    trends = ReadingStatisticsService.get_reading_trends(user, days=30)
    
    # 获取各周期统计
    daily_stats = ReadingStatisticsService.get_reading_time_stats(user, 'daily')
    weekly_stats = ReadingStatisticsService.get_reading_time_stats(user, 'weekly')
    monthly_stats = ReadingStatisticsService.get_reading_time_stats(user, 'monthly')
    yearly_stats = ReadingStatisticsService.get_reading_time_stats(user, 'yearly')
    
    # 获取最近阅读的书籍
    recent_sessions = ReadingSession.objects.filter(
        user=user,
        end_time__isnull=False
    ).select_related('book').order_by('-end_time')[:10]
    
    context = {
        'stats': stats,
        'trends': trends,
        'daily_stats': daily_stats,
        'weekly_stats': weekly_stats,
        'monthly_stats': monthly_stats,
        'yearly_stats': yearly_stats,
        'recent_sessions': recent_sessions,
        'current_period': period_type,
    }
    
    return render(request, 'books/reading_statistics.html', context)


@login_required
def start_reading_session(request, book_id):
    """开始阅读会话"""
    if request.method == 'POST':
        try:
            book = get_object_or_404(Book, id=book_id, user=request.user)
            chapter_number = request.POST.get('chapter_number')
            
            session = ReadingStatisticsService.start_reading_session(
                request.user, book, chapter_number
            )
            
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'message': '阅读会话已开始'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'开始阅读会话失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def end_reading_session(request):
    """结束阅读会话"""
    if request.method == 'POST':
        try:
            book_id = request.POST.get('book_id')
            book = None
            if book_id:
                book = get_object_or_404(Book, id=book_id, user=request.user)
            
            count = ReadingStatisticsService.end_reading_session(request.user, book)
            
            # 更新统计数据
            ReadingStatisticsService.update_reading_statistics(request.user)
            
            return JsonResponse({
                'success': True,
                'sessions_ended': count,
                'message': f'已结束 {count} 个阅读会话'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'结束阅读会话失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def book_notes(request, book_id):
    """书籍笔记页面"""
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    # 获取筛选参数
    note_type = request.GET.get('type')
    chapter_number = request.GET.get('chapter')
    search_keyword = request.GET.get('search')
    
    # 获取笔记
    if search_keyword:
        notes = BookNoteService.search_notes(request.user, search_keyword, book)
    else:
        notes = BookNoteService.get_book_notes(
            request.user, book, note_type, 
            int(chapter_number) if chapter_number else None
        )
    
    # 获取章节列表
    chapters = book.contents.values_list('chapter_number', 'chapter_title').distinct()
    
    # 获取笔记统计
    note_stats = {
        'total': notes.count(),
        'highlights': notes.filter(note_type='highlight').count(),
        'notes': notes.filter(note_type='note').count(),
        'bookmarks': notes.filter(note_type='bookmark').count(),
        'questions': notes.filter(note_type='question').count(),
        'insights': notes.filter(note_type='insight').count(),
    }
    
    context = {
        'book': book,
        'notes': notes,
        'chapters': chapters,
        'note_stats': note_stats,
        'current_type': note_type,
        'current_chapter': chapter_number,
        'search_keyword': search_keyword,
    }
    
    return render(request, 'books/book_notes.html', context)


@login_required
def create_note(request):
    """创建笔记"""
    if request.method == 'POST':
        try:
            book_id = request.POST.get('book_id')
            book = get_object_or_404(Book, id=book_id, user=request.user)
            
            note = BookNoteService.create_note(
                user=request.user,
                book=book,
                chapter_number=int(request.POST.get('chapter_number')),
                position_start=int(request.POST.get('position_start')),
                position_end=int(request.POST.get('position_end')),
                selected_text=request.POST.get('selected_text'),
                note_content=request.POST.get('note_content', ''),
                note_type=request.POST.get('note_type', 'note'),
                color=request.POST.get('color', 'yellow'),
                tags=request.POST.get('tags', '')
            )
            
            return JsonResponse({
                'success': True,
                'note_id': note.id,
                'message': '笔记创建成功'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'创建笔记失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def update_note(request, note_id):
    """更新笔记"""
    if request.method == 'POST':
        try:
            note = get_object_or_404(BookNote, id=note_id, user=request.user)
            
            note.note_content = request.POST.get('note_content', note.note_content)
            note.note_type = request.POST.get('note_type', note.note_type)
            note.color = request.POST.get('color', note.color)
            note.tags = request.POST.get('tags', note.tags)
            note.save()
            
            return JsonResponse({
                'success': True,
                'message': '笔记更新成功'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'更新笔记失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def delete_note(request, note_id):
    """删除笔记"""
    if request.method == 'POST':
        try:
            note = get_object_or_404(BookNote, id=note_id, user=request.user)
            note.delete()
            
            return JsonResponse({
                'success': True,
                'message': '笔记删除成功'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'删除笔记失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def note_collections(request):
    """笔记集合页面"""
    collections = NoteCollection.objects.filter(user=request.user)
    
    if request.method == 'POST':
        # 创建新集合
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            note_ids = request.POST.getlist('note_ids')
            
            collection = BookNoteService.create_note_collection(
                request.user, name, description, note_ids
            )
            
            return JsonResponse({
                'success': True,
                'collection_id': collection.id,
                'message': '笔记集合创建成功'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'创建集合失败: {str(e)}'
            })
    
    context = {
        'collections': collections,
    }
    
    return render(request, 'books/note_collections.html', context)


@login_required
def export_notes(request, book_id=None):
    """导出笔记"""
    try:
        book = None
        if book_id:
            book = get_object_or_404(Book, id=book_id, user=request.user)
        
        format_type = request.GET.get('format', 'json')
        notes_data = BookNoteService.export_notes(request.user, book, format_type)
        
        if format_type == 'json':
            response = JsonResponse({
                'success': True,
                'data': notes_data,
                'count': len(notes_data)
            })
        else:
            # 其他格式的导出可以在这里实现
            response = JsonResponse({
                'success': False,
                'message': '不支持的导出格式'
            })
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'导出失败: {str(e)}'
        })


@login_required
def book_summaries(request, book_id):
    """书籍总结页面"""
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    # 获取现有总结
    summaries = AISummaryService.get_book_summaries(book)
    
    # 获取段落总结
    paragraph_summaries = AISummaryService.get_paragraph_summaries(book)
    
    context = {
        'book': book,
        'summaries': summaries,
        'paragraph_summaries': paragraph_summaries,
    }
    
    return render(request, 'books/book_summaries.html', context)


@login_required
def create_book_summary(request, book_id):
    """创建书籍总结"""
    if request.method == 'POST':
        try:
            book = get_object_or_404(Book, id=book_id, user=request.user)
            summary_type = request.POST.get('summary_type', 'overview')
            
            # 检查是否已存在该类型的总结
            existing = BookSummary.objects.filter(
                book=book, 
                summary_type=summary_type
            ).first()
            
            if existing:
                return JsonResponse({
                    'success': False,
                    'message': '该类型的总结已存在'
                })
            
            # 创建总结
            summary = AISummaryService.create_book_summary(
                book, summary_type, request.user
            )
            
            return JsonResponse({
                'success': True,
                'summary_id': summary.id,
                'message': '总结创建成功'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'创建总结失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def create_paragraph_summary(request):
    """创建段落总结"""
    if request.method == 'POST':
        try:
            book_id = request.POST.get('book_id')
            book = get_object_or_404(Book, id=book_id, user=request.user)
            
            summary = AISummaryService.create_paragraph_summary(
                book=book,
                chapter_number=int(request.POST.get('chapter_number')),
                paragraph_start=int(request.POST.get('paragraph_start')),
                paragraph_end=int(request.POST.get('paragraph_end')),
                original_text=request.POST.get('original_text'),
                summary_type=request.POST.get('summary_type', 'brief'),
                user=request.user
            )
            
            return JsonResponse({
                'success': True,
                'summary_id': summary.id,
                'summary_text': summary.summary_text,
                'message': '段落总结创建成功'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'创建段落总结失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
@require_http_methods(["GET", "POST"])
def book_reader(request, book_id):
    """书籍阅读器页面"""
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    # 获取或创建阅读助手
    assistant_service = ReadingAssistantService(request.user, book)
    
    # 获取阅读进度
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()
    current_chapter = progress.current_chapter if progress else 1
    
    # 获取章节列表
    chapters = BookContent.objects.filter(book=book).order_by('chapter_number')
    
    # 获取用户偏好设置
    try:
        from readify.user_management.models import UserPreferences
        preferences = UserPreferences.objects.get(user=request.user)
    except UserPreferences.DoesNotExist:
        preferences = None
    
    context = {
        'book': book,
        'chapters': chapters,
        'current_chapter': current_chapter,
        'assistant': assistant_service.assistant,
        'preferences': preferences,
        'progress': progress,
    }
    
    return render(request, 'books/reader.html', context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def toggle_reading_assistant(request, book_id):
    """启用/禁用阅读助手"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        enabled = data.get('enabled', True)
        
        assistant_service = ReadingAssistantService(request.user, book)
        result = assistant_service.toggle_assistant(enabled)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'操作失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def ai_text_analysis(request, book_id):
    """AI文本分析 - 对选中文本进行问答或总结"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        selected_text = data.get('selected_text', '')
        question = data.get('question', '')
        analysis_type = data.get('analysis_type', 'question')  # question, summary, explain
        chapter_number = data.get('chapter_number', 1)
        
        # 使用AI服务进行分析
        from readify.ai_services.services import AIService
        ai_service = AIService(user=request.user)
        
        if analysis_type == 'question':
            if not question:
                return JsonResponse({'success': False, 'error': '请输入问题'}, status=400)
            
            # 构建问答提示
            if selected_text:
                prompt = f"基于以下选中的文本内容，请回答问题：{question}\n\n选中文本：\n{selected_text}"
            else:
                # 如果没有选中文本，获取当前章节内容
                chapter_content = BookContent.objects.filter(
                    book=book, 
                    chapter_number=chapter_number
                ).first()
                
                if chapter_content:
                    content = chapter_content.content[:3000]  # 限制长度
                    prompt = f"基于以下章节内容，请回答问题：{question}\n\n章节内容：\n{content}"
                else:
                    prompt = f"关于书籍《{book.title}》，请回答问题：{question}"
            
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "你是一个专业的阅读助手，能够基于提供的文本内容准确回答用户的问题。请确保回答准确、详细且有帮助。"
            
            result = ai_service._make_api_request(messages, system_prompt)
            
            if result['success']:
                # 获取或创建阅读助手记录
                assistant, created = ReadingAssistant.objects.get_or_create(
                    user=request.user,
                    book=book,
                    defaults={
                        'session_name': f'{book.title} - 阅读助手',
                        'current_chapter': chapter_number,
                        'is_enabled': True
                    }
                )
                
                # 保存问答记录
                qa_record = ReadingQA.objects.create(
                    assistant=assistant,
                    question_type='text',
                    question=question,
                    selected_text=selected_text,
                    chapter_number=chapter_number,
                    answer=result['content'],
                    context_used=selected_text or '当前章节',
                    ai_model_used='AI助手',
                    processing_time=result.get('processing_time', 0),
                    tokens_used=result.get('tokens_used', 0)
                )
                
                return JsonResponse({
                    'success': True,
                    'result': {
                        'answer': result['content'],
                        'processing_time': result.get('processing_time', 0)
                    },
                    'analysis_type': analysis_type
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'AI分析失败')
                })
            
        elif analysis_type == 'summary':
            if not selected_text:
                return JsonResponse({'success': False, 'error': '请选择要总结的文本'}, status=400)
            
            prompt = f"请对以下文本进行简洁的总结：\n\n{selected_text}"
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "你是一个专业的文本总结助手，能够准确提取文本的核心内容并生成简洁明了的摘要。"
            
            result = ai_service._make_api_request(messages, system_prompt)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'result': {
                        'summary': result['content'],
                        'processing_time': result.get('processing_time', 0)
                    },
                    'analysis_type': analysis_type
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'AI总结失败')
                })
            
        elif analysis_type == 'explain':
            if not selected_text:
                return JsonResponse({'success': False, 'error': '请选择要解释的文本'}, status=400)
            
            prompt = f"请详细解释以下文本的含义和背景：\n\n{selected_text}"
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "你是一个专业的文本解释助手，能够深入分析文本的含义、背景和相关知识。"
            
            result = ai_service._make_api_request(messages, system_prompt)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'result': {
                        'explanation': result['content'],
                        'processing_time': result.get('processing_time', 0)
                    },
                    'analysis_type': analysis_type
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'AI解释失败')
                })
        
        return JsonResponse({
            'success': False,
            'error': '不支持的分析类型'
        })
        
    except Exception as e:
        logger.error(f"AI文本分析失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'AI分析失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def generate_smart_summary(request, book_id):
    """生成智能总结 - 支持段落、章节、全书总结"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        summary_type = data.get('summary_type', 'chapter')  # paragraph, chapter, book
        chapter_number = data.get('chapter_number')
        paragraph_text = data.get('paragraph_text', '')
        summary_style = data.get('summary_style', 'balanced')  # brief, balanced, detailed
        
        # 使用AI服务进行总结
        from readify.ai_services.services import AIService
        ai_service = AIService(user=request.user)
        
        if summary_type == 'paragraph':
            if not paragraph_text:
                return JsonResponse({'success': False, 'error': '请提供段落文本'}, status=400)
            
            prompt = f"请对以下段落进行{summary_style}总结：\n\n{paragraph_text}"
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "你是一个专业的文本总结助手，能够准确提取文本的核心内容并生成简洁明了的摘要。"
            
            result = ai_service._make_api_request(messages, system_prompt)
            
            if result['success']:
                # 保存段落总结
                ParagraphSummary.objects.create(
                    book=book,
                    chapter_number=chapter_number or 1,
                    paragraph_start=0,
                    paragraph_end=len(paragraph_text),
                    original_text=paragraph_text,
                    summary_text=result['content'],
                    summary_type=summary_style,
                    ai_model_used='AI助手'
                )
                
                return JsonResponse({
                    'success': True,
                    'summary': result['content'],
                    'summary_type': summary_type,
                    'processing_time': result.get('processing_time', 0)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', '生成段落总结失败')
                })
            
        elif summary_type == 'chapter':
            if not chapter_number:
                return JsonResponse({'success': False, 'error': '请指定章节号'}, status=400)
            
            chapter_content = BookContent.objects.filter(
                book=book, 
                chapter_number=chapter_number
            ).first()
            
            if not chapter_content:
                return JsonResponse({'success': False, 'error': '章节不存在'}, status=400)
            
            # 限制内容长度
            content = chapter_content.content
            if len(content) > 6000:
                content = content[:6000] + "..."
            
            prompt = f"请对以下章节内容进行{summary_style}总结，提取关键要点：\n\n章节标题：{chapter_content.chapter_title}\n\n内容：\n{content}"
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "你是一个专业的文本总结助手，能够准确提取章节的核心内容、关键要点和主要观点。"
            
            result = ai_service._make_api_request(messages, system_prompt)
            
            if result['success']:
                # 保存或更新章节总结
                chapter_summary, created = ChapterSummary.objects.get_or_create(
                    book=book,
                    chapter_number=chapter_number,
                    summary_type=summary_style,
                    defaults={
                        'chapter_title': chapter_content.chapter_title,
                        'summary_content': result['content'],
                        'key_points': [],
                        'word_count': len(result['content']),
                        'original_word_count': chapter_content.word_count,
                        'ai_model_used': 'AI助手',
                        'created_by': request.user
                    }
                )
                
                if not created:
                    chapter_summary.summary_content = result['content']
                    chapter_summary.word_count = len(result['content'])
                    chapter_summary.ai_model_used = 'AI助手'
                    chapter_summary.save()
                
                return JsonResponse({
                    'success': True,
                    'summary': result['content'],
                    'summary_type': summary_type,
                    'processing_time': result.get('processing_time', 0)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', '生成章节总结失败')
                })
            
        elif summary_type == 'book':
            # 获取书籍的所有章节内容
            chapters = BookContent.objects.filter(book=book).order_by('chapter_number')[:5]  # 限制前5章
            
            if not chapters.exists():
                return JsonResponse({'success': False, 'error': '书籍没有可用内容'}, status=400)
            
            # 合并章节内容
            content_parts = []
            for chapter in chapters:
                content_parts.append(f"第{chapter.chapter_number}章 {chapter.chapter_title}\n{chapter.content[:1000]}")
            
            combined_content = "\n\n".join(content_parts)
            
            prompt = f"请对以下书籍内容进行{summary_style}总结，包括主要主题、核心观点和关键信息：\n\n书名：{book.title}\n作者：{book.author}\n\n内容：\n{combined_content}"
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "你是一个专业的书籍总结助手，能够准确提取书籍的核心主题、主要观点和关键信息。"
            
            result = ai_service._make_api_request(messages, system_prompt)
            
            if result['success']:
                # 保存或更新全书总结
                book_summary, created = BookSummary.objects.get_or_create(
                    book=book,
                    summary_type=summary_style,
                    defaults={
                        'title': f'{book.title} - {summary_style}总结',
                        'content': result['content'],
                        'key_points': [],
                        'themes': [],
                        'word_count': len(result['content']),
                        'ai_model_used': 'AI助手',
                        'created_by': request.user
                    }
                )
                
                if not created:
                    book_summary.content = result['content']
                    book_summary.word_count = len(result['content'])
                    book_summary.ai_model_used = 'AI助手'
                    book_summary.save()
                
                return JsonResponse({
                    'success': True,
                    'summary': result['content'],
                    'summary_type': summary_type,
                    'processing_time': result.get('processing_time', 0)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', '生成全书总结失败')
                })
        
        return JsonResponse({
            'success': False,
            'error': '不支持的总结类型'
        })
        
    except Exception as e:
        logger.error(f"生成智能总结失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'生成总结失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_reading_time(request, book_id):
    """更新阅读时间统计"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        chapter_number = data.get('chapter_number', 1)
        reading_duration = data.get('duration', 0)  # 秒
        words_read = data.get('words_read', 0)
        
        # 更新活跃的阅读会话
        active_session = ReadingSession.objects.filter(
            user=request.user,
            book=book,
            is_active=True
        ).first()
        
        if active_session:
            active_session.duration_seconds += reading_duration
            active_session.chapter_number = chapter_number
            active_session.pages_read = data.get('pages_read', 0)
            active_session.save()
        
        # 更新阅读进度
        progress, created = ReadingProgress.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={'current_chapter': chapter_number}
        )
        
        progress.reading_time += reading_duration
        progress.current_chapter = chapter_number
        progress.last_read_at = timezone.now()
        progress.save()
        
        # 创建或更新阅读时间追踪记录
        time_tracker, created = ReadingTimeTracker.objects.get_or_create(
            user=request.user,
            book=book,
            chapter_number=chapter_number,
            is_active=True,
            defaults={
                'duration_seconds': reading_duration,
                'words_read': words_read
            }
        )
        
        if not created:
            time_tracker.duration_seconds += reading_duration
            time_tracker.words_read += words_read
            time_tracker.save()
        
        # 计算阅读速度
        if reading_duration > 0 and words_read > 0:
            reading_speed = (words_read / reading_duration) * 60  # 字/分钟
            time_tracker.reading_speed = reading_speed
            time_tracker.save()
        
        return JsonResponse({
            'success': True,
            'total_reading_time': progress.reading_time,
            'session_time': active_session.duration_seconds if active_session else 0,
            'reading_speed': time_tracker.reading_speed if hasattr(time_tracker, 'reading_speed') else 0
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_reading_analytics(request, book_id):
    """获取阅读分析数据"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        # 获取阅读进度
        progress = ReadingProgress.objects.filter(user=request.user, book=book).first()
        
        # 获取阅读会话统计
        sessions = ReadingSession.objects.filter(user=request.user, book=book)
        total_sessions = sessions.count()
        total_reading_time = sum(session.duration_seconds for session in sessions)
        
        # 获取章节阅读时间统计
        chapter_times = ReadingTimeTracker.objects.filter(
            user=request.user, 
            book=book
        ).values('chapter_number').annotate(
            total_time=models.Sum('duration_seconds'),
            avg_speed=models.Avg('reading_speed')
        ).order_by('chapter_number')
        
        # 获取最近7天的阅读统计
        from datetime import datetime, timedelta
        week_ago = timezone.now() - timedelta(days=7)
        recent_sessions = sessions.filter(start_time__gte=week_ago)
        
        daily_stats = {}
        for session in recent_sessions:
            date_key = session.start_time.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {'time': 0, 'sessions': 0}
            daily_stats[date_key]['time'] += session.duration_seconds
            daily_stats[date_key]['sessions'] += 1
        
        return JsonResponse({
            'success': True,
            'progress': {
                'current_chapter': progress.current_chapter if progress else 1,
                'progress_percentage': progress.progress_percentage if progress else 0,
                'total_reading_time': progress.reading_time if progress else 0
            },
            'statistics': {
                'total_sessions': total_sessions,
                'total_reading_time': total_reading_time,
                'average_session_time': total_reading_time / total_sessions if total_sessions > 0 else 0,
                'chapter_times': list(chapter_times),
                'daily_stats': daily_stats
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def translate_text_selection(request, book_id):
    """翻译选中的文本 - 支持行和页面翻译"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        # 获取翻译参数
        text = data.get('text', '').strip()
        target_language = data.get('target_language', 'en')
        source_language = data.get('source_language', 'auto')
        translation_type = data.get('translation_type', 'selection')  # selection, line, page, chapter
        
        # 位置信息
        chapter_number = data.get('chapter_number')
        line_number = data.get('line_number')
        page_number = data.get('page_number')
        start_position = data.get('start_position', 0)
        end_position = data.get('end_position', 0)
        
        if not text and translation_type == 'selection':
            return JsonResponse({
                'success': False,
                'error': '请选择要翻译的文本'
            }, status=400)
        
        # 根据翻译类型获取文本
        if translation_type == 'line' and line_number is not None:
            # 翻译指定行
            text = get_line_text(book, chapter_number, line_number)
            if not text:
                return JsonResponse({
                    'success': False,
                    'error': '未找到指定行的文本'
                }, status=400)
                
        elif translation_type == 'page' and page_number is not None:
            # 翻译指定页面
            text = get_page_text(book, chapter_number, page_number)
            if not text:
                return JsonResponse({
                    'success': False,
                    'error': '未找到指定页面的文本'
                }, status=400)
                
        elif translation_type == 'chapter' and chapter_number is not None:
            # 翻译整个章节
            chapter_content = BookContent.objects.filter(
                book=book, 
                chapter_number=chapter_number
            ).first()
            
            if not chapter_content:
                return JsonResponse({
                    'success': False,
                    'error': '未找到指定章节'
                }, status=400)
            
            text = chapter_content.content
        
        if not text:
            return JsonResponse({
                'success': False,
                'error': '没有找到要翻译的文本'
            }, status=400)
        
        # 检查文本长度
        if len(text) > 10000:
            return JsonResponse({
                'success': False,
                'error': '文本过长，请选择较短的内容进行翻译'
            }, status=400)
        
        # 调用翻译服务
        from readify.translation_service.services import TranslationService
        translation_service = TranslationService()
        
        result = translation_service.translate_text(
            text=text,
            target_language=target_language,
            source_language=source_language,
            user=request.user,
            use_cache=True
        )
        
        if result['success']:
            # 保存翻译记录
            from readify.translation_service.models import TranslationHistory
            TranslationHistory.objects.create(
                user=request.user,
                source_text=text[:500],  # 限制长度
                translated_text=result['translated_text'][:500],
                source_language=result.get('detected_language', source_language),
                target_language=target_language,
                translation_context={
                    'book_id': book_id,
                    'book_title': book.title,
                    'chapter_number': chapter_number,
                    'line_number': line_number,
                    'page_number': page_number,
                    'translation_type': translation_type
                }
            )
            
            return JsonResponse({
                'success': True,
                'original_text': text,
                'translated_text': result['translated_text'],
                'source_language': result.get('detected_language', source_language),
                'target_language': target_language,
                'translation_type': translation_type,
                'confidence': result.get('confidence', 0.8),
                'cached': result.get('cached', False)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '翻译失败')
            }, status=500)
            
    except Exception as e:
        logger.error(f"翻译失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'翻译失败: {str(e)}'
        }, status=500)


def get_line_text(book, chapter_number, line_number):
    """获取指定行的文本"""
    try:
        chapter_content = BookContent.objects.filter(
            book=book, 
            chapter_number=chapter_number
        ).first()
        
        if not chapter_content:
            return None
        
        lines = chapter_content.content.split('\n')
        if 0 <= line_number - 1 < len(lines):
            return lines[line_number - 1].strip()
        
        return None
    except Exception:
        return None


def get_page_text(book, chapter_number, page_number, lines_per_page=30):
    """获取指定页面的文本"""
    try:
        chapter_content = BookContent.objects.filter(
            book=book, 
            chapter_number=chapter_number
        ).first()
        
        if not chapter_content:
            return None
        
        lines = chapter_content.content.split('\n')
        start_line = (page_number - 1) * lines_per_page
        end_line = start_line + lines_per_page
        
        if start_line < len(lines):
            page_lines = lines[start_line:end_line]
            return '\n'.join(page_lines).strip()
        
        return None
    except Exception:
        return None


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def get_translation_languages(request):
    """获取支持的翻译语言列表"""
    try:
        from readify.translation_service.services import TranslationService
        translation_service = TranslationService()
        languages = translation_service.get_supported_languages()
        
        return JsonResponse({
            'success': True,
            'languages': languages
        })
        
    except Exception as e:
        logger.error(f"获取语言列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '获取语言列表失败'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def get_translation_history(request, book_id):
    """获取书籍的翻译历史"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        from readify.translation_service.models import TranslationHistory
        
        # 获取该书籍的翻译历史
        history = TranslationHistory.objects.filter(
            user=request.user,
            translation_context__book_id=str(book_id)
        ).order_by('-created_at')[:20]
        
        history_data = []
        for record in history:
            history_data.append({
                'id': record.id,
                'source_text': record.source_text[:100] + '...' if len(record.source_text) > 100 else record.source_text,
                'translated_text': record.translated_text[:100] + '...' if len(record.translated_text) > 100 else record.translated_text,
                'source_language': record.source_language,
                'target_language': record.target_language,
                'created_at': record.created_at.isoformat(),
                'context': record.translation_context
            })
        
        return JsonResponse({
            'success': True,
            'history': history_data
        })
        
    except Exception as e:
        logger.error(f"获取翻译历史失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': '获取翻译历史失败'
        }, status=500)


@login_required
def optimized_book_reader(request, book_id):
    """优化的书籍阅读器视图"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        # 获取章节和页面参数
        chapter_number = int(request.GET.get('chapter', 1))
        page_number = int(request.GET.get('page', 1))
        
        # 创建优化渲染器
        renderer = OptimizedBookRenderer(book)
        
        # 渲染内容
        render_result = renderer.render_chapter(chapter_number, page_number)
        
        # 获取目录
        table_of_contents = renderer.get_table_of_contents()
        
        # 获取元数据
        metadata = renderer.get_book_metadata()
        
        # 更新阅读进度
        reading_progress, created = ReadingProgress.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={'current_chapter': chapter_number, 'current_page': page_number}
        )
        if not created:
            reading_progress.current_chapter = chapter_number
            reading_progress.current_page = page_number
            reading_progress.last_read_at = timezone.now()
            reading_progress.save()
        
        # 更新阅读会话
        session, created = ReadingSession.objects.get_or_create(
            user=request.user,
            book=book,
            session_date=timezone.now().date(),
            defaults={'duration': timedelta(0)}
        )
        
        context = {
            'book': book,
            'render_result': render_result,
            'table_of_contents': table_of_contents,
            'metadata': metadata,
            'current_chapter': chapter_number,
            'current_page': page_number,
            'reading_progress': reading_progress,
            'renderer_type': render_result.get('renderer_type', 'unknown'),
            'supports_pagination': render_result.get('supports_pagination', False),
        }
        
        # 清理渲染器资源
        renderer.cleanup()
        
        return render(request, 'books/optimized_reader.html', context)
        
    except Exception as e:
        logger.error(f"优化阅读器错误: {str(e)}")
        messages.error(request, f'阅读器加载失败: {str(e)}')
        return redirect('book_detail', book_id=book_id)


@login_required
def get_optimized_chapter_content(request, book_id):
    """AJAX获取优化渲染的章节内容"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        chapter_number = int(request.GET.get('chapter', 1))
        page_number = int(request.GET.get('page', 1))
        
        # 创建优化渲染器
        renderer = OptimizedBookRenderer(book)
        
        # 渲染内容
        render_result = renderer.render_chapter(chapter_number, page_number)
        
        # 清理资源
        renderer.cleanup()
        
        return JsonResponse({
            'success': True,
            'data': render_result
        })
        
    except Exception as e:
        logger.error(f"获取章节内容失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def get_book_metadata_api(request, book_id):
    """API获取书籍元数据"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        # 创建优化渲染器
        renderer = OptimizedBookRenderer(book)
        
        # 获取元数据
        metadata = renderer.get_book_metadata()
        
        # 获取目录
        table_of_contents = renderer.get_table_of_contents()
        
        # 清理资源
        renderer.cleanup()
        
        return JsonResponse({
            'success': True,
            'metadata': metadata,
            'table_of_contents': table_of_contents,
            'supported_formats': RendererFactory.get_supported_formats()
        })
        
    except Exception as e:
        logger.error(f"获取书籍元数据失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
