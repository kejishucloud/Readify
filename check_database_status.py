#!/usr/bin/env python
"""
检查数据库状态脚本
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import Book, BatchUpload, BookContent

def check_database_status():
    """检查数据库状态"""
    print("=== 数据库状态检查 ===")
    
    # 检查用户
    users = User.objects.all()
    print(f"用户总数: {users.count()}")
    
    # 检查书籍
    books = Book.objects.all()
    print(f"书籍总数: {books.count()}")
    
    # 检查批量上传记录
    batch_uploads = BatchUpload.objects.all()
    print(f"批量上传记录总数: {batch_uploads.count()}")
    
    # 检查书籍内容
    book_contents = BookContent.objects.all()
    print(f"书籍内容记录总数: {book_contents.count()}")
    
    print("\n=== 用户详情 ===")
    for user in users:
        user_books = Book.objects.filter(user=user)
        user_batches = BatchUpload.objects.filter(user=user)
        print(f"用户: {user.username}")
        print(f"  - 书籍数量: {user_books.count()}")
        print(f"  - 批量上传记录: {user_batches.count()}")
        
        # 显示最近的书籍
        recent_books = user_books.order_by('-uploaded_at')[:3]
        if recent_books:
            print("  - 最近的书籍:")
            for book in recent_books:
                content_count = BookContent.objects.filter(book=book).count()
                print(f"    * {book.title} (ID: {book.id}, 状态: {book.processing_status}, 内容章节: {content_count})")
        
        # 显示最近的批量上传
        recent_batches = user_batches.order_by('-created_at')[:3]
        if recent_batches:
            print("  - 最近的批量上传:")
            for batch in recent_batches:
                print(f"    * {batch.upload_name} (ID: {batch.id}, 状态: {batch.status}, 成功: {batch.successful_files}/{batch.total_files})")
        print()

def check_specific_user(username):
    """检查特定用户的数据"""
    try:
        user = User.objects.get(username=username)
        print(f"\n=== 用户 {username} 详细信息 ===")
        
        books = Book.objects.filter(user=user).order_by('-uploaded_at')
        print(f"书籍总数: {books.count()}")
        
        for book in books:
            content_count = BookContent.objects.filter(book=book).count()
            print(f"- {book.title}")
            print(f"  ID: {book.id}")
            print(f"  状态: {book.processing_status}")
            print(f"  上传时间: {book.uploaded_at}")
            print(f"  内容章节数: {content_count}")
            print(f"  字数: {book.word_count}")
            print()
            
    except User.DoesNotExist:
        print(f"用户 {username} 不存在")

if __name__ == "__main__":
    check_database_status()
    
    # 如果有test_user，检查详细信息
    if User.objects.filter(username='test_user').exists():
        check_specific_user('test_user') 