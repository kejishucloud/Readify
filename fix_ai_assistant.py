#!/usr/bin/env python
"""
Readify AI助手快速修复脚本
自动修复常见的AI助手问题
"""

import os
import sys
import django
import shutil
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def fix_static_files():
    """修复静态文件问题"""
    print("🔧 修复静态文件...")
    
    try:
        # 复制前端文件到staticfiles
        frontend_js = project_root / 'frontend' / 'static' / 'js'
        static_js = project_root / 'staticfiles' / 'js'
        
        if frontend_js.exists() and static_js.exists():
            # 复制reader.js
            if (frontend_js / 'reader.js').exists():
                shutil.copy2(frontend_js / 'reader.js', static_js / 'reader.js')
                print("✅ 已更新staticfiles/js/reader.js")
            
            # 复制main.js
            if (frontend_js / 'main.js').exists():
                shutil.copy2(frontend_js / 'main.js', static_js / 'main.js')
                print("✅ 已更新staticfiles/js/main.js")
        
        return True
    except Exception as e:
        print(f"❌ 静态文件修复失败: {e}")
        return False

def fix_user_ai_config():
    """修复用户AI配置"""
    print("\n🔧 修复用户AI配置...")
    
    try:
        from django.contrib.auth.models import User
        from readify.user_management.models import UserAIConfig
        from django.conf import settings
        
        # 获取所有用户
        users = User.objects.all()
        
        for user in users:
            # 检查用户是否有AI配置
            config, created = UserAIConfig.objects.get_or_create(
                user=user,
                defaults={
                    'provider': 'custom' if getattr(settings, 'OPENAI_MODEL', '').startswith('Qwen') else 'openai',
                    'api_url': getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                    'api_key': '',  # 用户需要自己设置
                    'model_id': getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
                    'max_tokens': 4000,
                    'temperature': 0.7,
                    'timeout': 30,
                    'is_active': True
                }
            )
            
            if created:
                print(f"✅ 为用户 {user.username} 创建了AI配置")
            else:
                print(f"✅ 用户 {user.username} 已有AI配置")
        
        return True
    except Exception as e:
        print(f"❌ 用户AI配置修复失败: {e}")
        return False

def fix_database_migrations():
    """修复数据库迁移"""
    print("\n🔧 检查数据库迁移...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # 检查是否有未应用的迁移
        print("检查迁移状态...")
        execute_from_command_line(['manage.py', 'showmigrations'])
        
        # 应用迁移
        print("应用迁移...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ 数据库迁移完成")
        return True
    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        return False

def fix_ai_models():
    """修复AI模型配置"""
    print("\n🔧 修复AI模型配置...")
    
    try:
        from readify.ai_services.models import AIModel
        from django.conf import settings

        # 创建默认AI模型
        models_to_create = [
            {
                'name': 'Qwen3-30B-A3B',
                'provider': 'custom',
                'api_endpoint': getattr(settings, 'OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/api/v1'),
                'model_id': 'Qwen3-30B-A3B',
                'description': '通义千问3代30B模型',
                'max_tokens': 8000,
                'temperature': 0.7,
                'is_active': True
            },
            {
                'name': 'GPT-3.5-Turbo',
                'provider': 'openai',
                'api_endpoint': 'https://api.openai.com/v1',
                'model_id': 'gpt-3.5-turbo',
                'description': 'OpenAI GPT-3.5 Turbo模型',
                'max_tokens': 4000,
                'temperature': 0.7,
                'is_active': True
            }
        ]
        
        for model_data in models_to_create:
            model, created = AIModel.objects.update_or_create(
                model_id=model_data['model_id'],
                defaults=model_data
            )

            if created:
                print(f"✅ 创建AI模型: {model_data['name']}")
            else:
                print(f"✅ 更新AI模型: {model_data['name']}")
        
        return True
    except Exception as e:
        print(f"❌ AI模型配置修复失败: {e}")
        return False

def create_env_file():
    """创建环境配置文件"""
    print("\n🔧 检查环境配置文件...")
    
    env_file = project_root / '.env'
    env_example = project_root / 'env.example'
    
    if not env_file.exists() and env_example.exists():
        try:
            shutil.copy2(env_example, env_file)
            print("✅ 已创建.env文件，请编辑其中的配置")
            print("⚠️  请设置正确的API密钥和端点")
            return True
        except Exception as e:
            print(f"❌ 创建.env文件失败: {e}")
            return False
    elif env_file.exists():
        print("✅ .env文件已存在")
        return True
    else:
        print("❌ 未找到env.example文件")
        return False

def fix_permissions():
    """修复文件权限"""
    print("\n🔧 修复文件权限...")
    
    try:
        # 确保日志目录存在且可写
        logs_dir = project_root / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        # 确保媒体目录存在且可写
        media_dir = project_root / 'media'
        media_dir.mkdir(exist_ok=True)
        
        # 确保静态文件目录存在
        static_dir = project_root / 'staticfiles'
        static_dir.mkdir(exist_ok=True)
        
        print("✅ 目录权限检查完成")
        return True
    except Exception as e:
        print(f"❌ 文件权限修复失败: {e}")
        return False

def test_ai_service():
    """测试AI服务"""
    print("\n🧪 测试AI服务...")
    
    try:
        from readify.ai_services.services import AIService
        from django.contrib.auth.models import User
        
        # 获取第一个用户进行测试
        user = User.objects.first()
        if not user:
            print("❌ 没有找到用户，请先创建用户")
            return False
        
        ai_service = AIService(user=user)
        
        # 测试简单请求
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请简单回答：你好"}],
            "你是一个友好的助手。"
        )
        
        if result['success']:
            print("✅ AI服务测试成功")
            print(f"   回答: {result['content'][:50]}...")
            return True
        else:
            print(f"❌ AI服务测试失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ AI服务测试失败: {e}")
        return False

def main():
    """主修复函数"""
    print("=" * 60)
    print("    Readify AI助手快速修复工具")
    print("=" * 60)
    
    fixes = [
        ("环境配置文件", create_env_file),
        ("文件权限", fix_permissions),
        ("数据库迁移", fix_database_migrations),
        ("AI模型配置", fix_ai_models),
        ("用户AI配置", fix_user_ai_config),
        ("静态文件", fix_static_files),
        ("AI服务测试", test_ai_service),
    ]
    
    success_count = 0
    total_count = len(fixes)
    
    for fix_name, fix_func in fixes:
        print(f"\n{'='*20} {fix_name} {'='*20}")
        try:
            if fix_func():
                success_count += 1
        except Exception as e:
            print(f"❌ {fix_name}修复出错: {e}")
    
    print("\n" + "=" * 60)
    print(f"修复完成: {success_count}/{total_count} 项成功")
    
    if success_count == total_count:
        print("🎉 所有修复项目都成功完成！")
        print("\n📋 下一步操作:")
        print("1. 编辑.env文件，设置正确的API密钥")
        print("2. 运行: python check_status.py")
        print("3. 启动服务: python manage.py runserver")
    else:
        print("⚠️  部分修复项目失败，请查看上述错误信息")
        print("\n📖 详细指南请参考: AI_ASSISTANT_OPTIMIZATION_GUIDE.md")
    
    print("=" * 60)
    
    return 0 if success_count == total_count else 1

if __name__ == '__main__':
    sys.exit(main()) 