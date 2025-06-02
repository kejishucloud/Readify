from django.urls import path
from . import views

app_name = 'translation_service'

urlpatterns = [
    # 翻译API
    path('translate/', views.TranslationAPIView.as_view(), name='translate_text'),
    path('batch-translate/', views.batch_translate, name='batch_translate'),
    
    # 语言相关
    path('languages/', views.supported_languages, name='supported_languages'),
    path('language-pairs/', views.popular_language_pairs, name='popular_language_pairs'),
    path('detect-language/', views.detect_language, name='detect_language'),
    
    # 用户设置
    path('settings/', views.user_settings, name='user_settings'),
    
    # 历史记录
    path('history/', views.translation_history, name='translation_history'),
    path('history/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('requests/', views.request_history, name='request_history'),
    
    # 缓存管理
    path('cache/cleanup/', views.cleanup_cache, name='cleanup_cache'),
    path('cache/stats/', views.cache_stats, name='cache_stats'),
]