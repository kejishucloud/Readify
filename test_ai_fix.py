#!/usr/bin/env python
"""
测试AI配置修复
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.user_management.models import UserAIConfig
from readify.ai_services.services import AIService

def test_ai_config_fix():
    """测试AI配置修复"""
    print("🔧 测试AI配置修复...")
    print("=" * 60)
    
    try:
        # 获取用户
        user = User.objects.get(username='kejishu')
        print(f"👤 用户: {user.username}")
        
        # 检查用户当前配置
        try:
            config = UserAIConfig.objects.get(user=user)
            print(f"📋 用户当前配置:")
            print(f"   提供商: {config.provider}")
            print(f"   API地址: {config.api_url}")
            print(f"   模型: {config.model_id}")
            print(f"   API密钥长度: {len(config.api_key)}")
            print(f"   是否启用: {config.is_active}")
        except UserAIConfig.DoesNotExist:
            print("❌ 用户没有AI配置")
        
        # 测试AI服务配置获取
        print(f"\n🤖 测试AI服务配置获取:")
        ai_service = AIService(user=user)
        
        print(f"   AI服务配置:")
        for key, value in ai_service.config.items():
            if key == 'api_key':
                print(f"     {key}: {value[:8]}...{value[-4:] if len(value) > 12 else value}")
            elif key == 'headers':
                # 隐藏Authorization头中的敏感信息
                headers_copy = value.copy()
                if 'Authorization' in headers_copy:
                    auth_value = headers_copy['Authorization']
                    if len(auth_value) > 20:
                        headers_copy['Authorization'] = f"{auth_value[:15]}...{auth_value[-4:]}"
                print(f"     {key}: {headers_copy}")
            else:
                print(f"     {key}: {value}")
        
        # 测试API请求
        print(f"\n🧪 测试API请求:")
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回复'AI配置修复测试成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            print(f"✅ AI配置修复测试成功!")
            print(f"   AI回复: {result['content'][:100]}...")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            print(f"   使用令牌: {result['tokens_used']}")
            return True
        else:
            print(f"❌ AI配置修复测试失败: {result['error']}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ai_config_fix() 