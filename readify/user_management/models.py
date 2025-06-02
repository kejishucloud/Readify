from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """用户配置文件"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    bio = models.TextField(max_length=500, null=True, blank=True, verbose_name='个人简介')
    birth_date = models.DateField(null=True, blank=True, verbose_name='出生日期')
    location = models.CharField(max_length=100, null=True, blank=True, verbose_name='位置')
    website = models.URLField(null=True, blank=True, verbose_name='个人网站')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户配置文件'
        verbose_name_plural = '用户配置文件'
    
    def __str__(self):
        return f'{self.user.username} - 配置文件'


class UserPreferences(models.Model):
    """用户偏好设置"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', '浅色主题'),
        ('dark', '深色主题'),
        ('auto', '自动')
    ], verbose_name='主题')
    language = models.CharField(max_length=10, default='zh', verbose_name='界面语言')
    user_timezone = models.CharField(max_length=50, default='Asia/Shanghai', verbose_name='时区')
    email_notifications = models.BooleanField(default=True, verbose_name='邮件通知')
    push_notifications = models.BooleanField(default=True, verbose_name='推送通知')
    
    # 语音设置
    voice_enabled = models.BooleanField(default=True, verbose_name='启用语音功能')
    voice_speed = models.FloatField(default=1.0, verbose_name='语音速度')
    voice_type = models.CharField(max_length=20, default='female', choices=[
        ('female', '女声'),
        ('male', '男声'),
        ('child', '童声')
    ], verbose_name='语音类型')
    auto_read = models.BooleanField(default=False, verbose_name='自动朗读')
    
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户偏好'
        verbose_name_plural = '用户偏好'
    
    def __str__(self):
        return f'{self.user.username} - 偏好设置'


class UserAIConfig(models.Model):
    """用户AI服务配置"""
    AI_PROVIDERS = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('google', 'Google'),
        ('azure', 'Azure OpenAI'),
        ('custom', '自定义'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    provider = models.CharField(max_length=20, choices=AI_PROVIDERS, default='openai', verbose_name='AI提供商')
    api_url = models.URLField(default='https://api.openai.com/v1', verbose_name='API地址')
    api_key = models.CharField(max_length=500, verbose_name='API密钥')
    model_id = models.CharField(max_length=100, default='gpt-3.5-turbo', verbose_name='模型ID')
    max_tokens = models.IntegerField(default=4000, verbose_name='最大令牌数')
    temperature = models.FloatField(default=0.7, verbose_name='温度参数')
    timeout = models.IntegerField(default=30, verbose_name='请求超时(秒)')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户AI配置'
        verbose_name_plural = '用户AI配置'
    
    def __str__(self):
        return f'{self.user.username} - {self.get_provider_display()}'
    
    def get_headers(self):
        """获取API请求头"""
        headers = {
            'Content-Type': 'application/json',
        }
        
        if self.provider == 'openai':
            headers['Authorization'] = f'Bearer {self.api_key}'
        elif self.provider == 'anthropic':
            headers['x-api-key'] = self.api_key
            headers['anthropic-version'] = '2023-06-01'
        elif self.provider == 'google':
            headers['Authorization'] = f'Bearer {self.api_key}'
        elif self.provider == 'azure':
            headers['api-key'] = self.api_key
        else:  # custom - 支持多种认证方式
            # 检查API密钥格式，支持不同的认证方式
            if self.api_key.startswith('Bearer '):
                headers['Authorization'] = self.api_key
            elif self.api_key.startswith('sk-'):
                headers['Authorization'] = f'Bearer {self.api_key}'
            else:
                # 对于自定义API，直接使用Bearer认证
                headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    def get_chat_endpoint(self):
        """获取聊天API端点"""
        if self.provider == 'anthropic':
            return f"{self.api_url.rstrip('/')}/messages"
        elif self.provider == 'google':
            return f"{self.api_url.rstrip('/')}/models/{self.model_id}:generateContent"
        else:  # openai, azure, custom
            return f"{self.api_url.rstrip('/')}/chat/completions" 