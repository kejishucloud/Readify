from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
import json
from django.views.decorators.csrf import csrf_exempt

from .models import Book, BookContent, ReadingProgress, BookNote, BookQuestion, BookCategory, BatchUpload, ReadingSession, ReadingStatistics, NoteCollection, ParagraphSummary, BookSummary, ReadingAssistant, ReadingQA, ChapterSummary, ReadingTimeTracker
from .services import BookProcessingService, CategoryService, ReadingStatisticsService, BookNoteService, AISummaryService
from .reading_assistant import ReadingAssistantService


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
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'categories': categories,
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
            
            # 异步处理AI分类
            processing_service = BookProcessingService(request.user)
            processing_service.classify_book_with_ai(book)
            
            messages.success(request, f'书籍《{title}》上传成功！正在进行AI分类...')
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
        
        if not files:
            messages.error(request, '请选择要上传的文件')
            return render(request, 'books/batch_upload.html')
        
        try:
            # 处理批量上传
            processing_service = BookProcessingService(request.user)
            batch_upload = processing_service.process_batch_upload(files, batch_name)
            
            messages.success(request, f'批量上传已开始，共{len(files)}个文件。批次ID：{batch_upload.id}')
            return redirect('batch_upload_status', batch_id=batch_upload.id)
            
        except Exception as e:
            messages.error(request, f'批量上传失败：{str(e)}')
    
    return render(request, 'books/batch_upload.html')


