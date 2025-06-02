from django.shortcuts import render
from django.http import JsonResponse
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

from .services import ChatTTSService
from .models import ChatTTSCache, ChatTTSRequest, TTSSpeaker, TTSSettings

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