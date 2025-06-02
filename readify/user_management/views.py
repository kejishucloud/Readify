from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
import json
import logging

from .models import UserProfile, UserPreferences, UserAIConfig
from readify.books.models import Book, ReadingProgress, BookNote, BookQuestion
from readify.ai_services.models import AIRequest
from readify.translation_service.models import TranslationRequest
from readify.tts_service.models import ChatTTSRequest
from readify.ai_services.services import AIService

logger = logging.getLogger(__name__)


def get_user_stats(user):
    """获取用户统计数据的辅助函数"""
    if not user.is_authenticated:
        return {
            'total_books': 0,
            'categories_count': 0,
            'total_views': 0,
            'notes_count': 0,
        }
    
    try:
        user_books = Book.objects.filter(user=user)
        
        # 计算阅读时间，处理可能的None值
        reading_progresses = ReadingProgress.objects.filter(user=user)
        total_reading_time = 0
        for progress in reading_progresses:
            if hasattr(progress, 'reading_time') and progress.reading_time:
                total_reading_time += progress.reading_time
        
        user_stats = {
            'total_books': user_books.count(),
            'categories_count': user_books.values('category').distinct().count(),
            'total_views': sum([book.view_count for book in user_books if hasattr(book, 'view_count') and book.view_count]),
            'notes_count': BookNote.objects.filter(user=user).count(),
        }
        
        return user_stats
    except Exception as e:
        logger.error(f"获取用户统计数据失败: {str(e)}")
        return {
            'total_books': 0,
            'categories_count': 0,
            'total_views': 0,
            'notes_count': 0,
        }


@login_required
def user_settings(request):
    """用户设置页面"""
    try:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        preferences, created = UserPreferences.objects.get_or_create(user=request.user)
        ai_config, created = UserAIConfig.objects.get_or_create(user=request.user)
        
        # 获取用户统计数据
        user_stats = get_user_stats(request.user)
        
        context = {
            'profile': profile,
            'preferences': preferences,
            'ai_config': ai_config,
            'user_stats': user_stats,
        }
        
        return render(request, 'user_management/settings.html', context)
        
    except Exception as e:
        logger.error(f"加载用户设置失败: {str(e)}")
        messages.error(request, '加载设置失败')
        return redirect('home')


@login_required
@require_http_methods(["GET", "POST"])
def update_profile(request):
    """更新用户配置文件"""
    if request.method == 'GET':
        # 显示个人资料页面
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # 获取用户统计数据
            user_stats = get_user_stats(request.user)
            
            context = {
                'profile': profile,
                'user': request.user,
                'user_stats': user_stats,
            }
            return render(request, 'user_management/profile.html', context)
        except Exception as e:
            logger.error(f"加载个人资料失败: {str(e)}")
            messages.error(request, '加载个人资料失败')
            return redirect('user_management:settings')
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # 更新用户基本信息
            user = request.user
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            user.save()
            
            # 更新配置文件字段
            if 'bio' in data:
                profile.bio = data['bio']
            if 'location' in data:
                profile.location = data['location']
            if 'website' in data:
                profile.website = data['website']
            if 'birth_date' in data and data['birth_date']:
                profile.birth_date = data['birth_date']
            
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': '个人资料更新成功'
            })
            
        except Exception as e:
            logger.error(f"更新用户配置文件失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'更新失败: {str(e)}'
            }, status=500)


