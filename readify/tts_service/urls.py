from django.urls import path
from . import views

app_name = 'tts_service'

urlpatterns = [
    # TTS API
    path('generate/', views.ChatTTSAPIView.as_view(), name='generate_speech'),
    
    # 说话人管理
    path('speakers/', views.get_speakers, name='get_speakers'),
    
    # 用户设置
    path('settings/', views.user_settings, name='user_settings'),
    
    # 历史记录
    path('history/', views.request_history, name='request_history'),
    
    # 缓存管理
    path('cache/cleanup/', views.cleanup_cache, name='cleanup_cache'),
    path('cache/stats/', views.cache_stats, name='cache_stats'),
] 