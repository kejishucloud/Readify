#!/usr/bin/env python
"""
环境变量设置脚本
帮助用户快速配置OpenAI API密钥
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """创建.env文件"""
    print("🔧 Readify AI配置助手")
    print("=" * 50)
    
    # 检查是否已存在.env文件
    env_file = Path('.env')
    if env_file.exists():
        print("⚠️ .env文件已存在")
        overwrite = input("是否覆盖现有配置？(y/N): ").lower().strip()
        if overwrite != 'y':
            print("❌ 取消操作")
            return False
    
    print("\n请输入您的OpenAI API配置信息：")
    print("（如果您没有API密钥，请访问：https://platform.openai.com/account/api-keys）")
    
    # 获取用户输入
    api_key = input("\n🔑 OpenAI API密钥 (sk-...): ").strip()
    
    if not api_key:
        print("❌ API密钥不能为空")
        return False
    
    if not api_key.startswith('sk-'):
        print("⚠️ 警告：API密钥通常以 'sk-' 开头")
        confirm = input("是否继续？(y/N): ").lower().strip()
        if confirm != 'y':
            return False
    
    # 可选配置
    model = input("🤖 模型名称 (默认: gpt-3.5-turbo): ").strip() or "gpt-3.5-turbo"
    base_url = input("🌐 API地址 (默认: https://api.openai.com/v1): ").strip() or "https://api.openai.com/v1"
    
    # 创建.env文件内容
    env_content = f"""# Readify 环境变量配置文件
# 由setup_env.py自动生成

# Django 基础配置
SECRET_KEY=django-insecure-xhf&x6@xlty7)t9p21gv7l-2*-vmuaa(l5=w_ml&eae*7512nf
DEBUG=True

# OpenAI API 配置
OPENAI_API_KEY={api_key}
OPENAI_MODEL={model}
OPENAI_BASE_URL={base_url}

# 数据库配置（可选）
# DATABASE_URL=sqlite:///db.sqlite3

# Redis配置（可选）
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ChatTTS配置（可选）
# CHATTTS_MODEL_PATH=/path/to/chattts/models
# CHATTTS_SAMPLE_RATE=24000
# CHATTTS_MAX_TEXT_LENGTH=1000
"""
    
    try:
        # 写入.env文件
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("\n✅ .env文件创建成功！")
        print(f"📁 文件位置: {env_file.absolute()}")
        
        # 显示配置信息
        print("\n📋 配置信息:")
        print(f"   API密钥: {api_key[:10]}...{api_key[-4:]}")
        print(f"   模型: {model}")
        print(f"   API地址: {base_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建.env文件失败: {str(e)}")
        return False

def set_temp_env():
    """设置临时环境变量"""
    print("\n🔧 设置临时环境变量")
    print("=" * 50)
    
    api_key = input("🔑 OpenAI API密钥 (sk-...): ").strip()
    
    if not api_key:
        print("❌ API密钥不能为空")
        return False
    
    # 设置环境变量
    os.environ['OPENAI_API_KEY'] = api_key
    os.environ['OPENAI_MODEL'] = 'gpt-3.5-turbo'
    os.environ['OPENAI_BASE_URL'] = 'https://api.openai.com/v1'
    
    print("✅ 临时环境变量设置成功！")
    print("⚠️ 注意：这些设置只在当前会话中有效")
    
    # 显示PowerShell命令
    print("\n💡 要在PowerShell中永久设置，请运行：")
    print(f'   $env:OPENAI_API_KEY="{api_key}"')
    print('   $env:OPENAI_MODEL="gpt-3.5-turbo"')
    print('   $env:OPENAI_BASE_URL="https://api.openai.com/v1"')
    
    return True

def test_configuration():
    """测试配置"""
    print("\n🧪 测试AI配置")
    print("=" * 50)
    
    try:
        # 导入Django并设置
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
        django.setup()
        
        from django.contrib.auth.models import User
        from readify.ai_services.services import AIService
        
        # 获取演示用户
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            print("⚠️ 演示用户不存在，使用默认配置测试")
            user = None
        
        # 测试AI服务
        ai_service = AIService(user)
        
        print("🚀 发送测试请求...")
        test_messages = [
            {"role": "user", "content": "请回复'AI配置测试成功'"}
        ]
        
        response = ai_service.chat(test_messages)
        
        print("✅ AI配置测试成功！")
        print(f"📝 AI响应: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI配置测试失败: {str(e)}")
        return False

def show_help():
    """显示帮助信息"""
    print("🆘 Readify AI配置帮助")
    print("=" * 50)
    
    print("1. 获取OpenAI API密钥：")
    print("   - 访问：https://platform.openai.com/account/api-keys")
    print("   - 登录您的OpenAI账户")
    print("   - 点击 'Create new secret key'")
    print("   - 复制生成的API密钥")
    
    print("\n2. 配置方式：")
    print("   - 方式1：创建.env文件（推荐）")
    print("   - 方式2：设置临时环境变量")
    print("   - 方式3：通过Web界面配置")
    
    print("\n3. 常见问题：")
    print("   - 401错误：API密钥无效或未设置")
    print("   - 429错误：API调用频率过高")
    print("   - 网络错误：检查网络连接")
    
    print("\n4. 免费替代方案：")
    print("   - DeepSeek API（免费额度）")
    print("   - 本地AI模型（Ollama）")
    print("   - 其他兼容OpenAI格式的API")

def main():
    """主函数"""
    print("🤖 Readify AI配置助手")
    print("=" * 50)
    
    while True:
        print("\n请选择操作：")
        print("1. 创建.env配置文件")
        print("2. 设置临时环境变量")
        print("3. 测试当前配置")
        print("4. 显示帮助信息")
        print("5. 退出")
        
        choice = input("\n请输入选项 (1-5): ").strip()
        
        if choice == '1':
            create_env_file()
        elif choice == '2':
            set_temp_env()
        elif choice == '3':
            test_configuration()
        elif choice == '4':
            show_help()
        elif choice == '5':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选项，请重新选择")

if __name__ == '__main__':
    main() 