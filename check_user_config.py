#!/usr/bin/env python
"""
检查用户AI配置
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.user_management.models import UserAIConfig

def check_user_config():
    """检查用户AI配置"""
    try:
        user = User.objects.get(username='kejishu')
        print(f"用户: {user.username}")
        
        try:
            config = UserAIConfig.objects.get(user=user)
            print(f"提供商: {config.provider}")
            print(f"API地址: {config.api_url}")
            print(f"模型: {config.model_id}")
            print(f"API密钥长度: {len(config.api_key)}")
            print(f"API密钥内容: {repr(config.api_key)}")
            print(f"是否启用: {config.is_active}")
            
            # 检查headers
            headers = config.get_headers()
            print(f"请求头: {headers}")
            
            return config
        except UserAIConfig.DoesNotExist:
            print("❌ 用户没有AI配置")
            return None
            
    except User.DoesNotExist:
        print("❌ 用户不存在")
        return None
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        return None

if __name__ == "__main__":
    check_user_config() 