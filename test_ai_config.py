#!/usr/bin/env python
"""
AI配置测试脚本
用于验证OpenAI API配置是否正确
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.ai_services.services import AIService
from readify.user_management.models import UserAIConfig

def test_environment_variables():
    """测试环境变量配置"""
    print("🔍 检查环境变量配置...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    if not api_key:
        print("❌ 环境变量 OPENAI_API_KEY 未设置")
        return False
    
    if not api_key.startswith('sk-'):
        print("❌ API密钥格式不正确，应该以 'sk-' 开头")
        return False
    
    print(f"✅ API密钥: {api_key[:10]}...{api_key[-4:]}")
    print(f"✅ 模型: {model}")
    print(f"✅ API地址: {base_url}")
    return True

def test_database_config():
    """测试数据库配置"""
    print("\n🔍 检查数据库AI配置...")
    
    try:
        # 获取演示用户
        user = User.objects.get(username='demo_user')
        print(f"✅ 找到演示用户: {user.username}")
        
        # 检查用户AI配置
        ai_configs = UserAIConfig.objects.filter(user=user)
        if ai_configs.exists():
            config = ai_configs.first()
            print(f"✅ 用户AI配置存在")
            print(f"   提供商: {config.provider}")
            print(f"   模型: {config.model_id}")
            print(f"   API地址: {config.api_base_url}")
            if config.api_key:
                print(f"   API密钥: {config.api_key[:10]}...{config.api_key[-4:]}")
            return True, user
        else:
            print("⚠️ 用户AI配置不存在，将使用环境变量")
            return True, user
            
    except User.DoesNotExist:
        print("❌ 演示用户不存在，请先运行 demo_features.py")
        return False, None
    except Exception as e:
        print(f"❌ 数据库配置检查失败: {str(e)}")
        return False, None

def test_ai_service(user):
    """测试AI服务"""
    print("\n🔍 测试AI服务连接...")
    
    try:
        # 初始化AI服务
        ai_service = AIService(user)
        print("✅ AI服务初始化成功")
        
        # 测试简单对话
        test_messages = [
            {"role": "user", "content": "你好，这是一个测试消息。请简单回复'测试成功'。"}
        ]
        
        print("🚀 发送测试请求...")
        response = ai_service.chat(test_messages)
        
        if response:
            print("✅ AI服务测试成功！")
            print(f"📝 AI响应: {response}")
            return True
        else:
            print("❌ AI服务返回空响应")
            return False
            
    except Exception as e:
        print(f"❌ AI服务测试失败: {str(e)}")
        return False

def create_user_ai_config(user):
    """创建用户AI配置"""
    print("\n🛠️ 创建用户AI配置...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 无法创建配置：环境变量中没有API密钥")
        return False
    
    try:
        config, created = UserAIConfig.objects.get_or_create(
            user=user,
            defaults={
                'provider': 'openai',
                'api_base_url': 'https://api.openai.com/v1',
                'api_key': api_key,
                'model_id': 'gpt-3.5-turbo',
                'max_tokens': 4000,
                'temperature': 0.7,
                'is_enabled': True
            }
        )
        
        if created:
            print("✅ 用户AI配置创建成功")
        else:
            print("✅ 用户AI配置已存在")
            
        return True
        
    except Exception as e:
        print(f"❌ 创建用户AI配置失败: {str(e)}")
        return False

def show_setup_guide():
    """显示设置指南"""
    print("\n📋 AI配置设置指南")
    print("=" * 50)
    
    print("方法一：环境变量配置（推荐）")
    print("1. 在项目根目录创建 .env 文件")
    print("2. 添加以下内容：")
    print("   OPENAI_API_KEY=sk-your_actual_api_key_here")
    print("   OPENAI_MODEL=gpt-3.5-turbo")
    print("   OPENAI_BASE_URL=https://api.openai.com/v1")
    
    print("\n方法二：临时设置（Windows PowerShell）")
    print('   $env:OPENAI_API_KEY="sk-your_actual_api_key_here"')
    
    print("\n方法三：临时设置（Linux/Mac）")
    print('   export OPENAI_API_KEY="sk-your_actual_api_key_here"')
    
    print("\n🔗 获取API密钥：")
    print("   访问：https://platform.openai.com/account/api-keys")
    print("   登录并创建新的API密钥")

def main():
    """主函数"""
    print("🤖 Readify AI配置测试")
    print("=" * 50)
    
    # 1. 测试环境变量
    env_ok = test_environment_variables()
    
    # 2. 测试数据库配置
    db_ok, user = test_database_config()
    
    if not db_ok:
        print("\n❌ 数据库配置测试失败")
        show_setup_guide()
        return 1
    
    # 3. 如果环境变量配置正确但数据库配置不存在，创建配置
    if env_ok and user:
        ai_configs = UserAIConfig.objects.filter(user=user)
        if not ai_configs.exists():
            create_user_ai_config(user)
    
    # 4. 测试AI服务
    if user:
        ai_ok = test_ai_service(user)
        
        if ai_ok:
            print("\n🎉 所有测试通过！AI配置正确。")
            print("现在您可以正常使用AI助手功能了。")
            return 0
        else:
            print("\n❌ AI服务测试失败")
    
    # 显示设置指南
    show_setup_guide()
    return 1

if __name__ == '__main__':
    sys.exit(main()) 