@login_required
def batch_upload_status(request, batch_id):
    """批量上传状态视图"""
    batch_upload = get_object_or_404(BatchUpload, id=batch_id, user=request.user)
    
    context = {
        'batch_upload': batch_upload,
        'books': Book.objects.filter(user=request.user, uploaded_at__gte=batch_upload.created_at)
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
    
    context = {
        'book': book,
        'progress': progress,
        'chapters': chapters,
        'current_chapter': current_chapter,
        'total_chapters': chapters.count(),
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
            }
        })
        
    except Exception as e:
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
                summary_type=request.POST.get('summary_type', 'brief')
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
def ask_reading_question(request, book_id):
    """向阅读助手提问"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        question = data.get('question', '').strip()
        if not question:
            return JsonResponse({
                'success': False,
                'error': '问题不能为空'
            }, status=400)
        
        question_type = data.get('question_type', 'text')
        selected_text = data.get('selected_text', '')
        chapter_number = data.get('chapter_number')
        position_start = data.get('position_start')
        position_end = data.get('position_end')
        
        assistant_service = ReadingAssistantService(request.user, book)
        result = assistant_service.ask_question(
            question=question,
            question_type=question_type,
            selected_text=selected_text,
            chapter_number=chapter_number,
            position_start=position_start,
            position_end=position_end
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'提问失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def generate_chapter_summary(request, book_id):
    """生成章节总结"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        chapter_number = data.get('chapter_number')
        if not chapter_number:
            return JsonResponse({
                'success': False,
                'error': '章节号不能为空'
            }, status=400)
        
        summary_type = data.get('summary_type', 'auto')
        
        assistant_service = ReadingAssistantService(request.user, book)
        result = assistant_service.generate_chapter_summary(chapter_number, summary_type)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'生成总结失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def start_reading_session(request, book_id):
    """开始阅读会话"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        chapter_number = data.get('chapter_number', 1)
        
        assistant_service = ReadingAssistantService(request.user, book)
        result = assistant_service.start_reading_session(chapter_number)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'开始阅读失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def end_reading_session(request):
    """结束阅读会话"""
    try:
        data = json.loads(request.body)
        
        tracker_id = data.get('tracker_id')
        words_read = data.get('words_read', 0)
        
        if not tracker_id:
            return JsonResponse({
                'success': False,
                'error': '会话ID不能为空'
            }, status=400)
        
        # 直接通过tracker_id获取并结束会话
        try:
            tracker = ReadingTimeTracker.objects.get(
                id=tracker_id,
                user=request.user,
                is_active=True
            )
            
            tracker.words_read = words_read
            tracker.end_tracking()
            
            # 更新阅读进度
            progress = ReadingProgress.objects.get(user=request.user, book=tracker.book)
            progress.reading_time += tracker.duration_seconds
            progress.save()
            
            return JsonResponse({
                'success': True,
                'duration': tracker.duration_seconds,
                'words_read': words_read,
                'reading_speed': tracker.reading_speed,
                'message': f'阅读会话结束，用时{tracker.duration_seconds}秒'
            })
            
        except ReadingTimeTracker.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '未找到活跃的阅读会话'
            }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'结束阅读失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_reading_statistics(request, book_id):
    """获取阅读统计"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        assistant_service = ReadingAssistantService(request.user, book)
        result = assistant_service.get_reading_statistics()
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取统计失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_chapter_content(request, book_id, chapter_number):
    """获取章节内容"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        try:
            chapter = BookContent.objects.get(book=book, chapter_number=chapter_number)
            
            return JsonResponse({
                'success': True,
                'chapter': {
                    'number': chapter.chapter_number,
                    'title': chapter.chapter_title,
                    'content': chapter.content,
                    'word_count': chapter.word_count,
                }
            })
            
        except BookContent.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'未找到第{chapter_number}章内容'
            }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取章节内容失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_qa_history(request, book_id):
    """获取问答历史"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        # 获取阅读助手
        try:
            assistant = ReadingAssistant.objects.get(user=request.user, book=book)
        except ReadingAssistant.DoesNotExist:
            return JsonResponse({
                'success': True,
                'qa_history': []
            })
        
        # 获取问答记录
        qa_records = ReadingQA.objects.filter(assistant=assistant).order_by('-created_at')[:50]
        
        qa_history = []
        for qa in qa_records:
            qa_history.append({
                'id': qa.id,
                'question': qa.question,
                'answer': qa.answer,
                'question_type': qa.question_type,
                'selected_text': qa.selected_text,
                'chapter_number': qa.chapter_number,
                'is_helpful': qa.is_helpful,
                'created_at': qa.created_at.isoformat(),
                'processing_time': qa.processing_time,
            })
        
        return JsonResponse({
            'success': True,
            'qa_history': qa_history
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取问答历史失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def rate_qa_answer(request, qa_id):
    """评价问答回答"""
    try:
        data = json.loads(request.body)
        is_helpful = data.get('is_helpful')
        
        if is_helpful is None:
            return JsonResponse({
                'success': False,
                'error': '评价参数不能为空'
            }, status=400)
        
        # 获取问答记录
        qa = get_object_or_404(ReadingQA, id=qa_id, assistant__user=request.user)
        qa.is_helpful = is_helpful
        qa.save()
        
        return JsonResponse({
            'success': True,
            'message': '评价已保存'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'评价失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_chapter_summaries(request, book_id):
    """获取章节总结列表"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        summaries = ChapterSummary.objects.filter(book=book).order_by('chapter_number')
        
        summary_list = []
        for summary in summaries:
            summary_list.append({
                'id': summary.id,
                'chapter_number': summary.chapter_number,
                'chapter_title': summary.chapter_title,
                'summary_type': summary.summary_type,
                'summary_content': summary.summary_content,
                'key_points': summary.key_points,
                'word_count': summary.word_count,
                'compression_ratio': summary.compression_ratio,
                'created_at': summary.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'summaries': summary_list
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取总结列表失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def text_to_speech(request, book_id):
    """文本转语音"""
    try:
        book = get_object_or_404(Book, id=book_id, user=request.user)
        data = json.loads(request.body)
        
        text = data.get('text', '').strip()
        if not text:
            return JsonResponse({
                'success': False,
                'error': '文本不能为空'
            }, status=400)
        
        # 获取用户语音偏好
        try:
            from readify.user_management.models import UserPreferences
            preferences = UserPreferences.objects.get(user=request.user)
            voice_settings = {
                'voice_speed': preferences.voice_speed,
                'voice_type': preferences.voice_type,
                'voice_engine': preferences.voice_engine,
                'voice_language': preferences.voice_language,
                'voice_pitch': preferences.voice_pitch,
                'voice_volume': preferences.voice_volume,
            }
        except UserPreferences.DoesNotExist:
            voice_settings = {
                'voice_speed': 1.0,
                'voice_type': 'female',
                'voice_engine': 'system',
                'voice_language': 'zh-CN',
                'voice_pitch': 1.0,
                'voice_volume': 1.0,
            }
        
        # 调用TTS服务
        from readify.tts_service.services import EnhancedChatTTSService
        result = EnhancedChatTTSService.text_to_speech_with_preferences(
            text=text,
            user=request.user,
            book=book
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'audio_url': result['audio_url'],
                'duration': result.get('duration', 0),
                'message': '语音生成成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '语音生成失败')
            }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'语音生成失败: {str(e)}'
        }, status=500)
