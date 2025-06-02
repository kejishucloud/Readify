#!/usr/bin/env python
"""
测试批量上传状态页面的问题
"""
import os
import sys
import django
import requests
from datetime import datetime

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import BatchUpload, Book

def test_status_page():
    """测试状态页面访问"""
    print("=== 批量上传状态页面测试 ===")
    
    # 1. 检查是否有批量上传记录
    print("\n1. 检查批量上传记录...")
    batch_uploads = BatchUpload.objects.all().order_by('-created_at')
    print(f"找到 {batch_uploads.count()} 个批量上传记录")
    
    if batch_uploads.exists():
        for batch in batch_uploads[:3]:  # 显示最近3个
            print(f"  - ID: {batch.id}, 名称: {batch.upload_name}, 状态: {batch.status}")
            print(f"    创建时间: {batch.created_at}")
            print(f"    文件数: {batch.total_files}, 成功: {batch.successful_files}, 失败: {batch.failed_files}")
    
    # 2. 测试状态页面URL
    print("\n2. 测试状态页面URL...")
    if batch_uploads.exists():
        latest_batch = batch_uploads.first()
        status_url = f"http://127.0.0.1:8000/books/batch-upload/{latest_batch.id}/status/"
        print(f"测试URL: {status_url}")
        
        try:
            # 创建一个会话来模拟登录
            session = requests.Session()
            
            # 首先获取登录页面的CSRF token
            login_page = session.get('http://127.0.0.1:8000/auth/login/')
            if login_page.status_code == 200:
                print("✅ 登录页面可访问")
                
                # 尝试直接访问状态页面（可能会重定向到登录）
                response = session.get(status_url)
                print(f"状态页面响应码: {response.status_code}")
                print(f"最终URL: {response.url}")
                
                if response.status_code == 404:
                    print("❌ 状态页面返回404错误")
                elif response.status_code == 302:
                    print("⚠️ 状态页面重定向（可能需要登录）")
                elif response.status_code == 200:
                    print("✅ 状态页面可访问")
                else:
                    print(f"⚠️ 状态页面返回状态码: {response.status_code}")
            else:
                print(f"❌ 无法访问登录页面，状态码: {login_page.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到服务器，请确保Django服务器正在运行")
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")
    else:
        print("⚠️ 没有批量上传记录可测试")
    
    # 3. 检查相关书籍
    print("\n3. 检查相关书籍...")
    if batch_uploads.exists():
        latest_batch = batch_uploads.first()
        
        # 获取与此批量上传相关的书籍
        from datetime import timedelta
        from django.utils import timezone
        
        time_buffer = timedelta(minutes=5)
        start_time = latest_batch.created_at - time_buffer
        end_time = latest_batch.completed_at + time_buffer if latest_batch.completed_at else timezone.now() + time_buffer
        
        books = Book.objects.filter(
            user=latest_batch.user,
            uploaded_at__gte=start_time,
            uploaded_at__lte=end_time
        ).order_by('-uploaded_at')
        
        print(f"找到 {books.count()} 本相关书籍")
        for book in books:
            print(f"  - {book.title} (上传时间: {book.uploaded_at})")
    
    # 4. 检查URL路由配置
    print("\n4. 检查URL路由配置...")
    from django.urls import reverse
    try:
        if batch_uploads.exists():
            latest_batch = batch_uploads.first()
            url = reverse('batch_upload_status', kwargs={'batch_id': latest_batch.id})
            print(f"✅ URL路由正常: {url}")
        else:
            # 测试一个假的ID
            url = reverse('batch_upload_status', kwargs={'batch_id': 1})
            print(f"✅ URL路由配置正常: {url}")
    except Exception as e:
        print(f"❌ URL路由配置错误: {str(e)}")

def test_book_list_display():
    """测试书籍列表显示问题"""
    print("\n=== 书籍列表显示测试 ===")
    
    # 1. 检查所有用户的书籍
    print("\n1. 检查所有书籍...")
    all_books = Book.objects.all().order_by('-uploaded_at')
    print(f"数据库中总共有 {all_books.count()} 本书籍")
    
    if all_books.exists():
        print("最近的书籍:")
        for book in all_books[:5]:
            print(f"  - {book.title} (用户: {book.user.username}, 上传时间: {book.uploaded_at})")
    
    # 2. 检查每个用户的书籍
    print("\n2. 按用户检查书籍...")
    users = User.objects.all()
    for user in users:
        user_books = Book.objects.filter(user=user)
        print(f"用户 {user.username}: {user_books.count()} 本书籍")
        if user_books.exists():
            for book in user_books[:3]:
                print(f"  - {book.title}")
    
    # 3. 测试书籍列表页面
    print("\n3. 测试书籍列表页面...")
    try:
        session = requests.Session()
        response = session.get('http://127.0.0.1:8000/books/')
        print(f"书籍列表页面响应码: {response.status_code}")
        
        if response.status_code == 302:
            print("⚠️ 书籍列表页面重定向（可能需要登录）")
        elif response.status_code == 200:
            print("✅ 书籍列表页面可访问")
        else:
            print(f"⚠️ 书籍列表页面返回状态码: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")

if __name__ == '__main__':
    test_status_page()
    test_book_list_display() 