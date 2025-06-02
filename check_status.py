#!/usr/bin/env python
"""
Readify项目状态检查脚本
检查AI配置、数据库连接、conda环境等
"""

import os
import sys
import django
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def check_conda_environment():
    """检查conda环境"""
    print("🔍 检查conda环境...")
    
    # 检查是否在conda环境中
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env:
        print(f"✅ 当前conda环境: {conda_env}")
        if conda_env == 'DL':
            print("✅ 正在使用推荐的DL环境")
        else:
            print("⚠️  建议使用DL环境: conda activate DL")
    else:
        print("❌ 未检测到conda环境")
        return False
    
    return True

def check_ai_configuration():
    """检查AI配置"""
    print("\n🔍 检查AI配置...")
    
    from django.conf import settings
    
    # 检查环境变量配置
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    api_url = getattr(settings, 'OPENAI_BASE_URL', '')
    model = getattr(settings, 'OPENAI_MODEL', '')
    
    if api_key:
        print(f"✅ API密钥已配置 (长度: {len(api_key)})")
    else:
        print("❌ API密钥未配置")
        return False
    
    if api_url:
        print(f"✅ API地址: {api_url}")
    else:
        print("❌ API地址未配置")
        return False
    
    if model:
        print(f"✅ AI模型: {model}")
    else:
        print("❌ AI模型未配置")
        return False
    
    return True

def check_database():
    """检查数据库连接"""
    print("\n🔍 检查数据库连接...")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ 数据库连接正常")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_ai_service():
    """检查AI服务"""
    print("\n🔍 检查AI服务...")
    
    try:
        from readify.ai_services.services import AIService
        from django.contrib.auth.models import User
        
        # 创建测试用户（如果不存在）
        test_user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )
        
        # 测试AI服务
        ai_service = AIService(user=test_user)
        config = ai_service.config
        
        print(f"✅ AI服务配置加载成功")
        print(f"   提供商: {config.get('provider', 'unknown')}")
        print(f"   模型: {config.get('model_id', 'unknown')}")
        print(f"   API地址: {config.get('api_url', 'unknown')}")
        
        # 测试简单的AI请求
        print("\n🧪 测试AI请求...")
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请回答：1+1等于几？"}],
            "你是一个数学助手。"
        )
        
        if result['success']:
            print("✅ AI请求测试成功")
            print(f"   回答: {result['content'][:50]}...")
        else:
            print(f"❌ AI请求测试失败: {result.get('error', '未知错误')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ AI服务检查失败: {e}")
        return False

def check_required_packages():
    """检查必需的Python包"""
    print("\n🔍 检查必需的Python包...")
    
    required_packages = [
        ('django', 'django'),
        ('requests', 'requests'),
        ('PIL', 'Pillow'),
        ('chardet', 'chardet')
    ]
    
    optional_packages = [
        ('magic', 'python-magic')
    ]
    
    missing_packages = []
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} (未安装)")
            missing_packages.append(package_name)
    
    # 检查可选包
    for import_name, package_name in optional_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name} (可选)")
        except ImportError:
            print(f"⚠️  {package_name} (可选，未安装)")
    
    if missing_packages:
        print(f"\n⚠️  缺少以下必需包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """主检查函数"""
    print("=" * 50)
    print("    Readify 智能阅读助手 - 状态检查")
    print("=" * 50)
    
    checks = [
        ("Conda环境", check_conda_environment),
        ("必需包", check_required_packages),
        ("数据库", check_database),
        ("AI配置", check_ai_configuration),
        ("AI服务", check_ai_service),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name}检查出错: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有检查通过！Readify已准备就绪。")
        print("💡 可以运行: python manage.py runserver")
    else:
        print("⚠️  部分检查未通过，请根据上述提示进行修复。")
        print("📖 详细配置指南请参考: AI_CONFIG_GUIDE.md")
    print("=" * 50)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main()) 