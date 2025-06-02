#!/usr/bin/env python
"""
模拟真实Web请求测试AI配置
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def test_real_web_request():
    """模拟真实的Web请求"""
    print("🌐 模拟真实Web请求测试...")
    print("=" * 60)
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        
        # 创建测试客户端
        client = Client()
        
        # 获取用户
        user = User.objects.get(username='kejishucloud')
        
        # 强制登录用户
        client.force_login(user)
        print(f"✅ 用户 {user.username} 已登录")
        
        # 1. 测试获取AI配置
        print(f"\n1️⃣ 测试获取AI配置...")
        config_response = client.get('/user/ai-config/')
        
        print(f"   响应状态码: {config_response.status_code}")
        
        if config_response.status_code == 200:
            config_data = json.loads(config_response.content.decode())
            print(f"   ✅ 配置获取成功:")
            print(f"   📄 配置数据: {json.dumps(config_data, indent=4, ensure_ascii=False)}")
            
            # 检查配置是否正确
            if config_data.get('success') and config_data.get('config', {}).get('provider') == 'custom':
                print(f"   ✅ 配置显示为自定义提供商")
            else:
                print(f"   ❌ 配置显示不正确")
                return False
        else:
            print(f"   ❌ 配置获取失败")
            return False
        
        # 2. 测试AI配置
        print(f"\n2️⃣ 测试AI配置...")
        test_response = client.post('/user/ai-config/test/')
        
        print(f"   响应状态码: {test_response.status_code}")
        
        if test_response.status_code == 200:
            test_data = json.loads(test_response.content.decode())
            print(f"   📄 测试响应: {json.dumps(test_data, indent=4, ensure_ascii=False)}")
            
            if test_data.get('success'):
                print(f"   ✅ AI配置测试成功!")
                return True
            else:
                print(f"   ❌ AI配置测试失败: {test_data.get('message')}")
                return False
        else:
            print(f"   ❌ 测试请求失败")
            try:
                error_data = json.loads(test_response.content.decode())
                print(f"   📄 错误数据: {json.dumps(error_data, indent=4, ensure_ascii=False)}")
            except:
                print(f"   📄 错误文本: {test_response.content.decode()}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_service_directly():
    """直接测试AI服务"""
    print(f"\n🤖 直接测试AI服务...")
    print("=" * 60)
    
    try:
        from django.contrib.auth.models import User
        from readify.ai_services.services import AIService
        
        user = User.objects.get(username='kejishucloud')
        
        # 创建AI服务实例
        ai_service = AIService(user=user)
        
        print(f"   用户: {user.username}")
        print(f"   AI服务配置:")
        print(f"     提供商: {ai_service.config['provider']}")
        print(f"     API地址: {ai_service.config['api_url']}")
        print(f"     模型: {ai_service.config['model_id']}")
        print(f"     API密钥: {ai_service.config['api_key'][:8]}...{ai_service.config['api_key'][-4:]}")
        
        # 发送测试请求
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回复'直接服务测试成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            print(f"   ✅ 直接服务测试成功!")
            print(f"   AI回复: {result['content'][:100]}...")
            print(f"   处理时间: {result['processing_time']:.2f}秒")
            print(f"   使用令牌: {result['tokens_used']}")
            return True
        else:
            print(f"   ❌ 直接服务测试失败: {result['error']}")
            return False
        
    except Exception as e:
        print(f"❌ 直接服务测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_database_config():
    """检查数据库中的配置"""
    print(f"\n💾 检查数据库配置...")
    print("=" * 60)
    
    try:
        from django.contrib.auth.models import User
        from readify.user_management.models import UserAIConfig
        
        user = User.objects.get(username='kejishucloud')
        
        # 获取所有该用户的AI配置
        configs = UserAIConfig.objects.filter(user=user)
        
        print(f"   用户 {user.username} 的AI配置:")
        for config in configs:
            print(f"     ID: {config.id}")
            print(f"     提供商: {config.provider}")
            print(f"     API地址: {config.api_url}")
            print(f"     模型: {config.model_id}")
            print(f"     API密钥: {config.api_key[:8]}...{config.api_key[-4:]}")
            print(f"     是否启用: {config.is_active}")
            print(f"     创建时间: {config.created_at}")
            print(f"     更新时间: {config.updated_at}")
            print(f"     ---")
        
        # 获取当前活跃的配置
        try:
            active_config = UserAIConfig.objects.get(user=user, is_active=True)
            print(f"   ✅ 当前活跃配置: ID {active_config.id}")
            return True
        except UserAIConfig.DoesNotExist:
            print(f"   ❌ 没有找到活跃的配置")
            return False
        except UserAIConfig.MultipleObjectsReturned:
            print(f"   ⚠️ 找到多个活跃配置，这可能导致问题")
            return False
        
    except Exception as e:
        print(f"❌ 检查数据库配置失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 真实Web请求AI配置测试")
    print("=" * 60)
    
    # 检查数据库配置
    db_ok = check_database_config()
    
    # 直接测试AI服务
    service_ok = test_ai_service_directly()
    
    # 模拟真实Web请求
    web_ok = test_real_web_request()
    
    print(f"\n📊 测试结果总结:")
    print("=" * 60)
    print(f"   数据库配置: {'✅ 正常' if db_ok else '❌ 异常'}")
    print(f"   AI服务: {'✅ 正常' if service_ok else '❌ 异常'}")
    print(f"   Web请求: {'✅ 正常' if web_ok else '❌ 异常'}")
    
    if db_ok and service_ok and web_ok:
        print(f"\n🎉 所有测试通过! Web界面AI配置应该可以正常工作。")
        print(f"\n💡 如果浏览器中仍然有问题，请:")
        print(f"   1. 硬刷新页面 (Ctrl+F5)")
        print(f"   2. 清除浏览器缓存")
        print(f"   3. 检查浏览器开发者工具的Console和Network标签页")
    else:
        print(f"\n⚠️ 发现问题:")
        if not db_ok:
            print(f"   - 数据库配置有问题")
        if not service_ok:
            print(f"   - AI服务有问题")
        if not web_ok:
            print(f"   - Web请求有问题")

if __name__ == "__main__":
    main() 