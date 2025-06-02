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
    
    # 新的阅读器功能
    path('books/<int:book_id>/reader/', views.book_reader, name='book_reader'),
    
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
    
    # 阅读助手API
    path('api/books/<int:book_id>/assistant/toggle/', views.toggle_reading_assistant, name='toggle_reading_assistant'),
    
    # 阅读会话管理
    path('start-session/<int:book_id>/', views.start_reading_session, name='start_reading_session'),
    path('end-session/', views.end_reading_session, name='end_reading_session'),
    
    # 阅读统计相关
    path('statistics/', views.reading_statistics, name='reading_statistics'),
    
    # 笔记相关
    path('<int:book_id>/notes/', views.book_notes, name='book_notes'),
    path('notes/create/', views.create_note, name='create_note'),
    path('notes/<int:note_id>/update/', views.update_note, name='update_note'),
    path('notes/<int:note_id>/delete/', views.delete_note, name='delete_note'),
    path('notes/collections/', views.note_collections, name='note_collections'),
    path('notes/export/', views.export_notes, name='export_notes'),
    path('notes/export/<int:book_id>/', views.export_notes, name='export_book_notes'),
    
    # AI总结相关
    path('<int:book_id>/summaries/', views.book_summaries, name='book_summaries'),
    path('<int:book_id>/summaries/create/', views.create_book_summary, name='create_book_summary'),
    path('summaries/paragraph/create/', views.create_paragraph_summary, name='create_paragraph_summary'),
    
    # AI助手功能
    path('ai-analysis/<int:book_id>/', views.ai_text_analysis, name='ai_text_analysis'),
    path('smart-summary/<int:book_id>/', views.generate_smart_summary, name='generate_smart_summary'),
    path('update-reading-time/<int:book_id>/', views.update_reading_time, name='update_reading_time'),
    path('reading-analytics/<int:book_id>/', views.get_reading_analytics, name='get_reading_analytics'),
    
    # 翻译功能
    path('translate/<int:book_id>/', views.translate_text_selection, name='translate_text_selection'),
    path('translation-languages/', views.get_translation_languages, name='get_translation_languages'),
    path('translation-history/<int:book_id>/', views.get_translation_history, name='get_translation_history'),
    
    # 优化渲染器相关路由
    path('books/<int:book_id>/optimized-reader/', views.optimized_book_reader, name='optimized_book_reader'),
    path('books/<int:book_id>/optimized-content/', views.get_optimized_chapter_content, name='get_optimized_chapter_content'),
    path('books/<int:book_id>/metadata-api/', views.get_book_metadata_api, name='get_book_metadata_api'),
    
    # 收藏功能
    path('books/<int:book_id>/toggle-favorite/', views.toggle_book_favorite, name='toggle_book_favorite'),
    path('books/<int:book_id>/favorite-status/', views.check_book_favorite_status, name='check_book_favorite_status'),
    path('favorites/', views.favorite_books, name='favorite_books'),
    
    # 最近阅读
    path('recent/', views.recent_books, name='recent_books'),
    
    # 阅读统计图表
    path('statistics/charts/', views.reading_statistics_charts, name='reading_statistics_charts'),
    path('api/statistics/charts/', views.get_reading_charts_data, name='get_reading_charts_data'),
    
    # 阅读目标管理
    path('goals/', views.reading_goals, name='reading_goals'),
    path('goals/create/', views.create_reading_goal, name='create_reading_goal'),
    path('goals/<int:goal_id>/update/', views.update_reading_goal, name='update_reading_goal'),
    path('goals/<int:goal_id>/delete/', views.delete_reading_goal, name='delete_reading_goal'),
    path('api/goals/progress/', views.get_reading_goal_progress, name='get_reading_goal_progress'),
    
    # 高级搜索
    path('search/advanced/', views.advanced_book_search, name='advanced_book_search'),
] 