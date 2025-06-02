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

from .services import TranslationService
from .models import TranslationCache, TranslationRequest, TranslationHistory, LanguagePair

logger = logging.getLogger(__name__)


class TranslationAPIView(View):
    """翻译API视图"""
    
    def __init__(self):
        super().__init__()
        self.translation_service = TranslationService()
    
    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        """翻译文本"""
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            target_language = data.get('target_language', 'zh')
            source_language = data.get('source_language', 'auto')
            model = data.get('model')
            use_cache = data.get('use_cache', True)
            
            if not text:
                return JsonResponse({
                    'success': False,
                    'error': '文本不能为空'
                }, status=400)
            
            # 检查文本长度
            if len(text) > 10000:
                return JsonResponse({
                    'success': False,
                    'error': '文本长度不能超过10000字符'
                }, status=400)
            
            # 翻译文本
            result = self.translation_service.translate_text(
                text=text,
                target_language=target_language,
                source_language=source_language,
                model=model,
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
            logger.error(f"翻译API错误: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': '服务器内部错误'
            }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_translate(request):
    """批量翻译"""
    try:
        texts = request.data.get('texts', [])
        target_language = request.data.get('target_language', 'zh')
        source_language = request.data.get('source_language', 'auto')
        model = request.data.get('model')
        
        if not texts or not isinstance(texts, list):
            return Response({
                'success': False,
                'error': '请提供有效的文本列表'
            }, status=400)
        
        if len(texts) > 50:
            return Response({
                'success': False,
                'error': '批量翻译最多支持50条文本'
            }, status=400)
        
        translation_service = TranslationService()
        results = translation_service.batch_translate(
            texts=texts,
            target_language=target_language,
            source_language=source_language,
            model=model,
            user=request.user
        )
        
        return Response({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"批量翻译失败: {str(e)}")
        return Response({
            'success': False,
            'error': '批量翻译失败'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def supported_languages(request):
    """获取支持的语言列表"""
    try:
        translation_service = TranslationService()
        languages = translation_service.get_supported_languages()
        
        return Response({
            'success': True,
            'languages': languages
        })
        
    except Exception as e:
        logger.error(f"获取语言列表失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取语言列表失败'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def popular_language_pairs(request):
    """获取热门语言对"""
    try:
        limit = int(request.GET.get('limit', 10))
        translation_service = TranslationService()
        pairs = translation_service.get_popular_language_pairs(limit)
        
        return Response({
            'success': True,
            'language_pairs': pairs
        })
        
    except Exception as e:
        logger.error(f"获取热门语言对失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取热门语言对失败'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_language(request):
    """检测文本语言"""
    try:
        text = request.data.get('text', '').strip()
        
        if not text:
            return Response({
                'success': False,
                'error': '文本不能为空'
            }, status=400)
        
        translation_service = TranslationService()
        detected_language = translation_service.detect_language(text)
        
        # 获取语言名称
        languages = translation_service.get_supported_languages()
        language_name = languages.get(detected_language, detected_language)
        
        return Response({
            'success': True,
            'detected_language': detected_language,
            'language_name': language_name
        })
        
    except Exception as e:
        logger.error(f"语言检测失败: {str(e)}")
        return Response({
            'success': False,
            'error': '语言检测失败'
        }, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_settings(request):
    """用户翻译设置"""
    try:
        translation_service = TranslationService()
        
        if request.method == 'GET':
            # 获取用户设置
            settings = translation_service.get_user_settings(request.user)
            return Response({
                'success': True,
                'settings': settings
            })
        
        elif request.method == 'POST':
            # 更新用户设置
            settings_data = request.data
            success = translation_service.update_user_settings(request.user, settings_data)
            
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
        logger.error(f"翻译设置操作失败: {str(e)}")
        return Response({
            'success': False,
            'error': '操作失败'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def translation_history(request):
    """获取翻译历史"""
    try:
        limit = int(request.GET.get('limit', 50))
        translation_service = TranslationService()
        history = translation_service.get_translation_history(request.user, limit)
        
        return Response({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"获取翻译历史失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取翻译历史失败'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request):
    """切换收藏状态"""
    try:
        history_id = request.data.get('history_id')
        
        if not history_id:
            return Response({
                'success': False,
                'error': '请提供历史记录ID'
            }, status=400)
        
        try:
            history_item = TranslationHistory.objects.get(
                id=history_id,
                user=request.user
            )
            history_item.is_favorite = not history_item.is_favorite
            history_item.save()
            
            return Response({
                'success': True,
                'is_favorite': history_item.is_favorite,
                'message': '收藏状态已更新'
            })
            
        except TranslationHistory.DoesNotExist:
            return Response({
                'success': False,
                'error': '历史记录不存在'
            }, status=404)
        
    except Exception as e:
        logger.error(f"切换收藏状态失败: {str(e)}")
        return Response({
            'success': False,
            'error': '操作失败'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_history(request):
    """获取翻译请求历史"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        requests = TranslationRequest.objects.filter(
            user=request.user
        ).order_by('-created_at')[start:end]
        
        total = TranslationRequest.objects.filter(user=request.user).count()
        
        history = []
        for req in requests:
            history.append({
                'id': req.id,
                'source_text': req.source_text[:100] + '...' if len(req.source_text) > 100 else req.source_text,
                'translated_text': req.translated_text[:100] + '...' if req.translated_text and len(req.translated_text) > 100 else req.translated_text,
                'source_language': req.source_language,
                'target_language': req.target_language,
                'translation_model': req.translation_model,
                'status': req.status,
                'error_message': req.error_message,
                'processing_time': req.processing_time,
                'confidence_score': req.confidence_score,
                'created_at': req.created_at.isoformat(),
                'completed_at': req.completed_at.isoformat() if req.completed_at else None
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
        logger.error(f"获取翻译请求历史失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取历史记录失败'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cleanup_cache(request):
    """清理翻译缓存"""
    try:
        days = int(request.data.get('days', 30))
        translation_service = TranslationService()
        result = translation_service.cleanup_cache(days)
        
        return Response({
            'success': True,
            'message': f'清理完成，删除了{result["deleted_records"]}条记录',
            'deleted_records': result['deleted_records']
        })
        
    except Exception as e:
        logger.error(f"清理翻译缓存失败: {str(e)}")
        return Response({
            'success': False,
            'error': '清理缓存失败'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cache_stats(request):
    """获取缓存统计信息"""
    try:
        total_cache = TranslationCache.objects.count()
        user_requests = TranslationRequest.objects.filter(user=request.user).count()
        user_history = TranslationHistory.objects.filter(user=request.user).count()
        
        # 获取最近的缓存
        recent_cache = TranslationCache.objects.order_by('-created_at')[:10]
        
        cache_list = []
        for cache in recent_cache:
            cache_list.append({
                'source_language': cache.source_language,
                'target_language': cache.target_language,
                'translation_model': cache.translation_model,
                'confidence_score': cache.confidence_score,
                'access_count': cache.access_count,
                'created_at': cache.created_at.isoformat()
            })
        
        return Response({
            'success': True,
            'stats': {
                'total_cache': total_cache,
                'user_requests': user_requests,
                'user_history': user_history,
                'recent_cache': cache_list
            }
        })
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取统计信息失败'
        }, status=500) 