@login_required
@require_http_methods(["POST"])
def update_preferences(request):
    """更新用户偏好设置"""
    try:
        data = json.loads(request.body)
        
        preferences, created = UserPreferences.objects.get_or_create(user=request.user)
        
        # 基本设置
        if 'theme' in data:
            preferences.theme = data['theme']
        if 'language' in data:
            preferences.language = data['language']
        if 'user_timezone' in data:
            preferences.user_timezone = data['user_timezone']
        if 'email_notifications' in data:
            preferences.email_notifications = data['email_notifications']
        if 'push_notifications' in data:
            preferences.push_notifications = data['push_notifications']
        
        # 语音设置
        if 'voice_enabled' in data:
            preferences.voice_enabled = data['voice_enabled']
        if 'voice_speed' in data:
            preferences.voice_speed = float(data['voice_speed'])
        if 'voice_type' in data:
            preferences.voice_type = data['voice_type']
        if 'voice_engine' in data:
            preferences.voice_engine = data['voice_engine']
        if 'voice_language' in data:
            preferences.voice_language = data['voice_language']
        if 'voice_pitch' in data:
            preferences.voice_pitch = float(data['voice_pitch'])
        if 'voice_volume' in data:
            preferences.voice_volume = float(data['voice_volume'])
        if 'auto_read' in data:
            preferences.auto_read = data['auto_read']
        if 'auto_read_delay' in data:
            preferences.auto_read_delay = int(data['auto_read_delay'])
        
        # 阅读设置
        if 'reading_font_size' in data:
            preferences.reading_font_size = int(data['reading_font_size'])
        if 'reading_line_height' in data:
            preferences.reading_line_height = float(data['reading_line_height'])
        if 'reading_background' in data:
            preferences.reading_background = data['reading_background']
        if 'reading_mode' in data:
            preferences.reading_mode = data['reading_mode']
        
        # AI助手设置
        if 'ai_assistant_enabled' in data:
            preferences.ai_assistant_enabled = data['ai_assistant_enabled']
        if 'ai_auto_summary' in data:
            preferences.ai_auto_summary = data['ai_auto_summary']
        if 'ai_context_memory' in data:
            preferences.ai_context_memory = data['ai_context_memory']
        if 'ai_response_style' in data:
            preferences.ai_response_style = data['ai_response_style']
        
        preferences.save()
        
        return JsonResponse({
            'success': True,
            'message': '偏好设置更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新用户偏好设置失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def ai_config_view(request):
    """AI配置管理"""
    if request.method == 'GET':
        try:
            ai_config, created = UserAIConfig.objects.get_or_create(user=request.user)
            
            context = {
                'ai_config': ai_config,
                'user_stats': get_user_stats(request.user),
            }
            
            return render(request, 'user_management/ai_config.html', context)
            
        except Exception as e:
            logger.error(f"加载AI配置失败: {str(e)}")
            messages.error(request, '加载AI配置失败')
            return redirect('user_management:settings')
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            ai_config, created = UserAIConfig.objects.get_or_create(user=request.user)
            
            # 更新AI配置
            if 'openai_api_key' in data:
                ai_config.openai_api_key = data['openai_api_key']
            if 'openai_model' in data:
                ai_config.openai_model = data['openai_model']
            if 'openai_base_url' in data:
                ai_config.openai_base_url = data['openai_base_url']
            if 'max_tokens' in data:
                ai_config.max_tokens = int(data['max_tokens'])
            if 'temperature' in data:
                ai_config.temperature = float(data['temperature'])
            if 'enabled' in data:
                ai_config.enabled = data['enabled']
            
            ai_config.save()
            
            return JsonResponse({
                'success': True,
                'message': 'AI配置更新成功'
            })
            
        except Exception as e:
            logger.error(f"更新AI配置失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'更新失败: {str(e)}'
            }, status=500)


@login_required
@require_http_methods(["POST"])
def test_ai_config_view(request):
    """测试AI配置"""
    try:
        ai_config = UserAIConfig.objects.get(user=request.user)
        
        if not ai_config.enabled:
            return JsonResponse({
                'success': False,
                'message': 'AI功能未启用'
            })
        
        # 这里可以添加实际的AI测试逻辑
        ai_service = AIService(ai_config)
        test_result = ai_service.test_connection()
        
        return JsonResponse({
            'success': test_result['success'],
            'message': test_result['message']
        })
        
    except UserAIConfig.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'AI配置不存在'
        })
    except Exception as e:
        logger.error(f"测试AI配置失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'测试失败: {str(e)}'
        }, status=500)


@login_required
def get_user_stats_view(request):
    """获取用户统计数据API"""
    try:
        user_stats = get_user_stats(request.user)
        return JsonResponse({
            'success': True,
            'data': user_stats
        })
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        }, status=500)


def register(request):
    """用户注册"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # 创建用户配置文件
            UserProfile.objects.create(user=user)
            UserPreferences.objects.create(user=user)
            UserAIConfig.objects.create(user=user)
            
            login(request, user)
            messages.success(request, '注册成功！欢迎使用Readify')
            return redirect('home')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def custom_logout(request):
    """自定义退出登录视图，支持GET和POST请求"""
    if request.method == 'GET':
        # 对于GET请求，显示确认页面
        return render(request, 'registration/logout_confirm.html')
    elif request.method == 'POST':
        # 对于POST请求，执行退出登录
        logout(request)
        messages.success(request, '您已成功退出登录')
        return redirect('home')
    
    # 其他请求方法重定向到首页
    return redirect('home') 