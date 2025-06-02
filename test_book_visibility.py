#!/usr/bin/env python
"""
测试书籍在Web界面的可见性
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from readify.books.models import Book, BookCategory

def test_book_list_visibility():
    """测试书籍列表页面的可见性"""
    print("=== 测试书籍列表页面可见性 ===")
    
    # 测试不同用户的书籍列表
    users = ['test_user', 'kejishu', 'kejishucloud']
    
    for username in users:
        try:
            user = User.objects.get(username=username)
            print(f"\n--- 测试用户: {username} ---")
            
            # 创建测试客户端
            client = Client()
            client.force_login(user)
            
            # 访问书籍列表页面
            response = client.get('/books/')
            print(f"书籍列表页面状态码: {response.status_code}")
            
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # 检查页面是否包含书籍信息
                user_books = Book.objects.filter(user=user)
                print(f"数据库中的书籍数量: {user_books.count()}")
                
                # 检查页面内容
                if user_books.exists():
                    found_books = 0
                    for book in user_books[:5]:  # 检查前5本书
                        if book.title in content:
                            found_books += 1
                            print(f"✅ 找到书籍: {book.title}")
                        else:
                            print(f"❌ 未找到书籍: {book.title}")
                    
                    print(f"页面中找到的书籍数量: {found_books}/{min(5, user_books.count())}")
                    
                    # 检查是否有"暂无书籍"的提示
                    if "暂无书籍" in content or "没有书籍" in content:
                        print("⚠️ 页面显示'暂无书籍'提示")
                    
                else:
                    print("数据库中没有书籍")
                    
            else:
                print(f"❌ 页面访问失败，状态码: {response.status_code}")
                
        except User.DoesNotExist:
            print(f"用户 {username} 不存在")

def test_category_browsing():
    """测试分类浏览功能"""
    print("\n=== 测试分类浏览功能 ===")
    
    try:
        user = User.objects.get(username='test_user')
        client = Client()
        client.force_login(user)
        
        # 访问分类列表页面
        response = client.get('/categories/')
        print(f"分类列表页面状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 分类列表页面访问成功")
            
            # 检查是否有分类
            categories = BookCategory.objects.all()
            print(f"数据库中的分类数量: {categories.count()}")
            
            # 测试访问特定分类的书籍
            if categories.exists():
                category = categories.first()
                category_response = client.get(f'/categories/{category.code}/')
                print(f"分类 '{category.name}' 页面状态码: {category_response.status_code}")
                
                if category_response.status_code == 200:
                    print(f"✅ 分类 '{category.name}' 页面访问成功")
                else:
                    print(f"❌ 分类 '{category.name}' 页面访问失败")
        else:
            print(f"❌ 分类列表页面访问失败，状态码: {response.status_code}")
            
    except User.DoesNotExist:
        print("测试用户不存在")

def test_search_functionality():
    """测试搜索功能"""
    print("\n=== 测试搜索功能 ===")
    
    try:
        user = User.objects.get(username='test_user')
        client = Client()
        client.force_login(user)
        
        # 获取用户的一本书进行搜索测试
        user_books = Book.objects.filter(user=user)
        if user_books.exists():
            test_book = user_books.first()
            search_term = test_book.title[:3]  # 使用书名的前3个字符
            
            response = client.get(f'/books/?search={search_term}')
            print(f"搜索 '{search_term}' 的结果页面状态码: {response.status_code}")
            
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                if test_book.title in content:
                    print(f"✅ 搜索成功找到书籍: {test_book.title}")
                else:
                    print(f"❌ 搜索未找到书籍: {test_book.title}")
            else:
                print(f"❌ 搜索页面访问失败")
        else:
            print("用户没有书籍，无法测试搜索功能")
            
    except User.DoesNotExist:
        print("测试用户不存在")

def test_book_detail_access():
    """测试书籍详情页面访问"""
    print("\n=== 测试书籍详情页面访问 ===")
    
    try:
        user = User.objects.get(username='test_user')
        client = Client()
        client.force_login(user)
        
        user_books = Book.objects.filter(user=user)[:3]  # 测试前3本书
        
        for book in user_books:
            response = client.get(f'/books/{book.id}/')
            print(f"书籍 '{book.title}' 详情页面状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ 书籍 '{book.title}' 详情页面访问成功")
            else:
                print(f"❌ 书籍 '{book.title}' 详情页面访问失败")
                
    except User.DoesNotExist:
        print("测试用户不存在")

if __name__ == "__main__":
    test_book_list_visibility()
    test_category_browsing()
    test_search_functionality()
    test_book_detail_access() 