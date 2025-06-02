import os
import time
import logging
import hashlib
from typing import Optional, Dict, Any, List
from pathlib import Path
import torch
import torchaudio
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from langdetect import detect
import ChatTTS
from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db.models import Q, Count

from .models import ChatTTSCache, ChatTTSRequest, TTSSpeaker, TTSSettings, TTSVoice, UserVoicePreference, TTSUsageLog

logger = logging.getLogger(__name__)


class ChatTTSService:
    """ChatTTS服务类"""
    
    def __init__(self):
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.sample_rate = getattr(settings, 'CHATTTS_SAMPLE_RATE', 24000)
        self.max_text_length = getattr(settings, 'CHATTTS_MAX_TEXT_LENGTH', 1000)
        self.cache_dir = getattr(settings, 'CHATTTS_CACHE_DIR', Path(settings.MEDIA_ROOT) / 'chattts_cache')
        self.model_path = getattr(settings, 'CHATTTS_MODEL_PATH', None)
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 语言映射
        self.language_mapping = {
            'zh': 'zh',
            'zh-cn': 'zh',
            'zh-hans': 'zh',
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
    
    def _load_model(self):
        """加载ChatTTS模型"""
        if self.model is None:
            try:
                logger.info("正在加载ChatTTS模型...")
                self.model = ChatTTS.Chat()
                
                # 如果指定了模型路径，从本地加载
                if self.model_path and os.path.exists(self.model_path):
                    self.model.load_models(source='local', local_path=self.model_path)
                else:
                    # 从HuggingFace加载
                    self.model.load_models(source='huggingface')
                
                logger.info(f"ChatTTS模型加载成功，使用设备: {self.device}")
                
            except Exception as e:
                logger.error(f"ChatTTS模型加载失败: {str(e)}")
                raise Exception(f"ChatTTS模型加载失败: {str(e)}")
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        try:
            detected = detect(text)
            return self.language_mapping.get(detected, 'zh')
        except:
            # 如果检测失败，默认返回中文
            return 'zh'
    
    def _split_text(self, text: str) -> List[str]:
        """分割长文本"""
        if len(text) <= self.max_text_length:
            return [text]
        
        # 按句号、问号、感叹号分割
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in '。！？.!?' and len(current) > 50:
                sentences.append(current.strip())
                current = ""
        
        if current.strip():
            sentences.append(current.strip())
        
        # 如果单个句子仍然太长，强制分割
        final_sentences = []
        for sentence in sentences:
            if len(sentence) <= self.max_text_length:
                final_sentences.append(sentence)
            else:
                # 按逗号分割
                parts = sentence.split('，')
                current_part = ""
                for part in parts:
                    if len(current_part + part) <= self.max_text_length:
                        current_part += part + '，'
                    else:
                        if current_part:
                            final_sentences.append(current_part.rstrip('，'))
                        current_part = part + '，'
                if current_part:
                    final_sentences.append(current_part.rstrip('，'))
        
        return final_sentences
    
    def _get_cache_key(self, text: str, language: str, speaker_id: str = 'default') -> str:
        """生成缓存键"""
        content = f"{text}_{language}_{speaker_id}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cached_audio(self, text: str, language: str, speaker_id: str = 'default') -> Optional[ChatTTSCache]:
        """获取缓存的音频"""
        try:
            cache_key = self._get_cache_key(text, language, speaker_id)
            cache_obj = ChatTTSCache.objects.get(text_hash=cache_key)
            
            # 检查文件是否存在
            if cache_obj.audio_file and os.path.exists(cache_obj.audio_file.path):
                cache_obj.update_access()
                return cache_obj
            else:
                # 文件不存在，删除缓存记录
                cache_obj.delete()
                return None
                
        except ChatTTSCache.DoesNotExist:
            return None
    
    def _save_to_cache(self, text: str, language: str, audio_data: np.ndarray, 
                      speaker_id: str = 'default') -> ChatTTSCache:
        """保存音频到缓存"""
        try:
            cache_key = self._get_cache_key(text, language, speaker_id)
            
            # 生成文件名
            filename = f"{cache_key}.wav"
            file_path = os.path.join(self.cache_dir, filename)
            
            # 保存音频文件
            torchaudio.save(
                file_path,
                torch.from_numpy(audio_data).unsqueeze(0),
                self.sample_rate
            )
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            duration = len(audio_data) / self.sample_rate
            
            # 创建缓存记录
            with open(file_path, 'rb') as f:
                cache_obj = ChatTTSCache.objects.create(
                    text_hash=cache_key,
                    language=language,
                    speaker_id=speaker_id,
                    audio_format='wav',
                    sample_rate=self.sample_rate,
                    duration=duration,
                    file_size=file_size
                )
                cache_obj.audio_file.save(filename, ContentFile(f.read()))
            
            return cache_obj
            
        except Exception as e:
            logger.error(f"保存音频缓存失败: {str(e)}")
            raise
    
    def generate_speech(self, text: str, language: str = None, speaker_id: str = 'default',
                       user=None, use_cache: bool = True) -> Dict[str, Any]:
        """生成语音"""
        try:
            # 检测语言
            if not language:
                language = self.detect_language(text)
            
            # 标准化语言代码
            language = self.language_mapping.get(language, 'zh')
            
            # 检查缓存
            if use_cache:
                cached = self._get_cached_audio(text, language, speaker_id)
                if cached:
                    return {
                        'success': True,
                        'audio_url': cached.audio_file.url,
                        'duration': cached.duration,
                        'from_cache': True,
                        'language': language
                    }
            
            # 创建请求记录
            request_obj = None
            if user:
                request_obj = ChatTTSRequest.objects.create(
                    user=user,
                    text=text,
                    language=language,
                    speaker_id=speaker_id,
                    status='processing'
                )
            
            start_time = time.time()
            
            try:
                # 加载模型
                self._load_model()
                
                # 分割长文本
                text_segments = self._split_text(text)
                audio_segments = []
                
                for segment in text_segments:
                    # 生成语音
                    wavs = self.model.infer([segment], use_decoder=True)
                    
                    if wavs and len(wavs) > 0:
                        audio_segments.append(wavs[0])
                
                if not audio_segments:
                    raise Exception("语音生成失败")
                
                # 合并音频片段
                if len(audio_segments) == 1:
                    final_audio = audio_segments[0]
                else:
                    final_audio = np.concatenate(audio_segments)
                
                # 保存到缓存
                cache_obj = self._save_to_cache(text, language, final_audio, speaker_id)
                
                processing_time = time.time() - start_time
                
                # 更新请求记录
                if request_obj:
                    request_obj.status = 'completed'
                    request_obj.audio_file = cache_obj.audio_file
                    request_obj.processing_time = processing_time
                    request_obj.completed_at = timezone.now()
                    request_obj.save()
                
                return {
                    'success': True,
                    'audio_url': cache_obj.audio_file.url,
                    'duration': cache_obj.duration,
                    'processing_time': processing_time,
                    'from_cache': False,
                    'language': language
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
            logger.error(f"语音生成失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'language': language if 'language' in locals() else 'unknown'
            }
    
    def get_available_speakers(self, language: str = None) -> List[Dict[str, Any]]:
        """获取可用的说话人"""
        queryset = TTSSpeaker.objects.filter(is_active=True)
        
        if language:
            language = self.language_mapping.get(language, language)
            queryset = queryset.filter(language=language)
        
        speakers = []
        for speaker in queryset:
            speakers.append({
                'speaker_id': speaker.speaker_id,
                'name': speaker.name,
                'language': speaker.language,
                'gender': speaker.gender,
                'age_group': speaker.age_group,
                'description': speaker.description
            })
        
        return speakers
    
    def get_user_settings(self, user) -> Dict[str, Any]:
        """获取用户TTS设置"""
        try:
            settings_obj = TTSSettings.objects.get(user=user)
            return {
                'default_language': settings_obj.default_language,
                'default_speaker': settings_obj.default_speaker,
                'speech_rate': settings_obj.speech_rate,
                'volume': settings_obj.volume,
                'auto_play': settings_obj.auto_play,
                'cache_enabled': settings_obj.cache_enabled
            }
        except TTSSettings.DoesNotExist:
            # 创建默认设置
            settings_obj = TTSSettings.objects.create(user=user)
            return {
                'default_language': settings_obj.default_language,
                'default_speaker': settings_obj.default_speaker,
                'speech_rate': settings_obj.speech_rate,
                'volume': settings_obj.volume,
                'auto_play': settings_obj.auto_play,
                'cache_enabled': settings_obj.cache_enabled
            }
    
    def update_user_settings(self, user, settings_data: Dict[str, Any]) -> bool:
        """更新用户TTS设置"""
        try:
            settings_obj, created = TTSSettings.objects.get_or_create(user=user)
            
            for key, value in settings_data.items():
                if hasattr(settings_obj, key):
                    setattr(settings_obj, key, value)
            
            settings_obj.save()
            return True
            
        except Exception as e:
            logger.error(f"更新用户TTS设置失败: {str(e)}")
            return False
    
    def cleanup_cache(self, days: int = 30) -> Dict[str, int]:
        """清理过期缓存"""
        try:
            from datetime import timedelta
            
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # 获取过期的缓存记录
            expired_caches = ChatTTSCache.objects.filter(last_accessed__lt=cutoff_date)
            
            deleted_files = 0
            deleted_records = 0
            
            for cache in expired_caches:
                # 删除文件
                if cache.audio_file and os.path.exists(cache.audio_file.path):
                    try:
                        os.remove(cache.audio_file.path)
                        deleted_files += 1
                    except:
                        pass
                
                # 删除记录
                cache.delete()
                deleted_records += 1
            
            return {
                'deleted_files': deleted_files,
                'deleted_records': deleted_records
            }
            
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")
            return {'deleted_files': 0, 'deleted_records': 0}


class TTSVoiceService:
    """TTS语音服务"""
    
    @staticmethod
    def get_available_voices(language=None, gender=None, voice_type=None):
        """获取可用语音列表"""
        query = Q(is_active=True)
        
        if language:
            query &= Q(language=language)
        if gender:
            query &= Q(gender=gender)
        if voice_type:
            query &= Q(voice_type=voice_type)
        
        return TTSVoice.objects.filter(query).order_by('-popularity', 'name')
    
    @staticmethod
    def get_user_preferences(user):
        """获取用户语音偏好"""
        preferences, created = UserVoicePreference.objects.get_or_create(
            user=user,
            defaults={
                'reading_speed': 1.0,
                'volume': 0.8,
                'pitch': 1.0,
                'auto_play': False,
                'pause_between_paragraphs': 0.5,
                'pause_between_sentences': 0.3,
            }
        )
        return preferences
    
    @staticmethod
    def update_user_preferences(user, **kwargs):
        """更新用户语音偏好"""
        preferences = TTSVoiceService.get_user_preferences(user)
        
        for key, value in kwargs.items():
            if hasattr(preferences, key):
                setattr(preferences, key, value)
        
        preferences.save()
        return preferences
    
    @staticmethod
    def set_default_voice(user, voice_id):
        """设置默认语音"""
        try:
            voice = TTSVoice.objects.get(voice_id=voice_id, is_active=True)
            preferences = TTSVoiceService.get_user_preferences(user)
            preferences.default_voice = voice
            preferences.save()
            return True
        except TTSVoice.DoesNotExist:
            return False
    
    @staticmethod
    def add_favorite_voice(user, voice_id):
        """添加收藏语音"""
        try:
            voice = TTSVoice.objects.get(voice_id=voice_id, is_active=True)
            preferences = TTSVoiceService.get_user_preferences(user)
            preferences.favorite_voices.add(voice)
            return True
        except TTSVoice.DoesNotExist:
            return False
    
    @staticmethod
    def remove_favorite_voice(user, voice_id):
        """移除收藏语音"""
        try:
            voice = TTSVoice.objects.get(voice_id=voice_id)
            preferences = TTSVoiceService.get_user_preferences(user)
            preferences.favorite_voices.remove(voice)
            return True
        except TTSVoice.DoesNotExist:
            return False
    
    @staticmethod
    def get_recommended_voices(user, language='zh'):
        """获取推荐语音"""
        # 基于用户使用历史推荐
        usage_logs = TTSUsageLog.objects.filter(
            user=user, 
            success=True
        ).values('voice').annotate(
            usage_count=Count('id')
        ).order_by('-usage_count')
        
        used_voice_ids = [log['voice'] for log in usage_logs[:5]]
        
        # 获取相似语音（同性别、同年龄组）
        if used_voice_ids:
            similar_voices = TTSVoice.objects.filter(
                language=language,
                is_active=True
            ).exclude(
                id__in=used_voice_ids
            ).order_by('-popularity')[:10]
        else:
            # 新用户推荐热门语音
            similar_voices = TTSVoice.objects.filter(
                language=language,
                is_active=True
            ).order_by('-popularity')[:10]
        
        return similar_voices
    
    @staticmethod
    def generate_voice_sample(voice_id, sample_text=None):
        """生成语音示例"""
        try:
            voice = TTSVoice.objects.get(voice_id=voice_id, is_active=True)
            text = sample_text or voice.sample_text
            
            # 调用ChatTTS服务生成示例
            from .chattts_service import ChatTTSService
            
            audio_data = ChatTTSService.text_to_speech(
                text=text,
                language=voice.language,
                speaker_id=voice.api_name or voice.voice_id
            )
            
            if audio_data:
                # 保存示例音频
                import tempfile
                import os
                from django.core.files import File
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    tmp_file.write(audio_data)
                    tmp_file.flush()
                    
                    with open(tmp_file.name, 'rb') as f:
                        voice.sample_audio.save(
                            f'sample_{voice.voice_id}.wav',
                            File(f),
                            save=True
                        )
                    
                    os.unlink(tmp_file.name)
                
                return voice.sample_audio.url
            
        except TTSVoice.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def log_usage(user, voice, book=None, text_length=0, audio_duration=None, 
                  processing_time=None, success=True, error_message=''):
        """记录使用日志"""
        TTSUsageLog.objects.create(
            user=user,
            voice=voice,
            book=book,
            text_length=text_length,
            audio_duration=audio_duration,
            processing_time=processing_time,
            success=success,
            error_message=error_message
        )
        
        if success:
            voice.increment_popularity()


class EnhancedChatTTSService(ChatTTSService):
    """增强的ChatTTS服务"""
    
    @staticmethod
    def text_to_speech_with_preferences(text, user, book=None, voice_id=None):
        """根据用户偏好进行语音合成"""
        import time
        start_time = time.time()
        
        # 获取用户偏好
        preferences = TTSVoiceService.get_user_preferences(user)
        
        # 确定使用的语音
        if voice_id:
            try:
                voice = TTSVoice.objects.get(voice_id=voice_id, is_active=True)
            except TTSVoice.DoesNotExist:
                voice = preferences.default_voice
        else:
            voice = preferences.default_voice
        
        if not voice:
            # 使用默认语音
            voice = TTSVoice.objects.filter(
                language='zh', 
                is_active=True
            ).order_by('-popularity').first()
        
        if not voice:
            return None
        
        try:
            # 应用用户偏好设置
            enhanced_text = EnhancedChatTTSService._apply_preferences(text, preferences)
            
            # 调用ChatTTS服务
            audio_data = ChatTTSService.text_to_speech(
                text=enhanced_text,
                language=voice.language,
                speaker_id=voice.api_name or voice.voice_id
            )
            
            processing_time = time.time() - start_time
            
            # 记录使用日志
            TTSVoiceService.log_usage(
                user=user,
                voice=voice,
                book=book,
                text_length=len(text),
                processing_time=processing_time,
                success=bool(audio_data)
            )
            
            return {
                'audio_data': audio_data,
                'voice': voice,
                'processing_time': processing_time
            }
            
        except Exception as e:
            # 记录错误日志
            TTSVoiceService.log_usage(
                user=user,
                voice=voice,
                book=book,
                text_length=len(text),
                processing_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
            return None
    
    @staticmethod
    def _apply_preferences(text, preferences):
        """应用用户偏好到文本"""
        enhanced_text = text
        
        # 添加停顿
        if preferences.pause_between_sentences > 0:
            import re
            # 在句号、问号、感叹号后添加停顿
            enhanced_text = re.sub(
                r'([。！？])', 
                f'\\1[pause:{preferences.pause_between_sentences}s]', 
                enhanced_text
            )
        
        if preferences.pause_between_paragraphs > 0:
            # 在段落间添加停顿
            enhanced_text = enhanced_text.replace(
                '\n\n', 
                f'\n\n[pause:{preferences.pause_between_paragraphs}s]'
            )
        
        # 语速控制（通过标记实现）
        if preferences.reading_speed != 1.0:
            enhanced_text = f'[speed:{preferences.reading_speed}]{enhanced_text}'
        
        # 音调控制
        if preferences.pitch != 1.0:
            enhanced_text = f'[pitch:{preferences.pitch}]{enhanced_text}'
        
        return enhanced_text
    
    @staticmethod
    def batch_generate_samples():
        """批量生成语音示例"""
        voices = TTSVoice.objects.filter(is_active=True, sample_audio='')
        
        for voice in voices:
            try:
                TTSVoiceService.generate_voice_sample(voice.voice_id)
                print(f"Generated sample for {voice.name}")
            except Exception as e:
                print(f"Failed to generate sample for {voice.name}: {e}") 