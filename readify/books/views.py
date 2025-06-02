from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
import json

from .models import Book, BookContent, ReadingProgress, BookNote, BookQuestion, BookCategory, BatchUpload
from .services import BookProcessingService, CategoryService


def home(request):
    """首页视图"""
    context = {}
    
    if request.user.is_authenticated:
        # 获取用户统计数据
        user_books = Book.objects.filter(user=request.user)
        context['user_stats'] = {
            'total_books': user_books.count(),
            'completed_books': ReadingProgress.objects.filter(
                user=request.user, 
                progress_percentage=100
            ).count(),
            'reading_time': sum([
                progress.reading_time for progress in 
                ReadingProgress.objects.filter(user=request.user)
            ]) // 3600,  # 转换为小时
            'questions_asked': BookQuestion.objects.filter(user=request.user).count(),
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
            'title': chapter.title
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def add_note(request):
    """添加笔记API"""
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        content = data.get('content', '')
        chapter_number = data.get('chapter_number', 1)
        
        if not content.strip():
            return JsonResponse({'success': False, 'error': '笔记内容不能为空'})
        
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        note = BookNote.objects.create(
            user=request.user,
            book=book,
            content=content,
            chapter_number=chapter_number
        )
        
        return JsonResponse({
            'success': True,
            'note': {
                'id': note.id,
                'content': note.content,
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
