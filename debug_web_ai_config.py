#!/usr/bin/env python
"""
调试Web界面AI配置功能
"""
import os
import sys
import django
import json

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def debug_ai_config_flow():
    """调试AI配置流程"""
    print("🔍 调试AI配置流程...")
    print("=" * 60)
    
    try:
        from django.contrib.auth.models import User
        from readify.user_management.models import UserAIConfig
        from readify.ai_services.services import AIService
        
        # 获取用户
        user = User.objects.get(username='kejishucloud')
        print(f"👤 用户: {user.username}")
        
        # 检查用户AI配置
        try:
            config = UserAIConfig.objects.get(user=user)
            print(f"✅ 找到用户AI配置:")
            print(f"   ID: {config.id}")
            print(f"   提供商: {config.provider}")
            print(f"   API地址: {config.api_url}")
            print(f"   模型: {config.model_id}")
            print(f"   API密钥: {config.api_key[:8]}...{config.api_key[-4:]}")
            print(f"   最大令牌: {config.max_tokens}")
            print(f"   温度: {config.temperature}")
            print(f"   超时: {config.timeout}")
            print(f"   是否启用: {config.is_active}")
            
            # 测试配置方法
            print(f"\n🔧 测试配置方法:")
            headers = config.get_headers()
            endpoint = config.get_chat_endpoint()
            print(f"   请求头: {headers}")
            print(f"   端点: {endpoint}")
            
        except UserAIConfig.DoesNotExist:
            print("❌ 没有找到用户AI配置")
            return False
        
        # 测试AI服务初始化
        print(f"\n🤖 测试AI服务初始化:")
        ai_service = AIService(user=user)
        
        print(f"   AI服务配置:")
        for key, value in ai_service.config.items():
            if key == 'api_key':
                print(f"     {key}: {value[:8]}...{value[-4:] if len(value) > 12 else value}")
            else:
                print(f"     {key}: {value}")
        
        # 模拟Web请求
        print(f"\n🌐 模拟Web请求:")
        from django.test import RequestFactory
        from readify.user_management.views import test_ai_config_view
        
        factory = RequestFactory()
        request = factory.post('/user/ai-config/test/', content_type='application/json')
        request.user = user
        
        print(f"   请求用户: {request.user.username}")
        print(f"   请求路径: /user/ai-config/test/")
        
        # 调用视图
        response = test_ai_config_view(request)
        response_data = json.loads(response.content.decode())
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应数据: {json.dumps(response_data, indent=4, ensure_ascii=False)}")
        
        return response_data.get('success', False)
        
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_api_call():
    """直接测试API调用"""
    print(f"\n🔗 直接测试API调用:")
    print("=" * 60)
    
    try:
        import requests
        
        config = {
            'api_url': 'http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1',
            'api_key': '90a07e44-8cb3-4e83-bb92-056e271b0307',
            'model_id': 'Qwen3-30B-A3B'
        }
        
        endpoint = f"{config['api_url'].rstrip('/')}/chat/completions"
        headers = {
            'Authorization': f"Bearer {config['api_key']}",
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': config['model_id'],
            'messages': [
                {'role': 'user', 'content': '请回复"直接API测试成功"'}
            ],
            'max_tokens': 100,
            'temperature': 0.7
        }
        
        print(f"   端点: {endpoint}")
        print(f"   请求头: {headers}")
        print(f"   请求数据: {json.dumps(data, indent=4, ensure_ascii=False)}")
        
        response = requests.post(endpoint, headers=headers, json=data, timeout=30)
        
        print(f"   响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 直接API调用成功!")
            print(f"   响应: {json.dumps(result, indent=4, ensure_ascii=False)}")
            return True
        else:
            print(f"   ❌ 直接API调用失败:")
            try:
                error_info = response.json()
                print(f"   错误: {json.dumps(error_info, indent=4, ensure_ascii=False)}")
            except:
                print(f"   错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 直接API测试失败: {str(e)}")
        return False

def check_ai_service_config_loading():
    """检查AI服务配置加载"""
    print(f"\n⚙️ 检查AI服务配置加载:")
    print("=" * 60)
    
    try:
        from django.contrib.auth.models import User
        from readify.ai_services.services import AIService
        
        user = User.objects.get(username='kejishucloud')
        
        # 创建AI服务实例并检查配置加载过程
        print(f"   创建AI服务实例...")
        ai_service = AIService(user=user)
        
        # 手动调用配置获取方法
        print(f"   手动调用_get_user_config()...")
        config = ai_service._get_user_config()
        
        print(f"   配置结果:")
        for key, value in config.items():
            if key == 'api_key':
                print(f"     {key}: {value[:8]}...{value[-4:] if len(value) > 12 else value}")
            else:
                print(f"     {key}: {value}")
        
        # 检查是否有headers和endpoint
        if 'headers' in config:
            print(f"   ✅ 配置包含headers")
        else:
            print(f"   ❌ 配置缺少headers")
            
        if 'endpoint' in config:
            print(f"   ✅ 配置包含endpoint")
        else:
            print(f"   ❌ 配置缺少endpoint")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查配置加载失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 Web界面AI配置调试工具")
    print("=" * 60)
    
    # 检查AI服务配置加载
    config_ok = check_ai_service_config_loading()
    
    # 直接测试API调用
    api_ok = test_direct_api_call()
    
    # 调试AI配置流程
    flow_ok = debug_ai_config_flow()
    
    print(f"\n📊 调试结果总结:")
    print("=" * 60)
    print(f"   配置加载: {'✅ 正常' if config_ok else '❌ 异常'}")
    print(f"   直接API: {'✅ 正常' if api_ok else '❌ 异常'}")
    print(f"   Web流程: {'✅ 正常' if flow_ok else '❌ 异常'}")
    
    if config_ok and api_ok and flow_ok:
        print(f"\n🎉 所有测试通过! Web界面AI配置应该可以正常工作。")
    else:
        print(f"\n⚠️ 发现问题，需要进一步调试。")
        
        if not config_ok:
            print(f"   - 配置加载有问题")
        if not api_ok:
            print(f"   - API调用有问题")
        if not flow_ok:
            print(f"   - Web流程有问题")

if __name__ == "__main__":
    main() 