import time
import logging
import hashlib
from typing import Optional, Dict, Any, List
import openai
import requests
import re
from django.conf import settings
from django.utils import timezone
from langdetect import detect, DetectorFactory
import json

from .models import (
    TranslationCache, TranslationRequest, TranslationSettings, 
    LanguagePair, TranslationHistory
)

# 设置langdetect的随机种子，确保结果一致性
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)


class TranslationService:
    """翻译服务类"""
    
    def __init__(self):
        # 检查是否使用Qwen模型
        self.default_model = getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        self.api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.base_url = getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        # 判断是否为Qwen模型
        self.is_qwen_model = 'Qwen' in self.default_model
        
        if self.is_qwen_model:
            # 使用自定义API
            self.client = None
            logger.info(f"使用Qwen模型: {self.default_model}")
        else:
            # 使用OpenAI客户端
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"使用OpenAI模型: {self.default_model}")
        
        self.supported_languages = getattr(settings, 'TRANSLATION_SUPPORTED_LANGUAGES', {
            'zh': '中文',
            'en': '英文',
            'ja': '日文',
            'ko': '韩文',
            'fr': '法文',
            'de': '德文',
            'es': '西班牙文',
            'it': '意大利文',
            'ru': '俄文',
            'ar': '阿拉伯文',
            'hi': '印地文',
            'pt': '葡萄牙文',
            'th': '泰文',
            'vi': '越南文'
        })
        
        # 语言检测映射
        self.language_mapping = {
            'zh-cn': 'zh',
            'zh-hans': 'zh',
            'zh-hant': 'zh',
            'zh-tw': 'zh',
            'en': 'en',
            'ja': 'ja',
            'ko': 'ko',
            'fr': 'fr',
            'de': 'de',
            'es': 'es',
            'it': 'it',
            'ru': 'ru',
            'ar': 'ar',
            'hi': 'hi',
            'pt': 'pt',
            'th': 'th',
            'vi': 'vi',
        }
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        try:
            # 清理文本
            clean_text = text.strip()
            if not clean_text:
                return 'zh'
            
            # 使用langdetect检测
            detected = detect(clean_text)
            return self.language_mapping.get(detected, detected)
            
        except Exception as e:
            logger.warning(f"语言检测失败: {str(e)}")
            return 'zh'  # 默认返回中文
    
    def _get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """生成缓存键"""
        content = f"{text}_{source_lang}_{target_lang}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cached_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[TranslationCache]:
        """获取缓存的翻译"""
        try:
            cache_key = self._get_cache_key(text, source_lang, target_lang)
            cache_obj = TranslationCache.objects.get(text_hash=cache_key)
            cache_obj.update_access()
            return cache_obj
        except TranslationCache.DoesNotExist:
            return None
    
    def _save_to_cache(self, text: str, source_lang: str, target_lang: str, 
                      translated_text: str, model: str, confidence: float = None) -> TranslationCache:
        """保存翻译到缓存"""
        try:
            cache_key = self._get_cache_key(text, source_lang, target_lang)
            
            cache_obj = TranslationCache.objects.create(
                text_hash=cache_key,
                source_language=source_lang,
                target_language=target_lang,
                source_text=text,
                translated_text=translated_text,
                translation_model=model,
                confidence_score=confidence
            )
            
            return cache_obj
            
        except Exception as e:
            logger.error(f"保存翻译缓存失败: {str(e)}")
            raise
    
    def _create_translation_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        """创建翻译提示词"""
        source_name = self.supported_languages.get(source_lang, source_lang)
        target_name = self.supported_languages.get(target_lang, target_lang)
        
        prompt = f"""请将以下{source_name}文本翻译成{target_name}。

要求：
1. 保持原文的语气和风格
2. 确保翻译准确、自然、流畅
3. 保留专业术语的准确性
4. 如果是文学作品，保持文学性
5. 只返回翻译结果，不要添加任何解释

原文：
{text}

翻译："""
        
        return prompt
    
    def _clean_qwen_response(self, text: str) -> str:
        """清理Qwen模型响应中的思考标签和多余内容"""
        if not text:
            return text
        
        # 移除<think>...</think>标签及其内容
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        # 移除其他可能的标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 清理多余的空白字符
        text = re.sub(r'\n\s*\n', '\n', text)
        text = text.strip()
        
        return text
    
    def _call_ai_translation(self, text: str, source_lang: str, target_lang: str, 
                           model: str = None) -> Dict[str, Any]:
        """调用AI进行翻译"""
        try:
            if not model:
                model = self.default_model
            
            prompt = self._create_translation_prompt(text, source_lang, target_lang)
            
            if self.is_qwen_model:
                # 使用自定义API调用Qwen模型
                return self._call_qwen_translation(text, source_lang, target_lang, model, prompt)
            else:
                # 使用OpenAI客户端
                return self._call_openai_translation(text, source_lang, target_lang, model, prompt)
            
        except Exception as e:
            logger.error(f"AI翻译失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _call_qwen_translation(self, text: str, source_lang: str, target_lang: str, 
                              model: str, prompt: str) -> Dict[str, Any]:
        """调用Qwen模型进行翻译"""
        try:
            # 构建请求
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            data = {
                'model': model,
                'messages': [
                    {
                        "role": "system",
                        "content": "你是一个专业的翻译助手，能够准确翻译各种语言的文本，保持原文的语气、风格和含义。请只返回翻译结果，不要添加任何解释、思考过程或额外内容。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                'temperature': 0.1,  # 降低温度以获得更稳定的输出
                'max_tokens': 4000,
                'stream': False
            }
            
            # 发送请求
            endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
            logger.info(f"发送Qwen翻译请求到: {endpoint}")
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code != 200:
                error_msg = f"Qwen API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                raise Exception("Qwen API响应格式错误：缺少choices字段")
            
            translated_text = result['choices'][0]['message']['content'].strip()
            
            # 清理Qwen模型的响应
            translated_text = self._clean_qwen_response(translated_text)
            
            # 简单的质量评估
            confidence = self._estimate_translation_quality(text, translated_text, source_lang, target_lang)
            
            logger.info(f"Qwen翻译成功，模型: {model}")
            
            return {
                'success': True,
                'translated_text': translated_text,
                'confidence': confidence,
                'model': model
            }
            
        except Exception as e:
            logger.error(f"Qwen翻译失败: {str(e)}")
            raise e
    
    def _call_openai_translation(self, text: str, source_lang: str, target_lang: str, 
                                model: str, prompt: str) -> Dict[str, Any]:
        """调用OpenAI模型进行翻译"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的翻译助手，能够准确翻译各种语言的文本，保持原文的语气、风格和含义。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # 简单的质量评估
            confidence = self._estimate_translation_quality(text, translated_text, source_lang, target_lang)
            
            logger.info(f"OpenAI翻译成功，模型: {model}")
            
            return {
                'success': True,
                'translated_text': translated_text,
                'confidence': confidence,
                'model': model
            }
            
        except Exception as e:
            logger.error(f"OpenAI翻译失败: {str(e)}")
            raise e
    
    def _estimate_translation_quality(self, source_text: str, translated_text: str, 
                                    source_lang: str, target_lang: str) -> float:
        """估算翻译质量"""
        try:
            # 简单的质量评估逻辑
            score = 0.8  # 基础分数
            
            # 长度比例检查
            length_ratio = len(translated_text) / len(source_text) if len(source_text) > 0 else 0
            if 0.5 <= length_ratio <= 2.0:
                score += 0.1
            
            # 检查是否包含原文（可能翻译失败）
            if source_text.strip() in translated_text:
                score -= 0.3
            
            # 检查是否为空或过短
            if len(translated_text.strip()) < 3:
                score -= 0.5
            
            return max(0.0, min(1.0, score))
            
        except:
            return 0.7  # 默认分数
    
    def translate_text(self, text: str, target_language: str, source_language: str = 'auto',
                      model: str = None, user=None, use_cache: bool = True) -> Dict[str, Any]:
        """翻译文本"""
        try:
            # 清理输入
            text = text.strip()
            if not text:
                return {'success': False, 'error': '文本不能为空'}
            
            # 检测源语言
            if source_language == 'auto':
                source_language = self.detect_language(text)
            
            # 标准化语言代码
            source_language = self.language_mapping.get(source_language, source_language)
            target_language = self.language_mapping.get(target_language, target_language)
            
            # 检查是否需要翻译
            if source_language == target_language:
                return {
                    'success': True,
                    'translated_text': text,
                    'source_language': source_language,
                    'target_language': target_language,
                    'from_cache': False,
                    'confidence': 1.0
                }
            
            # 检查缓存
            if use_cache:
                cached = self._get_cached_translation(text, source_language, target_language)
                if cached:
                    return {
                        'success': True,
                        'translated_text': cached.translated_text,
                        'source_language': source_language,
                        'target_language': target_language,
                        'from_cache': True,
                        'confidence': cached.confidence_score,
                        'model': cached.translation_model
                    }
            
            # 创建请求记录
            request_obj = None
            if user:
                request_obj = TranslationRequest.objects.create(
                    user=user,
                    source_text=text,
                    source_language=source_language,
                    target_language=target_language,
                    translation_model=model or self.default_model,
                    status='processing'
                )
            
            start_time = time.time()
            
            try:
                # 调用AI翻译
                result = self._call_ai_translation(text, source_language, target_language, model)
                
                if not result['success']:
                    raise Exception(result['error'])
                
                translated_text = result['translated_text']
                confidence = result['confidence']
                used_model = result['model']
                
                processing_time = time.time() - start_time
                
                # 保存到缓存
                if use_cache:
                    self._save_to_cache(text, source_language, target_language, 
                                      translated_text, used_model, confidence)
                
                # 更新请求记录
                if request_obj:
                    request_obj.status = 'completed'
                    request_obj.translated_text = translated_text
                    request_obj.processing_time = processing_time
                    request_obj.confidence_score = confidence
                    request_obj.completed_at = timezone.now()
                    request_obj.save()
                
                # 保存到历史记录
                if user:
                    TranslationHistory.objects.create(
                        user=user,
                        source_text=text,
                        translated_text=translated_text,
                        source_language=source_language,
                        target_language=target_language
                    )
                
                # 更新语言对使用统计
                try:
                    pair, created = LanguagePair.objects.get_or_create(
                        source_language=source_language,
                        target_language=target_language
                    )
                    pair.increment_usage()
                except:
                    pass
                
                return {
                    'success': True,
                    'translated_text': translated_text,
                    'source_language': source_language,
                    'target_language': target_language,
                    'from_cache': False,
                    'confidence': confidence,
                    'processing_time': processing_time,
                    'model': used_model
                }
                
            except Exception as e:
                # 更新请求记录
                if request_obj:
                    request_obj.status = 'failed'
                    request_obj.error_message = str(e)
                    request_obj.completed_at = timezone.now()
                    request_obj.save()
                
                raise e
                
        except Exception as e:
            logger.error(f"翻译失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'source_language': source_language if 'source_language' in locals() else 'unknown',
                'target_language': target_language if 'target_language' in locals() else 'unknown'
            }
    
    def batch_translate(self, texts: List[str], target_language: str, 
                       source_language: str = 'auto', model: str = None, 
                       user=None) -> List[Dict[str, Any]]:
        """批量翻译"""
        results = []
        
        for text in texts:
            result = self.translate_text(
                text=text,
                target_language=target_language,
                source_language=source_language,
                model=model,
                user=user
            )
            results.append(result)
        
        return results
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.supported_languages
    
    def get_popular_language_pairs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门语言对"""
        pairs = LanguagePair.objects.filter(
            is_supported=True
        ).order_by('-usage_count')[:limit]
        
        result = []
        for pair in pairs:
            result.append({
                'source_language': pair.source_language,
                'target_language': pair.target_language,
                'source_name': self.supported_languages.get(pair.source_language, pair.source_language),
                'target_name': self.supported_languages.get(pair.target_language, pair.target_language),
                'usage_count': pair.usage_count,
                'quality_score': pair.quality_score
            })
        
        return result
    
    def get_user_settings(self, user) -> Dict[str, Any]:
        """获取用户翻译设置"""
        try:
            settings_obj = TranslationSettings.objects.get(user=user)
            return {
                'default_source_language': settings_obj.default_source_language,
                'default_target_language': settings_obj.default_target_language,
                'preferred_model': settings_obj.preferred_model,
                'auto_detect_language': settings_obj.auto_detect_language,
                'cache_enabled': settings_obj.cache_enabled,
                'show_confidence': settings_obj.show_confidence
            }
        except TranslationSettings.DoesNotExist:
            # 创建默认设置
            settings_obj = TranslationSettings.objects.create(user=user)
            return {
                'default_source_language': settings_obj.default_source_language,
                'default_target_language': settings_obj.default_target_language,
                'preferred_model': settings_obj.preferred_model,
                'auto_detect_language': settings_obj.auto_detect_language,
                'cache_enabled': settings_obj.cache_enabled,
                'show_confidence': settings_obj.show_confidence
            }
    
    def update_user_settings(self, user, settings_data: Dict[str, Any]) -> bool:
        """更新用户翻译设置"""
        try:
            settings_obj, created = TranslationSettings.objects.get_or_create(user=user)
            
            for key, value in settings_data.items():
                if hasattr(settings_obj, key):
                    setattr(settings_obj, key, value)
            
            settings_obj.save()
            return True
            
        except Exception as e:
            logger.error(f"更新用户翻译设置失败: {str(e)}")
            return False
    
    def get_translation_history(self, user, limit: int = 50) -> List[Dict[str, Any]]:
        """获取翻译历史"""
        history = TranslationHistory.objects.filter(user=user)[:limit]
        
        result = []
        for item in history:
            result.append({
                'id': item.id,
                'source_text': item.source_text,
                'translated_text': item.translated_text,
                'source_language': item.source_language,
                'target_language': item.target_language,
                'source_name': self.supported_languages.get(item.source_language, item.source_language),
                'target_name': self.supported_languages.get(item.target_language, item.target_language),
                'is_favorite': item.is_favorite,
                'created_at': item.created_at
            })
        
        return result
    
    def cleanup_cache(self, days: int = 30) -> Dict[str, int]:
        """清理过期缓存"""
        try:
            from datetime import timedelta
            
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # 获取过期的缓存记录
            expired_caches = TranslationCache.objects.filter(last_accessed__lt=cutoff_date)
            deleted_count = expired_caches.count()
            expired_caches.delete()
            
            return {'deleted_records': deleted_count}
            
        except Exception as e:
            logger.error(f"清理翻译缓存失败: {str(e)}")
            return {'deleted_records': 0} 