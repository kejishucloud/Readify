from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import hashlib


class ChatTTSCache(models.Model):
    """ChatTTS缓存模型"""
    text_hash = models.CharField(max_length=64, unique=True, verbose_name='文本哈希', db_index=True)
    language = models.CharField(max_length=10, verbose_name='语言', db_index=True)
    speaker_id = models.CharField(max_length=50, default='default', verbose_name='说话人ID')
    audio_file = models.FileField(upload_to='chattts_cache/', verbose_name='音频文件')
    audio_format = models.CharField(max_length=10, default='wav', verbose_name='音频格式')
    sample_rate = models.IntegerField(default=24000, verbose_name='采样率')
    duration = models.FloatField(null=True, blank=True, verbose_name='音频时长(秒)')
    file_size = models.IntegerField(null=True, blank=True, verbose_name='文件大小(字节)')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    last_accessed = models.DateTimeField(default=timezone.now, verbose_name='最后访问时间')
    access_count = models.IntegerField(default=0, verbose_name='访问次数')
    
    class Meta:
        verbose_name = 'ChatTTS缓存'
        verbose_name_plural = 'ChatTTS缓存'
        indexes = [
            models.Index(fields=['text_hash', 'language']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_accessed']),
        ]
    
    def __str__(self):
        return f'{self.language} - {self.speaker_id} - {self.text_hash[:8]}'
    
    @classmethod
    def get_text_hash(cls, text, language, speaker_id='default'):
        """生成文本哈希"""
        content = f"{text}_{language}_{speaker_id}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def update_access(self):
        """更新访问信息"""
        self.last_accessed = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed', 'access_count'])


class ChatTTSRequest(models.Model):
    """ChatTTS请求记录"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    text = models.TextField(verbose_name='文本内容')
    language = models.CharField(max_length=10, verbose_name='语言')
    speaker_id = models.CharField(max_length=50, default='default', verbose_name='说话人ID')
    audio_file = models.FileField(upload_to='chattts_requests/', null=True, blank=True, verbose_name='音频文件')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')
    processing_time = models.FloatField(null=True, blank=True, verbose_name='处理时间(秒)')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = 'ChatTTS请求'
        verbose_name_plural = 'ChatTTS请求'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.language} - {self.status}'


class TTSSpeaker(models.Model):
    """TTS说话人模型"""
    speaker_id = models.CharField(max_length=50, unique=True, verbose_name='说话人ID')
    name = models.CharField(max_length=100, verbose_name='说话人名称')
    language = models.CharField(max_length=10, verbose_name='主要语言')
    gender = models.CharField(max_length=10, choices=[('male', '男性'), ('female', '女性'), ('neutral', '中性')], verbose_name='性别')
    age_group = models.CharField(max_length=20, choices=[
        ('child', '儿童'),
        ('young', '青年'),
        ('adult', '成年'),
        ('elderly', '老年')
    ], verbose_name='年龄组')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'TTS说话人'
        verbose_name_plural = 'TTS说话人'
        ordering = ['language', 'name']
    
    def __str__(self):
        return f'{self.name} ({self.language})'


class TTSSettings(models.Model):
    """TTS用户设置"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    default_language = models.CharField(max_length=10, default='zh', verbose_name='默认语言')
    default_speaker = models.CharField(max_length=50, default='default', verbose_name='默认说话人')
    speech_rate = models.FloatField(default=1.0, verbose_name='语速倍率')
    volume = models.FloatField(default=1.0, verbose_name='音量')
    auto_play = models.BooleanField(default=False, verbose_name='自动播放')
    cache_enabled = models.BooleanField(default=True, verbose_name='启用缓存')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'TTS设置'
        verbose_name_plural = 'TTS设置'
    
    def __str__(self):
        return f'{self.user.username} - TTS设置'


class TTSVoice(models.Model):
    """TTS语音模型"""
    VOICE_TYPES = [
        ('neural', '神经网络语音'),
        ('standard', '标准语音'),
        ('premium', '高级语音'),
        ('custom', '自定义语音'),
    ]
    
    EMOTION_TYPES = [
        ('neutral', '中性'),
        ('happy', '愉快'),
        ('sad', '悲伤'),
        ('angry', '愤怒'),
        ('excited', '兴奋'),
        ('calm', '平静'),
        ('serious', '严肃'),
    ]
    
    voice_id = models.CharField(max_length=100, unique=True, verbose_name='语音ID')
    name = models.CharField(max_length=100, verbose_name='语音名称')
    display_name = models.CharField(max_length=100, verbose_name='显示名称')
    language = models.CharField(max_length=10, verbose_name='语言代码')
    language_name = models.CharField(max_length=50, verbose_name='语言名称')
    gender = models.CharField(max_length=10, choices=[
        ('male', '男性'), 
        ('female', '女性'), 
        ('neutral', '中性')
    ], verbose_name='性别')
    age_group = models.CharField(max_length=20, choices=[
        ('child', '儿童'),
        ('teen', '青少年'),
        ('young_adult', '青年'),
        ('adult', '成年'),
        ('middle_aged', '中年'),
        ('elderly', '老年')
    ], verbose_name='年龄组')
    voice_type = models.CharField(max_length=20, choices=VOICE_TYPES, verbose_name='语音类型')
    emotion = models.CharField(max_length=20, choices=EMOTION_TYPES, default='neutral', verbose_name='情感')
    description = models.TextField(blank=True, verbose_name='描述')
    sample_text = models.TextField(default='这是一个语音示例。', verbose_name='示例文本')
    sample_audio = models.FileField(upload_to='voice_samples/', blank=True, null=True, verbose_name='示例音频')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    is_premium = models.BooleanField(default=False, verbose_name='是否为高级语音')
    provider = models.CharField(max_length=50, default='chattts', verbose_name='提供商')
    api_name = models.CharField(max_length=100, blank=True, verbose_name='API名称')
    quality_score = models.FloatField(default=5.0, verbose_name='质量评分')
    popularity = models.IntegerField(default=0, verbose_name='受欢迎程度')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'TTS语音'
        verbose_name_plural = 'TTS语音'
        ordering = ['-popularity', 'language', 'name']
        indexes = [
            models.Index(fields=['language', 'gender']),
            models.Index(fields=['voice_type', 'is_active']),
            models.Index(fields=['popularity']),
        ]
    
    def __str__(self):
        return f'{self.display_name} ({self.language_name})'
    
    def increment_popularity(self):
        """增加受欢迎程度"""
        self.popularity += 1
        self.save(update_fields=['popularity'])


class UserVoicePreference(models.Model):
    """用户语音偏好模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    favorite_voices = models.ManyToManyField(TTSVoice, blank=True, verbose_name='收藏语音')
    default_voice = models.ForeignKey(
        TTSVoice, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='default_for_users',
        verbose_name='默认语音'
    )
    reading_speed = models.FloatField(default=1.0, verbose_name='阅读速度')
    volume = models.FloatField(default=0.8, verbose_name='音量')
    pitch = models.FloatField(default=1.0, verbose_name='音调')
    auto_play = models.BooleanField(default=False, verbose_name='自动播放')
    pause_between_paragraphs = models.FloatField(default=0.5, verbose_name='段落间停顿(秒)')
    pause_between_sentences = models.FloatField(default=0.3, verbose_name='句子间停顿(秒)')
    background_music_enabled = models.BooleanField(default=False, verbose_name='启用背景音乐')
    background_music_volume = models.FloatField(default=0.2, verbose_name='背景音乐音量')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户语音偏好'
        verbose_name_plural = '用户语音偏好'
    
    def __str__(self):
        return f'{self.user.username} - 语音偏好'


class TTSUsageLog(models.Model):
    """TTS使用日志"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    voice = models.ForeignKey(TTSVoice, on_delete=models.CASCADE, verbose_name='使用的语音')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, null=True, blank=True, verbose_name='相关书籍')
    text_length = models.IntegerField(verbose_name='文本长度')
    audio_duration = models.FloatField(null=True, blank=True, verbose_name='音频时长(秒)')
    processing_time = models.FloatField(null=True, blank=True, verbose_name='处理时间(秒)')
    success = models.BooleanField(default=True, verbose_name='是否成功')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'TTS使用日志'
        verbose_name_plural = 'TTS使用日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['voice', 'success']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.voice.name} - {self.created_at.strftime("%Y-%m-%d %H:%M")}' 