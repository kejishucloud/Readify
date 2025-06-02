#!/usr/bin/env python
"""
创建或检查test_user用户
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User

def create_test_user():
    """创建测试用户"""
    username = 'test_user'
    password = 'testpass123'
    email = 'test@example.com'
    
    # 检查用户是否已存在
    try:
        user = User.objects.get(username=username)
        print(f"✅ 用户 {username} 已存在")
        
        # 检查密码是否正确
        if user.check_password(password):
            print("✅ 密码正确")
        else:
            print("⚠️ 密码不正确，重置密码...")
            user.set_password(password)
            user.save()
            print("✅ 密码已重置")
            
    except User.DoesNotExist:
        print(f"用户 {username} 不存在，正在创建...")
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        print(f"✅ 用户 {username} 创建成功")
    
    return user

def list_all_users():
    """列出所有用户"""
    print("\n=== 所有用户列表 ===")
    users = User.objects.all()
    for user in users:
        print(f"- {user.username} (邮箱: {user.email}, 活跃: {user.is_active})")

if __name__ == '__main__':
    create_test_user()
    list_all_users() 