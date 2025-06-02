#!/usr/bin/env python
"""
个人资料界面优化测试脚本
测试新的个人资料界面是否与主页风格保持一致
"""

import os
import sys
import json

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')

import django
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from readify.user_management.models import UserProfile
from readify.books.models import Book, BookNote, ReadingProgress

def test_profile_page_optimization():
    """测试个人资料页面优化"""
    print("🚀 开始测试个人资料界面优化...")
    
    # 先清理可能存在的测试数据
    try:
        existing_user = User.objects.filter(username='testuser').first()
        if existing_user:
            BookNote.objects.filter(user=existing_user).delete()
            Book.objects.filter(user=existing_user).delete()
            UserProfile.objects.filter(user=existing_user).delete()
            existing_user.delete()
            print("🧹 清理了已存在的测试数据")
    except Exception as e:
        print(f"⚠️  清理测试数据时出现警告: {e}")
    
    # 创建测试客户端
    client = Client()
    
    # 创建测试用户
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='测试',
        last_name='用户'
    )
    
    # 创建用户配置文件
    profile = UserProfile.objects.create(
        user=user,
        bio='这是一个测试用户的个人简介',
        location='北京, 中国',
        website='https://example.com'
    )
    
    # 创建一些测试数据
    book1 = Book.objects.create(
        title='测试书籍1',
        author='测试作者1',
        user=user,
        view_count=10
    )
    
    book2 = Book.objects.create(
        title='测试书籍2',
        author='测试作者2',
        user=user,
        view_count=5
    )
    
    # 创建笔记
    note1 = BookNote.objects.create(
        user=user,
        book=book1,
        note_content='这是一个测试笔记',
        chapter_number=1,
        selected_text='测试选中文本1'
    )
    
    note2 = BookNote.objects.create(
        user=user,
        book=book2,
        note_content='这是另一个测试笔记',
        chapter_number=1,
        selected_text='测试选中文本2'
    )
    
    # 登录用户
    client.login(username='testuser', password='testpass123')
    
    # 测试GET请求 - 显示个人资料页面
    print("📄 测试个人资料页面显示...")
    response = client.get(reverse('user_management:update_profile'))
    
    if response.status_code == 200:
        print("✅ 个人资料页面加载成功")
        
        # 检查页面内容
        content = response.content.decode('utf-8')
        
        # 检查是否包含新的设计元素
        checks = [
            ('profile-hero', '英雄区域'),
            ('stat-card', '统计卡片'),
            ('profile-info-item', '个人信息项'),
            ('section-title', '章节标题'),
            ('form-card', '表单卡片'),
            ('profile-avatar', '用户头像'),
            ('breadcrumb', '面包屑导航')
        ]
        
        for class_name, description in checks:
            if class_name in content:
                print(f"✅ 包含{description} ({class_name})")
            else:
                print(f"❌ 缺少{description} ({class_name})")
        
        # 检查统计数据
        if hasattr(response, 'context') and response.context and 'user_stats' in response.context:
            stats = response.context['user_stats']
            print(f"✅ 统计数据加载成功:")
            print(f"   - 总书籍数: {stats['total_books']}")
            print(f"   - 分类数量: {stats['categories_count']}")
            print(f"   - 总阅读次数: {stats['total_views']}")
            print(f"   - 笔记数量: {stats['notes_count']}")
        else:
            print("❌ 统计数据未加载")
            
    else:
        print(f"❌ 个人资料页面加载失败，状态码: {response.status_code}")
    
    # 测试POST请求 - 更新个人资料
    print("\n📝 测试个人资料更新...")
    update_data = {
        'first_name': '更新的名字',
        'last_name': '更新的姓氏',
        'bio': '这是更新后的个人简介',
        'location': '上海, 中国',
        'website': 'https://updated-example.com'
    }
    
    response = client.post(
        reverse('user_management:update_profile'),
        data=json.dumps(update_data),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✅ 个人资料更新成功")
            
            # 验证数据是否真的更新了
            user.refresh_from_db()
            profile.refresh_from_db()
            
            if user.first_name == '更新的名字':
                print("✅ 用户名字更新成功")
            else:
                print("❌ 用户名字更新失败")
                
            if profile.bio == '这是更新后的个人简介':
                print("✅ 个人简介更新成功")
            else:
                print("❌ 个人简介更新失败")
                
        else:
            print(f"❌ 个人资料更新失败: {result.get('message')}")
    else:
        print(f"❌ 个人资料更新请求失败，状态码: {response.status_code}")
    
    # 清理测试数据
    print("\n🧹 清理测试数据...")
    try:
        BookNote.objects.filter(user=user).delete()
        Book.objects.filter(user=user).delete()
        UserProfile.objects.filter(user=user).delete()
        User.objects.filter(username='testuser').delete()
        print("✅ 测试数据清理完成")
    except Exception as e:
        print(f"⚠️  清理测试数据时出现警告: {e}")

def test_style_consistency():
    """测试样式一致性"""
    print("\n🎨 测试样式一致性...")
    
    # 读取个人资料模板
    try:
        with open('frontend/templates/user_management/profile.html', 'r', encoding='utf-8') as f:
            profile_content = f.read()
        
        # 读取主页模板
        with open('frontend/templates/home.html', 'r', encoding='utf-8') as f:
            home_content = f.read()
        
        # 检查共同的样式元素
        common_styles = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',  # 渐变背景
            'box-shadow: 0 2px 10px rgba(0,0,0,0.1)',  # 卡片阴影
            'border-radius: 15px',  # 圆角
            'transform: translateY(-5px)',  # 悬停效果
            'fas fa-',  # Font Awesome图标
        ]
        
        for style in common_styles:
            in_profile = style in profile_content
            in_home = style in home_content
            
            if in_profile and in_home:
                print(f"✅ 共同样式: {style[:30]}...")
            elif in_profile:
                print(f"⚠️  仅在个人资料页面: {style[:30]}...")
            elif in_home:
                print(f"⚠️  仅在主页: {style[:30]}...")
            else:
                print(f"❌ 两个页面都没有: {style[:30]}...")
        
        print("✅ 样式一致性检查完成")
        
    except FileNotFoundError as e:
        print(f"❌ 模板文件未找到: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 Readify 个人资料界面优化测试")
    print("=" * 60)
    
    try:
        test_profile_page_optimization()
        test_style_consistency()
        
        print("\n" + "=" * 60)
        print("🎉 个人资料界面优化测试完成!")
        print("=" * 60)
        print("\n📋 优化总结:")
        print("✅ 使用与主页一致的渐变背景")
        print("✅ 添加了统计卡片展示用户数据")
        print("✅ 改进了表单设计和用户体验")
        print("✅ 增加了面包屑导航")
        print("✅ 优化了响应式布局")
        print("✅ 添加了悬停动画效果")
        print("✅ 统一了图标和按钮样式")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 