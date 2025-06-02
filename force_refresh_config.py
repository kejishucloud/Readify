#!/usr/bin/env python
"""
强制刷新用户AI配置
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def force_refresh_user_config():
    """强制刷新用户AI配置"""
    try:
        from django.contrib.auth.models import User
        from readify.user_management.models import UserAIConfig
        from readify.ai_services.services import AIService
        
        # 获取用户
        user = User.objects.get(username='kejishucloud')
        print(f"👤 用户: {user.username}")
        
        # 删除现有配置
        try:
            old_config = UserAIConfig.objects.get(user=user)
            old_config.delete()
            print("🗑️ 删除旧配置")
        except UserAIConfig.DoesNotExist:
            print("ℹ️ 没有找到旧配置")
        
        # 创建新配置
        new_config = UserAIConfig.objects.create(
            user=user,
            provider='custom',
            api_url='http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1',
            api_key='90a07e44-8cb3-4e83-bb92-056e271b0307',
            model_id='Qwen3-30B-A3B',
            max_tokens=4000,
            temperature=0.7,
            timeout=30,
            is_active=True
        )
        
        print("✅ 创建新配置:")
        print(f"   ID: {new_config.id}")
        print(f"   提供商: {new_config.provider}")
        print(f"   API地址: {new_config.api_url}")
        print(f"   模型: {new_config.model_id}")
        print(f"   API密钥: {new_config.api_key[:8]}...{new_config.api_key[-4:]}")
        print(f"   是否启用: {new_config.is_active}")
        
        # 测试新配置
        print(f"\n🧪 测试新配置...")
        
        # 创建新的AI服务实例
        ai_service = AIService(user=user)
        
        print(f"   AI服务配置:")
        print(f"     提供商: {ai_service.config['provider']}")
        print(f"     API地址: {ai_service.config['api_url']}")
        print(f"     模型: {ai_service.config['model_id']}")
        print(f"     API密钥: {ai_service.config['api_key'][:8]}...{ai_service.config['api_key'][-4:]}")
        
        # 发送测试请求
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回复'配置刷新测试成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            print(f"✅ 配置刷新测试成功!")
            print(f"   AI回复: {result['content'][:100]}...")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            print(f"   使用令牌: {result['tokens_used']}")
            return True
        else:
            print(f"❌ 配置刷新测试失败: {result['error']}")
            return False
        
    except Exception as e:
        print(f"❌ 强制刷新配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_web_view_directly():
    """直接测试Web视图"""
    print(f"\n🌐 直接测试Web视图...")
    
    try:
        from django.test import RequestFactory
        from django.contrib.auth.models import User
        from readify.user_management.views import test_ai_config_view
        import json
        
        user = User.objects.get(username='kejishucloud')
        
        # 创建请求
        factory = RequestFactory()
        request = factory.post('/user/ai-config/test/', content_type='application/json')
        request.user = user
        
        print(f"   请求用户: {request.user.username}")
        
        # 调用视图
        response = test_ai_config_view(request)
        response_data = json.loads(response.content.decode())
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        return response_data.get('success', False)
        
    except Exception as e:
        print(f"❌ Web视图测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔄 强制刷新用户AI配置")
    print("=" * 50)
    
    config_ok = force_refresh_user_config()
    
    if config_ok:
        web_ok = test_web_view_directly()
        
        if web_ok:
            print("\n🎉 配置刷新成功! 现在请在浏览器中重新测试。")
            print("\n💡 建议:")
            print("   1. 刷新浏览器页面 (Ctrl+F5)")
            print("   2. 清除浏览器缓存")
            print("   3. 重新点击'测试配置'按钮")
        else:
            print("\n⚠️ 配置刷新成功但Web视图测试失败")
    else:
        print("\n❌ 配置刷新失败") 