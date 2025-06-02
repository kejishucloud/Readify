#!/usr/bin/env python
"""
Readify项目状态检查脚本
"""
import os
import sys
import django
from django.conf import settings

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def check_database():
    """检查数据库连接"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ 数据库连接正常")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_models():
    """检查模型"""
    try:
        from readify.books.models import Book, BookCategory
        from readify.user_management.models import UserProfile
        
        # 检查是否有迁移需要应用
        from django.core.management import execute_from_command_line
        from io import StringIO
        import sys
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            execute_from_command_line(['manage.py', 'showmigrations', '--plan'])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        
        print("✅ 模型检查通过")
        return True
    except Exception as e:
        print(f"❌ 模型检查失败: {e}")
        return False

def check_static_files():
    """检查静态文件"""
    try:
        static_dirs = settings.STATICFILES_DIRS
        for static_dir in static_dirs:
            if os.path.exists(static_dir):
                print(f"✅ 静态文件目录存在: {static_dir}")
            else:
                print(f"⚠️  静态文件目录不存在: {static_dir}")
        return True
    except Exception as e:
        print(f"❌ 静态文件检查失败: {e}")
        return False

def check_media_files():
    """检查媒体文件目录"""
    try:
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root):
            print(f"✅ 媒体文件目录存在: {media_root}")
        else:
            os.makedirs(media_root, exist_ok=True)
            print(f"✅ 创建媒体文件目录: {media_root}")
        return True
    except Exception as e:
        print(f"❌ 媒体文件检查失败: {e}")
        return False

def check_logs():
    """检查日志目录"""
    try:
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        if os.path.exists(log_dir):
            print(f"✅ 日志目录存在: {log_dir}")
        else:
            os.makedirs(log_dir, exist_ok=True)
            print(f"✅ 创建日志目录: {log_dir}")
        return True
    except Exception as e:
        print(f"❌ 日志目录检查失败: {e}")
        return False

def main():
    """主检查函数"""
    print("🔍 开始检查Readify项目状态...")
    print("=" * 50)
    
    checks = [
        ("数据库", check_database),
        ("模型", check_models),
        ("静态文件", check_static_files),
        ("媒体文件", check_media_files),
        ("日志", check_logs),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n📋 检查{name}...")
        if check_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 检查完成: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 所有检查都通过！项目状态良好。")
        print("\n🚀 您可以通过以下方式访问项目:")
        print("   - 本地访问: http://localhost:8000")
        print("   - 网络访问: http://0.0.0.0:8000")
    else:
        print("⚠️  有些检查未通过，请查看上面的详细信息。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 