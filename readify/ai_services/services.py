import openai
import time
import logging
import requests
import json
from typing import Dict, Any, Optional
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from .models import AITask, AIModel
from readify.books.models import Book, BookContent

logger = logging.getLogger(__name__)


class AIService:
    """AI服务类 - 支持多种AI提供商"""
    
    def __init__(self, user: User = None):
        self.user = user
        # 不在初始化时缓存配置，每次使用时重新获取
        self._config = None
    
    @property
    def config(self):
        """动态获取配置，确保总是最新的"""
        return self._get_user_config()
    
    def _get_user_config(self):
        """获取用户AI配置"""
        if not self.user:
            # 使用默认配置
            return {
                'provider': 'openai',
                'api_url': getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'api_key': getattr(settings, 'OPENAI_API_KEY', ''),
                'model_id': getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
                'max_tokens': 4000,
                'temperature': 0.7,
                'timeout': 30
            }
        
        try:
            from readify.user_management.models import UserAIConfig
            # 每次都重新查询数据库，确保获取最新配置
            user_config = UserAIConfig.objects.get(user=self.user, is_active=True)
            
            # 构建配置字典
            config = {
                'provider': user_config.provider,
                'api_url': user_config.api_url,
                'api_key': user_config.api_key,
                'model_id': user_config.model_id,
                'max_tokens': user_config.max_tokens,
                'temperature': user_config.temperature,
                'timeout': user_config.timeout,
            }
            
            # 添加headers和endpoint
            config['headers'] = user_config.get_headers()
            config['endpoint'] = user_config.get_chat_endpoint()
            
            logger.info(f"使用用户自定义AI配置: {user_config.provider} - {user_config.model_id} (ID: {user_config.id})")
            return config
            
        except UserAIConfig.DoesNotExist:
            logger.warning(f"用户 {self.user.username} 没有AI配置，使用默认配置")
            # 如果没有配置，使用默认配置
            return {
                'provider': 'openai',
                'api_url': getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'api_key': getattr(settings, 'OPENAI_API_KEY', ''),
                'model_id': getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
                'max_tokens': 4000,
                'temperature': 0.7,
                'timeout': 30
            }
        except Exception as e:
            logger.error(f"获取用户AI配置失败: {str(e)}")
            # 如果出错，使用默认配置
            return {
                'provider': 'openai',
                'api_url': getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'api_key': getattr(settings, 'OPENAI_API_KEY', ''),
                'model_id': getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
                'max_tokens': 4000,
                'temperature': 0.7,
                'timeout': 30
            }
    
    def _make_api_request(self, messages: list, system_prompt: str = None) -> Dict[str, Any]:
        """通用API请求方法"""
        try:
            start_time = time.time()
            
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            # 根据提供商构建请求数据
            if self.config['provider'] == 'anthropic':
                data = self._build_anthropic_request(messages)
            elif self.config['provider'] == 'google':
                data = self._build_google_request(messages)
            else:  # openai, azure, custom
                data = self._build_openai_request(messages)
            
            # 获取端点和请求头
            endpoint = self.config.get('endpoint')
            if not endpoint:
                endpoint = f"{self.config['api_url'].rstrip('/')}/chat/completions"
            
            headers = self.config.get('headers')
            if not headers:
                headers = {
                    'Authorization': f"Bearer {self.config['api_key']}", 
                    'Content-Type': 'application/json'
                }
            
            # 记录请求信息（不包含敏感信息）
            logger.info(f"发送AI请求到: {endpoint}")
            logger.info(f"模型: {self.config['model_id']}")
            logger.info(f"提供商: {self.config['provider']}")
            logger.info(f"用户: {self.user.username if self.user else '默认'}")
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=self.config['timeout']
            )
            
            # 详细的错误信息
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    if 'error' in error_json:
                        error_detail += f": {error_json['error'].get('message', '未知错误')}"
                    else:
                        error_detail += f": {error_json}"
                except:
                    error_detail += f": {response.text[:200]}"
                
                logger.error(f"API请求失败: {error_detail}")
                logger.error(f"请求端点: {endpoint}")
                logger.error(f"请求头: {dict(headers)}")  # 记录请求头（但不记录敏感信息）
                
                return {
                    'success': False,
                    'error': f'API请求失败: {error_detail}'
                }
            
            result = response.json()
            processing_time = time.time() - start_time
            
            # 解析响应
            content, tokens_used = self._parse_response(result)
            
            logger.info(f"AI请求成功，处理时间: {processing_time:.2f}秒，使用令牌: {tokens_used}")
            
            return {
                'success': True,
                'content': content,
                'processing_time': processing_time,
                'tokens_used': tokens_used
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"请求超时（{self.config['timeout']}秒）"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到API服务器: {self.config['api_url']}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            return {
                'success': False,
                'error': f'API请求失败: {str(e)}'
            }
        except Exception as e:
            logger.error(f"AI服务错误: {str(e)}")
            return {
                'success': False,
                'error': f'AI服务错误: {str(e)}'
            }
    
    def _build_openai_request(self, messages: list) -> dict:
        """构建OpenAI格式的请求"""
        return {
            'model': self.config['model_id'],
            'messages': messages,
            'max_tokens': self.config['max_tokens'],
            'temperature': self.config['temperature']
        }
    
    def _build_anthropic_request(self, messages: list) -> dict:
        """构建Anthropic格式的请求"""
        # Anthropic使用不同的消息格式
        system_msg = None
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_msg = msg['content']
            else:
                user_messages.append(msg)
        
        data = {
            'model': self.config['model_id'],
            'max_tokens': self.config['max_tokens'],
            'temperature': self.config['temperature'],
            'messages': user_messages
        }
        
        if system_msg:
            data['system'] = system_msg
        
        return data
    
    def _build_google_request(self, messages: list) -> dict:
        """构建Google格式的请求"""
        # Google使用不同的格式
        contents = []
        for msg in messages:
            if msg['role'] == 'system':
                continue  # Google在contents中不支持system角色
            role = 'user' if msg['role'] == 'user' else 'model'
            contents.append({
                'role': role,
                'parts': [{'text': msg['content']}]
            })
        
        return {
            'contents': contents,
            'generationConfig': {
                'maxOutputTokens': self.config['max_tokens'],
                'temperature': self.config['temperature']
            }
        }
    
    def _parse_response(self, result: dict) -> tuple:
        """解析API响应"""
        content = ""
        tokens_used = 0
        
        if self.config['provider'] == 'anthropic':
            if 'content' in result and result['content']:
                content = result['content'][0].get('text', '')
            if 'usage' in result:
                tokens_used = result['usage'].get('output_tokens', 0)
        elif self.config['provider'] == 'google':
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    content = candidate['content']['parts'][0].get('text', '')
            if 'usageMetadata' in result:
                tokens_used = result['usageMetadata'].get('totalTokenCount', 0)
        else:  # openai, azure, custom
            if 'choices' in result and result['choices']:
                content = result['choices'][0]['message']['content']
            if 'usage' in result:
                tokens_used = result['usage'].get('total_tokens', 0)
        
        return content, tokens_used
    
    def generate_summary(self, book) -> Dict[str, Any]:
        """生成书籍摘要"""
        try:
            # 获取书籍内容
            content = self._get_book_content(book)
            if not content:
                return {'success': False, 'error': '无法获取书籍内容'}
            
            # 限制内容长度
            if len(content) > 8000:
                content = content[:8000] + "..."
            
            messages = [
                {
                    "role": "user",
                    "content": f"请为以下书籍内容生成一个详细的摘要，包括主要观点、核心内容和关键信息：\n\n{content}"
                }
            ]
            
            system_prompt = "你是一个专业的文本摘要助手，能够准确提取文本的核心内容并生成简洁明了的摘要。"
            
            result = self._make_api_request(messages, system_prompt)
            
            if result['success']:
                return {
                    'success': True,
                    'summary': result['content'],
                    'processing_time': result['processing_time'],
                    'tokens_used': result['tokens_used']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"生成摘要失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def answer_question(self, book, question: str) -> Dict[str, Any]:
        """回答关于书籍的问题"""
        try:
            # 获取书籍内容
            content = self._get_book_content(book)
            if not content:
                return {'success': False, 'error': '无法获取书籍内容'}
            
            # 限制内容长度
            if len(content) > 6000:
                content = content[:6000] + "..."
            
            messages = [
                {
                    "role": "user",
                    "content": f"基于以下书籍内容，请回答问题：{question}\n\n书籍内容：\n{content}"
                }
            ]
            
            system_prompt = "你是一个专业的阅读助手，能够基于提供的书籍内容准确回答用户的问题。请确保回答准确、详细且有帮助。"
            
            result = self._make_api_request(messages, system_prompt)
            
            if result['success']:
                return {
                    'success': True,
                    'answer': result['content'],
                    'processing_time': result['processing_time'],
                    'tokens_used': result['tokens_used']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"回答问题失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def extract_keywords(self, book) -> Dict[str, Any]:
        """提取书籍关键词"""
        try:
            # 获取书籍内容
            content = self._get_book_content(book)
            if not content:
                return {'success': False, 'error': '无法获取书籍内容'}
            
            # 限制内容长度
            if len(content) > 6000:
                content = content[:6000] + "..."
            
            messages = [
                {
                    "role": "user",
                    "content": f"请从以下书籍内容中提取10-15个最重要的关键词，用逗号分隔：\n\n{content}"
                }
            ]
            
            system_prompt = "你是一个专业的关键词提取助手，能够准确识别文本中的核心概念和重要术语。"
            
            result = self._make_api_request(messages, system_prompt)
            
            if result['success']:
                # 解析关键词
                keywords_text = result['content'].strip()
                keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
                
                return {
                    'success': True,
                    'keywords': keywords,
                    'processing_time': result['processing_time'],
                    'tokens_used': result['tokens_used']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"提取关键词失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def analyze_text(self, text: str, analysis_type: str = 'general') -> Dict[str, Any]:
        """分析文本"""
        try:
            if analysis_type == 'sentiment':
                prompt = f"请分析以下文本的情感倾向（积极、消极、中性）并给出详细解释：\n\n{text}"
            elif analysis_type == 'structure':
                prompt = f"请分析以下文本的结构和组织方式：\n\n{text}"
            elif analysis_type == 'style':
                prompt = f"请分析以下文本的写作风格和特点：\n\n{text}"
            else:  # general
                prompt = f"请对以下文本进行全面分析，包括主题、结构、风格等方面：\n\n{text}"
            
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "你是一个专业的文本分析师，能够从多个角度深入分析文本内容。"
            
            result = self._make_api_request(messages, system_prompt)
            
            if result['success']:
                return {
                    'success': True,
                    'analysis': result['content'],
                    'processing_time': result['processing_time'],
                    'tokens_used': result['tokens_used']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"文本分析失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_book_content(self, book) -> str:
        """获取书籍内容"""
        try:
            from readify.books.models import BookContent
            
            # 获取书籍的所有章节内容
            chapters = BookContent.objects.filter(book=book).order_by('chapter_number')
            
            if chapters.exists():
                # 如果有章节内容，合并所有章节
                content_parts = []
                for chapter in chapters[:5]:  # 限制前5章
                    content_parts.append(f"第{chapter.chapter_number}章 {chapter.title}\n{chapter.content}")
                return "\n\n".join(content_parts)
            else:
                # 如果没有章节内容，返回书籍描述
                return book.description or f"书名：{book.title}\n作者：{book.author}"
                
        except Exception as e:
            logger.error(f"获取书籍内容失败: {str(e)}")
            return ""

    def generate_book_summary(self, book_id, user):
        """生成书籍摘要"""
        try:
            book = Book.objects.get(id=book_id, user=user)
            
            # 创建AI任务
            task = AITask.objects.create(
                user=user,
                task_type='summary',
                input_data={'book_id': book_id}
            )
            
            # 获取书籍内容
            contents = BookContent.objects.filter(book=book).order_by('chapter_number')
            
            if not contents.exists():
                task.status = 'failed'
                task.error_message = '书籍内容未找到'
                task.save()
                return task
            
            # 准备内容文本
            full_text = ""
            for content in contents[:5]:  # 只取前5章进行摘要
                full_text += f"第{content.chapter_number}章: {content.chapter_title}\n"
                full_text += content.content[:2000] + "\n\n"  # 限制每章字数
            
            # 调用AI生成摘要
            task.status = 'processing'
            task.started_at = timezone.now()
            task.save()
            
            prompt = f"""
            请为以下书籍内容生成一个详细的摘要，包括：
            1. 主要内容概述
            2. 核心观点和主题
            3. 关键信息提取
            4. 适合的读者群体
            
            书籍标题：{book.title}
            作者：{book.author}
            
            内容：
            {full_text}
            
            请用中文回答，字数控制在500-800字之间。
            """
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的图书分析师，擅长提取书籍的核心内容并生成高质量的摘要。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content
            
            # 更新书籍摘要
            book.summary = summary
            book.processing_status = 'completed'
            book.save()
            
            # 更新任务状态
            task.status = 'completed'
            task.output_data = {'summary': summary}
            task.completed_at = timezone.now()
            task.save()
            
            return task
            
        except Exception as e:
            logger.error(f"生成书籍摘要失败: {str(e)}")
            if 'task' in locals():
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_at = timezone.now()
                task.save()
            raise e
    
    def extract_keywords(self, book_id, user):
        """提取书籍关键词"""
        try:
            book = Book.objects.get(id=book_id, user=user)
            
            # 创建AI任务
            task = AITask.objects.create(
                user=user,
                task_type='keyword_extraction',
                input_data={'book_id': book_id}
            )
            
            # 使用书籍摘要或内容提取关键词
            text_for_keywords = book.summary if book.summary else ""
            
            if not text_for_keywords:
                # 如果没有摘要，使用前几章内容
                contents = BookContent.objects.filter(book=book).order_by('chapter_number')[:3]
                text_for_keywords = " ".join([content.content[:1000] for content in contents])
            
            if not text_for_keywords:
                task.status = 'failed'
                task.error_message = '没有可用的文本内容'
                task.save()
                return task
            
            task.status = 'processing'
            task.started_at = timezone.now()
            task.save()
            
            prompt = f"""
            请从以下文本中提取10-15个最重要的关键词，这些关键词应该能够代表文本的核心主题和概念。
            
            书籍标题：{book.title}
            
            文本内容：
            {text_for_keywords}
            
            请以JSON格式返回关键词列表，例如：["关键词1", "关键词2", "关键词3"]
            """
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的文本分析师，擅长提取文本的关键词和核心概念。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            keywords_text = response.choices[0].message.content
            
            # 尝试解析JSON格式的关键词
            try:
                import json
                keywords = json.loads(keywords_text)
            except:
                # 如果解析失败，使用简单的文本分割
                keywords = [kw.strip().strip('"') for kw in keywords_text.split(',')]
            
            # 更新书籍关键词
            book.keywords = keywords
            book.save()
            
            # 更新任务状态
            task.status = 'completed'
            task.output_data = {'keywords': keywords}
            task.completed_at = timezone.now()
            task.save()
            
            return task
            
        except Exception as e:
            logger.error(f"提取关键词失败: {str(e)}")
            if 'task' in locals():
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_at = timezone.now()
                task.save()
            raise e 