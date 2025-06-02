#!/usr/bin/env python
"""
测试Web界面AI配置功能
"""
import os
import sys
import django
import json

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def test_user_ai_config():
    """测试用户AI配置"""
    print("🔍 测试用户AI配置...")
    print("=" * 50)
    
    try:
        from django.contrib.auth.models import User
        from readify.user_management.models import UserAIConfig
        from readify.ai_services.services import AIService
        
        # 获取或创建测试用户
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"✅ 创建测试用户: {user.username}")
        else:
            print(f"✅ 使用现有用户: {user.username}")
        
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
        
        print(f"✅ AI配置已保存")
        print(f"   提供商: {config.provider}")
        print(f"   API地址: {config.api_url}")
        print(f"   模型: {config.model_id}")
        print(f"   状态: {'启用' if config.is_active else '禁用'}")
        
        # 测试配置的headers和endpoint方法
        print(f"\n🔧 测试配置方法...")
        headers = config.get_headers()
        endpoint = config.get_chat_endpoint()
        
        print(f"   请求头: {headers}")
        print(f"   端点: {endpoint}")
        
        # 测试AI服务
        print(f"\n🧪 测试AI服务...")
        ai_service = AIService(user=user)
        
        # 检查配置是否正确加载
        print(f"   AI服务配置:")
        print(f"     提供商: {ai_service.config['provider']}")
        print(f"     API地址: {ai_service.config['api_url']}")
        print(f"     模型: {ai_service.config['model_id']}")
        print(f"     端点: {ai_service.config.get('endpoint', '未设置')}")
        
        # 发送测试请求
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回复'AI配置测试成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            print(f"✅ AI服务测试成功!")
            print(f"   AI回复: {result['content']}")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            print(f"   使用令牌: {result['tokens_used']}")
            return True
        else:
            print(f"❌ AI服务测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def simulate_web_request():
    """模拟Web请求测试"""
    print("\n🌐 模拟Web请求测试...")
    print("=" * 50)
    
    try:
        from django.test import RequestFactory
        from django.contrib.auth.models import User
        from readify.user_management.views import test_ai_config_view
        import json
        
        # 获取测试用户
        user = User.objects.get(username='testuser')
        
        # 创建请求工厂
        factory = RequestFactory()
        
        # 创建POST请求
        request = factory.post('/api/test-ai-config/', 
                              content_type='application/json')
        request.user = user
        
        # 调用视图
        response = test_ai_config_view(request)
        
        # 解析响应
        response_data = json.loads(response.content.decode())
        
        print(f"📥 响应状态码: {response.status_code}")
        print(f"📄 响应内容: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        if response_data.get('success'):
            print("✅ Web请求测试成功!")
            return True
        else:
            print(f"❌ Web请求测试失败: {response_data.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Web请求测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_default_settings():
    """检查默认设置"""
    print("\n⚙️ 检查默认设置...")
    print("=" * 50)
    
    try:
        from django.conf import settings
        
        print(f"OPENAI_API_KEY: {'已设置' if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY else '未设置'}")
        print(f"OPENAI_BASE_URL: {getattr(settings, 'OPENAI_BASE_URL', '未设置')}")
        print(f"OPENAI_MODEL: {getattr(settings, 'OPENAI_MODEL', '未设置')}")
        
        # 测试没有用户配置时的默认行为
        from readify.ai_services.services import AIService
        
        print(f"\n🔧 测试默认配置...")
        ai_service = AIService(user=None)  # 没有用户
        
        print(f"   默认提供商: {ai_service.config['provider']}")
        print(f"   默认API地址: {ai_service.config['api_url']}")
        print(f"   默认模型: {ai_service.config['model_id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查默认设置失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 Web界面AI配置测试工具")
    print("=" * 50)
    
    # 检查默认设置
    check_default_settings()
    
    # 测试用户AI配置
    if test_user_ai_config():
        print("\n🎉 用户AI配置测试通过!")
        
        # 模拟Web请求
        if simulate_web_request():
            print("\n✅ 所有测试通过! Web界面AI配置功能正常。")
        else:
            print("\n⚠️ 用户配置正常但Web请求测试失败")
    else:
        print("\n❌ 用户AI配置测试失败")
    
    print("\n💡 如果仍然遇到问题，请检查:")
    print("   1. 确保在Web界面中选择了'自定义'提供商")
    print("   2. 确保API密钥和模型名称正确")
    print("   3. 确保配置已保存并启用")
    print("   4. 检查浏览器控制台是否有错误信息")

if __name__ == "__main__":
    main() 