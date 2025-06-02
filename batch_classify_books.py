#!/usr/bin/env python
"""
批量分类所有未分类的书籍
"""

import os
import sys
import django
import time

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import Book, BookCategory
from readify.books.services import BookProcessingService

def batch_classify_books(max_books=20, delay_seconds=2):
    """批量分类未分类的书籍"""
    print("=== 批量分类未分类书籍 ===")
    
    # 获取所有未分类的书籍
    uncategorized_books = Book.objects.filter(category__isnull=True)[:max_books]
    
    print(f"找到 {uncategorized_books.count()} 本未分类书籍（处理前{max_books}本）")
    
    if not uncategorized_books.exists():
        print("没有未分类的书籍需要处理")
        return
    
    success_count = 0
    failed_count = 0
    
    for i, book in enumerate(uncategorized_books, 1):
        print(f"\n[{i}/{len(uncategorized_books)}] 处理书籍: {book.title}")
        print(f"  用户: {book.user.username}")
        print(f"  ID: {book.id}")
        
        try:
            # 创建处理服务
            processing_service = BookProcessingService(book.user)
            
            # 执行AI分类
            result = processing_service.classify_book_with_ai(book)
            
            if result['success']:
                # 重新获取书籍信息
                book.refresh_from_db()
                if book.category:
                    print(f"  ✅ 分类成功: {book.category.name}")
                    print(f"  置信度: {result.get('confidence', 'N/A')}")
                    success_count += 1
                else:
                    print(f"  ❌ 分类失败: 未设置分类")
                    failed_count += 1
            else:
                print(f"  ❌ 分类失败: {result.get('error', '未知错误')}")
                failed_count += 1
                
        except Exception as e:
            print(f"  ❌ 处理异常: {str(e)}")
            failed_count += 1
        
        # 添加延迟，避免API请求过于频繁
        if i < len(uncategorized_books):
            print(f"  等待 {delay_seconds} 秒...")
            time.sleep(delay_seconds)
    
    print(f"\n=== 批量分类完成 ===")
    print(f"成功分类: {success_count} 本")
    print(f"分类失败: {failed_count} 本")
    print(f"总计处理: {success_count + failed_count} 本")

def show_classification_summary():
    """显示分类统计摘要"""
    print("\n=== 分类统计摘要 ===")
    
    # 统计各分类的书籍数量
    categories = BookCategory.objects.all()
    
    for category in categories:
        book_count = Book.objects.filter(category=category).count()
        if book_count > 0:
            print(f"  - {category.name}: {book_count} 本书籍")
    
    # 统计未分类书籍
    uncategorized_count = Book.objects.filter(category__isnull=True).count()
    print(f"  - 未分类: {uncategorized_count} 本书籍")
    
    # 总计
    total_books = Book.objects.count()
    categorized_books = total_books - uncategorized_count
    print(f"\n总计: {total_books} 本书籍")
    print(f"已分类: {categorized_books} 本 ({categorized_books/total_books*100:.1f}%)")
    print(f"未分类: {uncategorized_count} 本 ({uncategorized_count/total_books*100:.1f}%)")

def classify_specific_user_books(username, max_books=10):
    """分类特定用户的书籍"""
    print(f"\n=== 分类用户 {username} 的书籍 ===")
    
    try:
        user = User.objects.get(username=username)
        uncategorized_books = Book.objects.filter(
            user=user, 
            category__isnull=True
        )[:max_books]
        
        print(f"用户 {username} 有 {uncategorized_books.count()} 本未分类书籍")
        
        if not uncategorized_books.exists():
            print("该用户没有未分类的书籍")
            return
        
        processing_service = BookProcessingService(user)
        success_count = 0
        
        for i, book in enumerate(uncategorized_books, 1):
            print(f"\n[{i}/{len(uncategorized_books)}] 处理: {book.title}")
            
            try:
                result = processing_service.classify_book_with_ai(book)
                
                if result['success']:
                    book.refresh_from_db()
                    if book.category:
                        print(f"  ✅ 分类为: {book.category.name}")
                        success_count += 1
                    else:
                        print(f"  ❌ 分类失败")
                else:
                    print(f"  ❌ 分类失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"  ❌ 处理异常: {str(e)}")
            
            # 添加延迟
            if i < len(uncategorized_books):
                time.sleep(1)
        
        print(f"\n用户 {username} 分类完成: {success_count}/{len(uncategorized_books)} 本成功")
        
    except User.DoesNotExist:
        print(f"用户 {username} 不存在")

if __name__ == "__main__":
    # 显示当前状态
    show_classification_summary()
    
    # 询问用户要执行的操作
    print("\n请选择操作:")
    print("1. 批量分类所有用户的书籍（前20本）")
    print("2. 分类特定用户的书籍")
    print("3. 只显示统计信息")
    
    choice = input("请输入选择 (1/2/3): ").strip()
    
    if choice == "1":
        batch_classify_books(max_books=20, delay_seconds=2)
        show_classification_summary()
    elif choice == "2":
        username = input("请输入用户名: ").strip()
        if username:
            classify_specific_user_books(username, max_books=10)
        else:
            print("用户名不能为空")
    elif choice == "3":
        print("仅显示统计信息")
    else:
        print("无效选择")
    
    print("\n脚本执行完成") 