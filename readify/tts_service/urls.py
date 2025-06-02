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

    # 语音选择和偏好设置
    path('voices/', views.voice_selection, name='voice_selection'),
    path('preferences/', views.voice_preferences, name='voice_preferences'),
    path('set-default-voice/', views.set_default_voice, name='set_default_voice'),
    path('toggle-favorite/', views.toggle_favorite_voice, name='toggle_favorite_voice'),
    path('generate-sample/', views.generate_voice_sample, name='generate_voice_sample'),
    path('tts-with-preferences/', views.tts_with_preferences, name='tts_with_preferences'),
    path('usage-statistics/', views.usage_statistics, name='usage_statistics'),
] 