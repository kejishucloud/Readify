from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AIRequest(models.Model):
    """AI请求模型"""
    REQUEST_TYPES = [
        ('summary', '书籍摘要'),
        ('question', '问题回答'),
        ('keywords', '关键词提取'),
        ('analysis', '文本分析'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, null=True, blank=True, verbose_name='关联书籍')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, verbose_name='请求类型')
    input_text = models.TextField(verbose_name='输入文本')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = 'AI请求'
        verbose_name_plural = 'AI请求'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.get_request_type_display()}'


class AIResponse(models.Model):
    """AI响应模型"""
    request = models.OneToOneField(AIRequest, on_delete=models.CASCADE, related_name='response', verbose_name='关联请求')
    response_text = models.TextField(verbose_name='响应文本')
    processing_time = models.FloatField(default=0, verbose_name='处理时间(秒)')
    tokens_used = models.IntegerField(default=0, verbose_name='使用的令牌数')
    model_used = models.CharField(max_length=100, blank=True, verbose_name='使用的模型')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'AI响应'
        verbose_name_plural = 'AI响应'
    
    def __str__(self):
        return f'响应 - {self.request.get_request_type_display()}'


class AITask(models.Model):
    """AI任务模型"""
    TASK_TYPES = [
        ('summary', '书籍摘要'),
        ('question', '问题回答'),
        ('translation', '翻译'),
        ('keyword_extraction', '关键词提取'),
    ]
    
    TASK_STATUS = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, verbose_name='任务类型')
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='pending', verbose_name='状态')
    input_data = models.JSONField(verbose_name='输入数据')
    output_data = models.JSONField(blank=True, null=True, verbose_name='输出数据')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = 'AI任务'
        verbose_name_plural = 'AI任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.get_task_type_display()}'


class AIModel(models.Model):
    """AI模型配置"""
    name = models.CharField(max_length=100, verbose_name='模型名称')
    provider = models.CharField(max_length=50, verbose_name='提供商')
    api_endpoint = models.URLField(verbose_name='API端点')
    model_id = models.CharField(max_length=100, verbose_name='模型ID')
    max_tokens = models.IntegerField(default=4000, verbose_name='最大令牌数')
    temperature = models.FloatField(default=0.7, verbose_name='温度参数')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'AI模型'
        verbose_name_plural = 'AI模型'
    
    def __str__(self):
        return f'{self.provider} - {self.name}' 