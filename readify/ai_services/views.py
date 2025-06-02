from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from .services import AIService
from .models import AIRequest, AIResponse
from readify.books.models import Book

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def generate_summary(request):
    """生成书籍摘要"""
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        if not book_id:
            return JsonResponse({
                'success': False,
                'message': '请提供书籍ID'
            }, status=400)
        
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        # 创建AI请求记录
        ai_request = AIRequest.objects.create(
            user=request.user,
            book=book,
            request_type='summary',
            input_text=f'为书籍《{book.title}》生成摘要'
        )
        
        # 调用AI服务（传入用户）
        ai_service = AIService(user=request.user)
        result = ai_service.generate_summary(book)
        
        if result['success']:
            # 保存AI响应
            ai_response = AIResponse.objects.create(
                request=ai_request,
                response_text=result['summary'],
                processing_time=result.get('processing_time', 0),
                tokens_used=result.get('tokens_used', 0)
            )
            
            ai_request.status = 'completed'
            ai_request.save()
            
            return JsonResponse({
                'success': True,
                'summary': result['summary'],
                'processing_time': result.get('processing_time', 0)
            })
        else:
            ai_request.status = 'failed'
            ai_request.error_message = result.get('error', '未知错误')
            ai_request.save()
            
            return JsonResponse({
                'success': False,
                'message': result.get('error', '摘要生成失败')
            }, status=500)
            
    except Exception as e:
        logger.error(f"生成摘要失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '服务器内部错误'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def ask_question(request):
    """AI问答"""
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        question = data.get('question', '').strip()
        
        if not book_id or not question:
            return JsonResponse({
                'success': False,
                'message': '请提供书籍ID和问题'
            }, status=400)
        
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        # 创建AI请求记录
        ai_request = AIRequest.objects.create(
            user=request.user,
            book=book,
            request_type='question',
            input_text=question
        )
        
        # 调用AI服务（传入用户）
        ai_service = AIService(user=request.user)
        result = ai_service.answer_question(book, question)
        
        if result['success']:
            # 保存AI响应
            ai_response = AIResponse.objects.create(
                request=ai_request,
                response_text=result['answer'],
                processing_time=result.get('processing_time', 0),
                tokens_used=result.get('tokens_used', 0)
            )
            
            ai_request.status = 'completed'
            ai_request.save()
            
            return JsonResponse({
                'success': True,
                'answer': result['answer'],
                'processing_time': result.get('processing_time', 0)
            })
        else:
            ai_request.status = 'failed'
            ai_request.error_message = result.get('error', '未知错误')
            ai_request.save()
            
            return JsonResponse({
                'success': False,
                'message': result.get('error', '回答生成失败')
            }, status=500)
            
    except Exception as e:
        logger.error(f"AI问答失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '服务器内部错误'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def extract_keywords(request):
    """提取关键词"""
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        if not book_id:
            return JsonResponse({
                'success': False,
                'message': '请提供书籍ID'
            }, status=400)
        
        book = get_object_or_404(Book, id=book_id, user=request.user)
        
        # 创建AI请求记录
        ai_request = AIRequest.objects.create(
            user=request.user,
            book=book,
            request_type='keywords',
            input_text=f'为书籍《{book.title}》提取关键词'
        )
        
        # 调用AI服务（传入用户）
        ai_service = AIService(user=request.user)
        result = ai_service.extract_keywords(book)
        
        if result['success']:
            # 保存AI响应
            ai_response = AIResponse.objects.create(
                request=ai_request,
                response_text=', '.join(result['keywords']),
                processing_time=result.get('processing_time', 0),
                tokens_used=result.get('tokens_used', 0)
            )
            
            ai_request.status = 'completed'
            ai_request.save()
            
            return JsonResponse({
                'success': True,
                'keywords': result['keywords'],
                'processing_time': result.get('processing_time', 0)
            })
        else:
            ai_request.status = 'failed'
            ai_request.error_message = result.get('error', '未知错误')
            ai_request.save()
            
            return JsonResponse({
                'success': False,
                'message': result.get('error', '关键词提取失败')
            }, status=500)
            
    except Exception as e:
        logger.error(f"关键词提取失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '服务器内部错误'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def analyze_text(request):
    """文本分析"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        analysis_type = data.get('type', 'general')
        
        if not text:
            return JsonResponse({
                'success': False,
                'message': '请提供要分析的文本'
            }, status=400)
        
        # 创建AI请求记录
        ai_request = AIRequest.objects.create(
            user=request.user,
            request_type='analysis',
            input_text=text
        )
        
        # 调用AI服务（传入用户）
        ai_service = AIService(user=request.user)
        result = ai_service.analyze_text(text, analysis_type)
        
        if result['success']:
            # 保存AI响应
            ai_response = AIResponse.objects.create(
                request=ai_request,
                response_text=result['analysis'],
                processing_time=result.get('processing_time', 0),
                tokens_used=result.get('tokens_used', 0)
            )
            
            ai_request.status = 'completed'
            ai_request.save()
            
            return JsonResponse({
                'success': True,
                'analysis': result['analysis'],
                'processing_time': result.get('processing_time', 0)
            })
        else:
            ai_request.status = 'failed'
            ai_request.error_message = result.get('error', '未知错误')
            ai_request.save()
            
            return JsonResponse({
                'success': False,
                'message': result.get('error', '文本分析失败')
            }, status=500)
            
    except Exception as e:
        logger.error(f"文本分析失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '服务器内部错误'
        }, status=500)


@login_required
def ai_history(request):
    """AI服务历史记录"""
    requests = AIRequest.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    history = []
    for req in requests:
        item = {
            'id': req.id,
            'type': req.request_type,
            'input_text': req.input_text[:100] + '...' if len(req.input_text) > 100 else req.input_text,
            'status': req.status,
            'created_at': req.created_at.isoformat(),
            'book_title': req.book.title if req.book else None
        }
        
        if req.status == 'completed' and hasattr(req, 'response'):
            item['response_text'] = req.response.response_text[:200] + '...' if len(req.response.response_text) > 200 else req.response.response_text
            item['processing_time'] = req.response.processing_time
        
        history.append(item)
    
    return JsonResponse({
        'success': True,
        'history': history
    })


@login_required
@require_http_methods(["POST"])
def clear_history(request):
    """清理AI服务历史记录"""
    try:
        days = int(request.POST.get('days', 30))
        
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = AIRequest.objects.filter(
            user=request.user,
            created_at__lt=cutoff_date
        ).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'已删除{deleted_count}条历史记录'
        })
        
    except Exception as e:
        logger.error(f"清理历史记录失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '清理失败'
        }, status=500)


# AI配置管理视图
@login_required
@require_http_methods(["GET", "POST"])
def ai_config(request):
    """AI配置管理"""
    from readify.user_management.models import UserAIConfig
    
    if request.method == 'GET':
        try:
            config = UserAIConfig.objects.get(user=request.user)
            return JsonResponse({
                'success': True,
                'config': {
                    'provider': config.provider,
                    'api_url': config.api_url,
                    'model_id': config.model_id,
                    'max_tokens': config.max_tokens,
                    'temperature': config.temperature,
                    'timeout': config.timeout,
                    'is_active': config.is_active
                }
            })
        except UserAIConfig.DoesNotExist:
            return JsonResponse({
                'success': True,
                'config': {
                    'provider': 'openai',
                    'api_url': 'https://api.openai.com/v1',
                    'model_id': 'gpt-3.5-turbo',
                    'max_tokens': 4000,
                    'temperature': 0.7,
                    'timeout': 30,
                    'is_active': False
                }
            })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            config, created = UserAIConfig.objects.get_or_create(
                user=request.user,
                defaults={
                    'provider': data.get('provider', 'openai'),
                    'api_url': data.get('api_url', 'https://api.openai.com/v1'),
                    'api_key': data.get('api_key', ''),
                    'model_id': data.get('model_id', 'gpt-3.5-turbo'),
                    'max_tokens': int(data.get('max_tokens', 4000)),
                    'temperature': float(data.get('temperature', 0.7)),
                    'timeout': int(data.get('timeout', 30)),
                    'is_active': data.get('is_active', True)
                }
            )
            
            if not created:
                # 更新现有配置
                config.provider = data.get('provider', config.provider)
                config.api_url = data.get('api_url', config.api_url)
                if data.get('api_key'):  # 只有提供了新密钥才更新
                    config.api_key = data.get('api_key')
                config.model_id = data.get('model_id', config.model_id)
                config.max_tokens = int(data.get('max_tokens', config.max_tokens))
                config.temperature = float(data.get('temperature', config.temperature))
                config.timeout = int(data.get('timeout', config.timeout))
                config.is_active = data.get('is_active', config.is_active)
                config.save()
            
            return JsonResponse({
                'success': True,
                'message': '配置保存成功'
            })
            
        except Exception as e:
            logger.error(f"保存AI配置失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'保存失败: {str(e)}'
            }, status=500)


@login_required
@require_http_methods(["POST"])
def test_ai_config(request):
    """测试AI配置"""
    try:
        ai_service = AIService(user=request.user)
        
        # 发送测试请求
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回复'配置测试成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': '配置测试成功',
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