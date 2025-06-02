from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.conf import settings

from .services import ChatTTSService, TTSVoiceService, EnhancedChatTTSService
from .models import ChatTTSCache, ChatTTSRequest, TTSSpeaker, TTSSettings, TTSVoice, UserVoicePreference, TTSUsageLog

logger = logging.getLogger(__name__)


class ChatTTSAPIView(View):
    """ChatTTS API视图"""
    
    def __init__(self):
        super().__init__()
        self.tts_service = ChatTTSService()
    
    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        """生成语音"""
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            language = data.get('language', 'zh')
            speaker_id = data.get('speaker_id', 'default')
            use_cache = data.get('use_cache', True)
            
            if not text:
                return JsonResponse({
                    'success': False,
                    'error': '文本不能为空'
                }, status=400)
            
            # 检查文本长度
            if len(text) > 5000:
                return JsonResponse({
                    'success': False,
                    'error': '文本长度不能超过5000字符'
                }, status=400)
            
            # 生成语音
            result = self.tts_service.generate_speech(
                text=text,
                language=language,
                speaker_id=speaker_id,
                user=request.user,
                use_cache=use_cache
            )
            
            if result['success']:
                return JsonResponse(result)
            else:
                return JsonResponse(result, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': '无效的JSON数据'
            }, status=400)
        except Exception as e:
            logger.error(f"TTS API错误: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': '服务器内部错误'
            }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_speakers(request):
    """获取可用的说话人列表"""
    try:
        tts_service = ChatTTSService()
        language = request.GET.get('language')
        speakers = tts_service.get_available_speakers(language)
        
        return Response({
            'success': True,
            'speakers': speakers
        })
        
    except Exception as e:
        logger.error(f"获取说话人列表失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取说话人列表失败'
        }, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_settings(request):
    """用户TTS设置"""
    try:
        tts_service = ChatTTSService()
        
        if request.method == 'GET':
            # 获取用户设置
            settings = tts_service.get_user_settings(request.user)
            return Response({
                'success': True,
                'settings': settings
            })
        
        elif request.method == 'POST':
            # 更新用户设置
            settings_data = request.data
            success = tts_service.update_user_settings(request.user, settings_data)
            
            if success:
                return Response({
                    'success': True,
                    'message': '设置更新成功'
                })
            else:
                return Response({
                    'success': False,
                    'error': '设置更新失败'
                }, status=500)
                
    except Exception as e:
        logger.error(f"TTS设置操作失败: {str(e)}")
        return Response({
            'success': False,
            'error': '操作失败'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_history(request):
    """获取用户TTS请求历史"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        requests = ChatTTSRequest.objects.filter(
            user=request.user
        ).order_by('-created_at')[start:end]
        
        total = ChatTTSRequest.objects.filter(user=request.user).count()
        
        history = []
        for req in requests:
            history.append({
                'id': req.id,
                'text': req.text[:100] + '...' if len(req.text) > 100 else req.text,
                'language': req.language,
                'speaker_id': req.speaker_id,
                'status': req.status,
                'error_message': req.error_message,
                'processing_time': req.processing_time,
                'created_at': req.created_at.isoformat(),
                'completed_at': req.completed_at.isoformat() if req.completed_at else None,
                'audio_url': req.audio_file.url if req.audio_file else None
            })
        
        return Response({
            'success': True,
            'history': history,
            'total': total,
            'page': page,
            'page_size': page_size,
            'has_next': end < total
        })
        
    except Exception as e:
        logger.error(f"获取TTS历史失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取历史记录失败'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cleanup_cache(request):
    """清理TTS缓存"""
    try:
        days = int(request.data.get('days', 30))
        tts_service = ChatTTSService()
        result = tts_service.cleanup_cache(days)
        
        return Response({
            'success': True,
            'message': f'清理完成，删除了{result["deleted_files"]}个文件和{result["deleted_records"]}条记录',
            'deleted_files': result['deleted_files'],
            'deleted_records': result['deleted_records']
        })
        
    except Exception as e:
        logger.error(f"清理TTS缓存失败: {str(e)}")
        return Response({
            'success': False,
            'error': '清理缓存失败'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cache_stats(request):
    """获取缓存统计信息"""
    try:
        total_cache = ChatTTSCache.objects.count()
        user_requests = ChatTTSRequest.objects.filter(user=request.user).count()
        
        # 获取最近的缓存
        recent_cache = ChatTTSCache.objects.order_by('-created_at')[:10]
        
        cache_list = []
        for cache in recent_cache:
            cache_list.append({
                'language': cache.language,
                'speaker_id': cache.speaker_id,
                'duration': cache.duration,
                'file_size': cache.file_size,
                'access_count': cache.access_count,
                'created_at': cache.created_at.isoformat()
            })
        
        return Response({
            'success': True,
            'stats': {
                'total_cache': total_cache,
                'user_requests': user_requests,
                'recent_cache': cache_list
            }
        })
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取统计信息失败'
        }, status=500)


@login_required
def voice_selection(request):
    """语音选择页面"""
    # 获取筛选参数
    language = request.GET.get('language', 'zh')
    gender = request.GET.get('gender')
    voice_type = request.GET.get('voice_type')
    
    # 获取可用语音
    voices = TTSVoiceService.get_available_voices(language, gender, voice_type)
    
    # 获取用户偏好
    preferences = TTSVoiceService.get_user_preferences(request.user)
    
    # 获取推荐语音
    recommended_voices = TTSVoiceService.get_recommended_voices(request.user, language)
    
    # 获取语言列表
    languages = TTSVoice.objects.filter(is_active=True).values_list(
        'language', 'language_name'
    ).distinct()
    
    context = {
        'voices': voices,
        'preferences': preferences,
        'recommended_voices': recommended_voices,
        'languages': languages,
        'current_language': language,
        'current_gender': gender,
        'current_voice_type': voice_type,
    }
    
    return render(request, 'tts_service/voice_selection.html', context)


@login_required
def voice_preferences(request):
    """语音偏好设置页面"""
    preferences = TTSVoiceService.get_user_preferences(request.user)
    
    if request.method == 'POST':
        try:
            # 更新偏好设置
            update_data = {}
            
            # 基本设置
            if 'reading_speed' in request.POST:
                update_data['reading_speed'] = float(request.POST.get('reading_speed'))
            if 'volume' in request.POST:
                update_data['volume'] = float(request.POST.get('volume'))
            if 'pitch' in request.POST:
                update_data['pitch'] = float(request.POST.get('pitch'))
            
            # 播放设置
            update_data['auto_play'] = request.POST.get('auto_play') == 'on'
            
            # 停顿设置
            if 'pause_between_paragraphs' in request.POST:
                update_data['pause_between_paragraphs'] = float(request.POST.get('pause_between_paragraphs'))
            if 'pause_between_sentences' in request.POST:
                update_data['pause_between_sentences'] = float(request.POST.get('pause_between_sentences'))
            
            # 背景音乐设置
            update_data['background_music_enabled'] = request.POST.get('background_music_enabled') == 'on'
            if 'background_music_volume' in request.POST:
                update_data['background_music_volume'] = float(request.POST.get('background_music_volume'))
            
            # 更新偏好
            TTSVoiceService.update_user_preferences(request.user, **update_data)
            
            return JsonResponse({
                'success': True,
                'message': '偏好设置已更新'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'更新失败: {str(e)}'
            })
    
    context = {
        'preferences': preferences,
    }
    
    return render(request, 'tts_service/voice_preferences.html', context)


@login_required
def set_default_voice(request):
    """设置默认语音"""
    if request.method == 'POST':
        try:
            voice_id = request.POST.get('voice_id')
            success = TTSVoiceService.set_default_voice(request.user, voice_id)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': '默认语音设置成功'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '语音不存在或不可用'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'设置失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def toggle_favorite_voice(request):
    """切换收藏语音"""
    if request.method == 'POST':
        try:
            voice_id = request.POST.get('voice_id')
            action = request.POST.get('action')  # 'add' or 'remove'
            
            if action == 'add':
                success = TTSVoiceService.add_favorite_voice(request.user, voice_id)
                message = '已添加到收藏' if success else '添加失败'
            else:
                success = TTSVoiceService.remove_favorite_voice(request.user, voice_id)
                message = '已从收藏移除' if success else '移除失败'
            
            return JsonResponse({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'操作失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def generate_voice_sample(request):
    """生成语音示例"""
    if request.method == 'POST':
        try:
            voice_id = request.POST.get('voice_id')
            sample_text = request.POST.get('sample_text')
            
            sample_url = TTSVoiceService.generate_voice_sample(voice_id, sample_text)
            
            if sample_url:
                return JsonResponse({
                    'success': True,
                    'sample_url': sample_url,
                    'message': '示例生成成功'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '示例生成失败'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'生成失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def tts_with_preferences(request):
    """使用用户偏好进行TTS"""
    if request.method == 'POST':
        try:
            text = request.POST.get('text')
            voice_id = request.POST.get('voice_id')
            book_id = request.POST.get('book_id')
            
            book = None
            if book_id:
                from readify.books.models import Book
                book = Book.objects.get(id=book_id, user=request.user)
            
            # 使用增强的TTS服务
            result = EnhancedChatTTSService.text_to_speech_with_preferences(
                text=text,
                user=request.user,
                book=book,
                voice_id=voice_id
            )
            
            if result and result['audio_data']:
                # 保存音频文件并返回URL
                import tempfile
                import os
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                
                # 生成文件名
                filename = f"tts_{request.user.id}_{timezone.now().timestamp()}.wav"
                
                # 保存文件
                file_path = default_storage.save(
                    f"tts_audio/{filename}",
                    ContentFile(result['audio_data'])
                )
                
                audio_url = default_storage.url(file_path)
                
                return JsonResponse({
                    'success': True,
                    'audio_url': audio_url,
                    'voice_name': result['voice'].display_name,
                    'processing_time': result['processing_time'],
                    'message': 'TTS生成成功'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'TTS生成失败'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'TTS生成失败: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '无效请求'})


@login_required
def usage_statistics(request):
    """TTS使用统计"""
    user = request.user
    
    # 获取使用统计
    total_usage = TTSUsageLog.objects.filter(user=user).count()
    successful_usage = TTSUsageLog.objects.filter(user=user, success=True).count()
    
    # 最常用的语音
    popular_voices = TTSUsageLog.objects.filter(
        user=user, success=True
    ).values(
        'voice__display_name', 'voice__language_name'
    ).annotate(
        usage_count=Count('id')
    ).order_by('-usage_count')[:5]
    
    # 最近使用记录
    recent_usage = TTSUsageLog.objects.filter(
        user=user
    ).select_related('voice', 'book').order_by('-created_at')[:10]
    
    # 按日期统计使用量
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    daily_usage = TTSUsageLog.objects.filter(
        user=user,
        created_at__date__range=[start_date, end_date]
    ).annotate(
        day=TruncDate('created_at')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    context = {
        'total_usage': total_usage,
        'successful_usage': successful_usage,
        'success_rate': (successful_usage / total_usage * 100) if total_usage > 0 else 0,
        'popular_voices': popular_voices,
        'recent_usage': recent_usage,
        'daily_usage': daily_usage,
    }
    
    return render(request, 'tts_service/usage_statistics.html', context) 