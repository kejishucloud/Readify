#!/usr/bin/env python
"""
AI配置测试脚本
用于测试自定义AI服务配置
"""
import os
import sys
import django
import requests
import json

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def test_custom_ai_config():
    """测试自定义AI配置"""
    print("🔍 测试自定义AI配置...")
    print("=" * 50)
    
    # 您的配置信息
    config = {
        'model': 'Qwen3-30B-A3B',
        'api_url': 'http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1',
        'api_key': '90a07e44-8cb3-4e83-bb92-056e271b0307',
        'max_tokens': 4000,
        'temperature': 0.7
    }
    
    # 构建请求
    endpoint = f"{config['api_url'].rstrip('/')}/chat/completions"
    headers = {
        'Authorization': f"Bearer {config['api_key']}",
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': config['model'],
        'messages': [
            {
                'role': 'user',
                'content': '请回复"AI配置测试成功"'
            }
        ],
        'max_tokens': config['max_tokens'],
        'temperature': config['temperature']
    }
    
    print(f"📡 API端点: {endpoint}")
    print(f"🤖 模型: {config['model']}")
    print(f"🔑 API密钥: {config['api_key'][:8]}...")
    print()
    
    try:
        print("📤 发送测试请求...")
        response = requests.post(
            endpoint,
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 请求成功！")
            print(f"📝 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 尝试解析响应
            if 'choices' in result and result['choices']:
                content = result['choices'][0]['message']['content']
                print(f"🎯 AI回复: {content}")
                return True
            else:
                print("⚠️  响应格式不符合预期")
                return False
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            try:
                error_info = response.json()
                print(f"📄 错误详情: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
            except:
                print(f"📄 错误详情: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请检查网络和API地址")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def test_different_auth_methods():
    """测试不同的认证方式"""
    print("\n🔐 测试不同认证方式...")
    print("=" * 50)
    
    config = {
        'model': 'Qwen3-30B-A3B',
        'api_url': 'http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1',
        'api_key': '90a07e44-8cb3-4e83-bb92-056e271b0307',
    }
    
    endpoint = f"{config['api_url'].rstrip('/')}/chat/completions"
    
    # 测试不同的认证方式
    auth_methods = [
        ('Bearer Token', {'Authorization': f"Bearer {config['api_key']}"}),
        ('API Key Header', {'X-API-Key': config['api_key']}),
        ('Custom Auth', {'Authorization': config['api_key']}),
    ]
    
    data = {
        'model': config['model'],
        'messages': [{'role': 'user', 'content': '测试'}],
        'max_tokens': 100
    }
    
    for auth_name, auth_headers in auth_methods:
        print(f"\n🔑 测试 {auth_name}...")
        headers = {'Content-Type': 'application/json'}
        headers.update(auth_headers)
        
        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=10)
            print(f"   状态码: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ {auth_name} 认证成功")
                return auth_headers
            else:
                print(f"   ❌ {auth_name} 认证失败")
        except Exception as e:
            print(f"   ❌ {auth_name} 测试异常: {str(e)}")
    
    return None

def save_working_config():
    """保存可用的配置到Django"""
    print("\n💾 保存配置到Django...")
    
    try:
        from django.contrib.auth.models import User
        from readify.user_management.models import UserAIConfig
        
        # 获取第一个用户（或创建测试用户）
        user = User.objects.first()
        if not user:
            print("⚠️  没有找到用户，请先创建用户账户")
            return False
        
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
        
        print(f"✅ 配置已保存到用户 {user.username}")
        return True
        
    except Exception as e:
        print(f"❌ 保存配置失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 Readify AI配置测试工具")
    print("=" * 50)
    
    # 测试基本配置
    if test_custom_ai_config():
        print("\n🎉 基本配置测试通过！")
        
        # 保存配置
        if save_working_config():
            print("\n✅ 配置已保存，您现在可以在Readify中使用AI功能了！")
        else:
            print("\n⚠️  配置测试通过但保存失败，请手动配置")
    else:
        print("\n❌ 基本配置测试失败")
        
        # 尝试不同的认证方式
        working_auth = test_different_auth_methods()
        if working_auth:
            print(f"\n✅ 找到可用的认证方式: {working_auth}")
        else:
            print("\n❌ 所有认证方式都失败了")
            print("\n💡 建议检查:")
            print("   1. API地址是否正确")
            print("   2. API密钥是否有效")
            print("   3. 网络连接是否正常")
            print("   4. 服务器是否在线")

if __name__ == "__main__":
    main() 