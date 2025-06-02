from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import hashlib


class TranslationCache(models.Model):
    """翻译缓存模型"""
    text_hash = models.CharField(max_length=64, unique=True, verbose_name='文本哈希', db_index=True)
    source_language = models.CharField(max_length=10, verbose_name='源语言', db_index=True)
    target_language = models.CharField(max_length=10, verbose_name='目标语言', db_index=True)
    source_text = models.TextField(verbose_name='源文本')
    translated_text = models.TextField(verbose_name='翻译文本')
    translation_model = models.CharField(max_length=50, default='gpt-3.5-turbo', verbose_name='翻译模型')
    confidence_score = models.FloatField(null=True, blank=True, verbose_name='置信度分数')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    last_accessed = models.DateTimeField(default=timezone.now, verbose_name='最后访问时间')
    access_count = models.IntegerField(default=0, verbose_name='访问次数')
    
    class Meta:
        verbose_name = '翻译缓存'
        verbose_name_plural = '翻译缓存'
        indexes = [
            models.Index(fields=['text_hash', 'source_language', 'target_language']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_accessed']),
        ]
    
    def __str__(self):
        return f'{self.source_language} -> {self.target_language} - {self.text_hash[:8]}'
    
    @classmethod
    def get_text_hash(cls, text, source_lang, target_lang):
        """生成文本哈希"""
        content = f"{text}_{source_lang}_{target_lang}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def update_access(self):
        """更新访问信息"""
        self.last_accessed = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed', 'access_count'])


class TranslationRequest(models.Model):
    """翻译请求记录"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    source_text = models.TextField(verbose_name='源文本')
    translated_text = models.TextField(null=True, blank=True, verbose_name='翻译文本')
    source_language = models.CharField(max_length=10, verbose_name='源语言')
    target_language = models.CharField(max_length=10, verbose_name='目标语言')
    translation_model = models.CharField(max_length=50, default='gpt-3.5-turbo', verbose_name='翻译模型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')
    processing_time = models.FloatField(null=True, blank=True, verbose_name='处理时间(秒)')
    confidence_score = models.FloatField(null=True, blank=True, verbose_name='置信度分数')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '翻译请求'
        verbose_name_plural = '翻译请求'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['source_language', 'target_language']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.source_language} -> {self.target_language} - {self.status}'


class TranslationSettings(models.Model):
    """翻译用户设置"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    default_source_language = models.CharField(max_length=10, default='auto', verbose_name='默认源语言')
    default_target_language = models.CharField(max_length=10, default='zh', verbose_name='默认目标语言')
    preferred_model = models.CharField(max_length=50, default='gpt-3.5-turbo', verbose_name='首选模型')
    auto_detect_language = models.BooleanField(default=True, verbose_name='自动检测语言')
    cache_enabled = models.BooleanField(default=True, verbose_name='启用缓存')
    show_confidence = models.BooleanField(default=False, verbose_name='显示置信度')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '翻译设置'
        verbose_name_plural = '翻译设置'
    
    def __str__(self):
        return f'{self.user.username} - 翻译设置'


class LanguagePair(models.Model):
    """语言对模型"""
    source_language = models.CharField(max_length=10, verbose_name='源语言')
    target_language = models.CharField(max_length=10, verbose_name='目标语言')
    is_supported = models.BooleanField(default=True, verbose_name='是否支持')
    quality_score = models.FloatField(default=0.8, verbose_name='翻译质量分数')
    usage_count = models.IntegerField(default=0, verbose_name='使用次数')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '语言对'
        verbose_name_plural = '语言对'
        unique_together = ['source_language', 'target_language']
        indexes = [
            models.Index(fields=['source_language', 'target_language']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f'{self.source_language} -> {self.target_language}'
    
    def increment_usage(self):
        """增加使用次数"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class TranslationHistory(models.Model):
    """翻译历史记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    source_text = models.TextField(verbose_name='源文本')
    translated_text = models.TextField(verbose_name='翻译文本')
    source_language = models.CharField(max_length=10, verbose_name='源语言')
    target_language = models.CharField(max_length=10, verbose_name='目标语言')
    is_favorite = models.BooleanField(default=False, verbose_name='是否收藏')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '翻译历史'
        verbose_name_plural = '翻译历史'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'is_favorite']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.source_language} -> {self.target_language}' 