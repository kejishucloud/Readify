#!/usr/bin/env python
"""
更新主要用户的AI配置
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.user_management.models import UserAIConfig

def update_main_user_config():
    """更新主要用户的AI配置"""
    try:
        # 获取用户
        user = User.objects.get(username='kejishucloud')
        print(f'为用户 {user.username} 更新AI配置...')

        # 创建或更新AI配置
        config, created = UserAIConfig.objects.get_or_create(
            user=user,
            defaults={
                'provider': 'custom',
                'api_url': 'http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1',
                'api_key': '90a07e44-8cb3-4e83-bb92-056e271b0307',
                'model_id': 'Qwen3-30B-A3B',
                'max_tokens': 4000,
                'temperature': 0.7,
                'timeout': 30,
                'is_active': True
            }
        )

        if not created:
            # 更新现有配置
            config.provider = 'custom'
            config.api_url = 'http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1'
            config.api_key = '90a07e44-8cb3-4e83-bb92-056e271b0307'
            config.model_id = 'Qwen3-30B-A3B'
            config.max_tokens = 4000
            config.temperature = 0.7
            config.timeout = 30
            config.is_active = True
            config.save()
            print('✅ 已更新现有配置')
        else:
            print('✅ 已创建新配置')

        print(f'配置详情:')
        print(f'  提供商: {config.provider}')
        print(f'  API地址: {config.api_url}')
        print(f'  模型: {config.model_id}')
        print(f'  最大令牌: {config.max_tokens}')
        print(f'  温度: {config.temperature}')
        print(f'  超时: {config.timeout}秒')
        print(f'  状态: {"启用" if config.is_active else "禁用"}')
        
        # 测试配置
        from readify.ai_services.services import AIService
        
        print(f'\n🧪 测试AI配置...')
        ai_service = AIService(user=user)
        
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回复'配置更新成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            print(f"✅ AI配置测试成功!")
            print(f"   AI回复: {result['content'][:100]}...")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            print(f"   使用令牌: {result['tokens_used']}")
        else:
            print(f"❌ AI配置测试失败: {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    update_main_user_config() 