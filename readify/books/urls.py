from django.urls import path
from . import views

urlpatterns = [
    # 首页
    path('', views.home, name='home'),
    
    # 书籍管理
    path('books/', views.book_list, name='book_list'),
    path('books/upload/', views.book_upload, name='book_upload'),
    path('books/batch-upload/', views.batch_upload, name='batch_upload'),
    path('books/batch-upload/<int:batch_id>/status/', views.batch_upload_status, name='batch_upload_status'),
    path('books/<int:book_id>/', views.book_detail, name='book_detail'),
    path('books/<int:book_id>/read/', views.book_read, name='book_read'),
    path('books/<int:book_id>/delete/', views.book_delete, name='book_delete'),
    path('books/<int:book_id>/notes/', views.notes_list, name='notes_list'),
    
    # 分类管理
    path('categories/', views.category_list, name='category_list'),
    path('categories/<str:category_code>/', views.category_books, name='category_books'),
    
    # 阅读历史
    path('reading-history/', views.reading_history, name='reading_history'),
    
    # API端点
    path('api/books/<int:book_id>/progress/', views.save_reading_progress, name='save_reading_progress'),
    path('api/books/<int:book_id>/chapters/<int:chapter_number>/', views.get_chapter_content, name='get_chapter_content'),
    path('api/books/<int:book_id>/notes/', views.add_note, name='add_note'),
    path('api/books/<int:book_id>/classify/', views.classify_book, name='classify_book'),
    path('api/batch-upload/<int:batch_id>/progress/', views.get_batch_upload_progress, name='get_batch_upload_progress'),
    path('api/categories/stats/', views.get_category_stats, name='get_category_stats'),
] 