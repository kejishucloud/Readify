from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
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
from readify.ai_services.services import AIService

logger = logging.getLogger(__name__)


@login_required
def user_settings(request):
    """用户设置页面"""
    try:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        preferences, created = UserPreferences.objects.get_or_create(user=request.user)
        ai_config, created = UserAIConfig.objects.get_or_create(user=request.user)
        
        context = {
            'profile': profile,
            'preferences': preferences,
            'ai_config': ai_config,
        }
        
        return render(request, 'user_management/settings.html', context)
        
    except Exception as e:
        logger.error(f"加载用户设置失败: {str(e)}")
        messages.error(request, '加载设置失败')
        return redirect('home')


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    """更新用户配置文件"""
    try:
        data = json.loads(request.body)
        
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # 更新字段
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
            'message': '配置文件更新成功'
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
        
        # 更新字段
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
    """AI配置视图"""
    if request.method == 'GET':
        try:
            config, created = UserAIConfig.objects.get_or_create(user=request.user)
            
            return JsonResponse({
                'success': True,
                'config': {
                    'provider': config.provider,
                    'api_url': config.api_url,
                    'model_id': config.model_id,
                    'max_tokens': config.max_tokens,
                    'temperature': config.temperature,
                    'timeout': config.timeout,
                    'is_active': config.is_active,
                    'has_api_key': bool(config.api_key)  # 不返回实际密钥
                }
            })
            
        except Exception as e:
            logger.error(f"获取AI配置失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'获取配置失败: {str(e)}'
            }, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            config, created = UserAIConfig.objects.get_or_create(user=request.user)
            
            # 更新配置
            if 'provider' in data:
                config.provider = data['provider']
            if 'api_url' in data:
                config.api_url = data['api_url']
            if 'api_key' in data and data['api_key']:  # 只有提供了新密钥才更新
                config.api_key = data['api_key']
            if 'model_id' in data:
                config.model_id = data['model_id']
            if 'max_tokens' in data:
                config.max_tokens = int(data['max_tokens'])
            if 'temperature' in data:
                config.temperature = float(data['temperature'])
            if 'timeout' in data:
                config.timeout = int(data['timeout'])
            if 'is_active' in data:
                config.is_active = data['is_active']
            
            config.save()
            
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
        ai_service = AIService(user=request.user)
        
        # 发送测试请求
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回复'AI配置测试成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': 'AI配置测试成功',
                'response': result['content']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'配置测试失败: {result["error"]}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"测试AI配置失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'测试失败: {str(e)}'
        }, status=500)


@login_required
def get_user_stats(request):
    """获取用户统计信息"""
    try:
        stats = {
            'total_books': Book.objects.filter(user=request.user).count(),
            'reading_progress': ReadingProgress.objects.filter(user=request.user).count(),
            'ai_requests': AIRequest.objects.filter(user=request.user).count(),
            'translation_requests': TranslationRequest.objects.filter(user=request.user).count(),
            'tts_requests': ChatTTSRequest.objects.filter(user=request.user).count(),
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        }, status=500)


def register(request):
    """用户注册视图"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 自动登录新用户
            login(request, user)
            messages.success(request, '注册成功！欢迎使用Readify！')
            return redirect('home')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form}) 