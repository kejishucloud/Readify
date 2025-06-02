from django.urls import path
from . import views

app_name = 'ai_services'

urlpatterns = [
    # AI服务API
    path('summary/', views.generate_summary, name='generate_summary'),
    path('question/', views.ask_question, name='ask_question'),
    path('keywords/', views.extract_keywords, name='extract_keywords'),
    path('analyze/', views.analyze_text, name='analyze_text'),
    
    # AI配置管理
    path('config/', views.ai_config, name='ai_config'),
    path('config/test/', views.test_ai_config, name='test_ai_config'),
    
    # 历史记录
    path('history/', views.ai_history, name='ai_history'),
    path('history/clear/', views.clear_history, name='clear_history'),
] 