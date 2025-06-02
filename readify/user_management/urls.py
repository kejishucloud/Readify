from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'user_management'

urlpatterns = [
    # 用户认证
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # 用户注册
    path('register/', views.register, name='register'),
    
    # 用户设置页面
    path('settings/', views.user_settings, name='settings'),
    
    # 配置文件管理
    path('profile/update/', views.update_profile, name='update_profile'),
    
    # 偏好设置
    path('preferences/update/', views.update_preferences, name='update_preferences'),
    
    # AI配置管理
    path('ai-config/', views.ai_config_view, name='ai_config'),
    path('ai-config/test/', views.test_ai_config_view, name='test_ai_config'),
    
    # 用户统计
    path('stats/', views.get_user_stats, name='user_stats'),
] 