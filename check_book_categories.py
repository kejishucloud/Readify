#!/usr/bin/env python
"""
检查书籍分类情况
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import Book, BookCategory

def check_book_categories():
    """检查书籍分类情况"""
    print("=== 检查书籍分类情况 ===")
    
    # 检查所有分类
    categories = BookCategory.objects.all()
    print(f"数据库中的分类总数: {categories.count()}")
    
    print("\n所有分类:")
    for category in categories:
        book_count = Book.objects.filter(category=category).count()
        print(f"  - {category.name} (code: {category.code}): {book_count} 本书籍")
    
    # 检查未分类的书籍
    uncategorized_books = Book.objects.filter(category__isnull=True)
    print(f"\n未分类书籍总数: {uncategorized_books.count()}")
    
    # 按用户分组显示未分类书籍
    users_with_uncategorized = {}
    for book in uncategorized_books:
        username = book.user.username
        if username not in users_with_uncategorized:
            users_with_uncategorized[username] = []
        users_with_uncategorized[username].append(book)
    
    print("\n按用户分组的未分类书籍:")
    for username, books in users_with_uncategorized.items():
        print(f"  用户 {username}: {len(books)} 本未分类书籍")
        for book in books[:3]:  # 显示前3本
            print(f"    - {book.title} (ID: {book.id}, 状态: {book.processing_status})")
    
    # 检查最近的书籍分类情况
    print("\n=== 最近20本书籍的分类情况 ===")
    recent_books = Book.objects.all().order_by('-uploaded_at')[:20]
    
    for book in recent_books:
        category_name = book.category.name if book.category else "未分类"
        print(f"- {book.title[:30]}... -> {category_name} (状态: {book.processing_status})")

def test_ai_classification():
    """测试AI分类功能"""
    print("\n=== 测试AI分类功能 ===")
    
    # 选择一本未分类的书籍进行测试
    uncategorized_book = Book.objects.filter(category__isnull=True).first()
    
    if not uncategorized_book:
        print("没有未分类的书籍可供测试")
        return
    
    print(f"测试书籍: {uncategorized_book.title} (ID: {uncategorized_book.id})")
    print(f"用户: {uncategorized_book.user.username}")
    print(f"当前状态: {uncategorized_book.processing_status}")
    
    # 尝试手动触发AI分类
    try:
        from readify.books.services import BookProcessingService
        
        processing_service = BookProcessingService(uncategorized_book.user)
        result = processing_service.classify_book_with_ai(uncategorized_book)
        
        print(f"AI分类结果: {result}")
        
        # 重新获取书籍信息
        uncategorized_book.refresh_from_db()
        if uncategorized_book.category:
            print(f"✅ 分类成功: {uncategorized_book.category.name}")
        else:
            print("❌ 分类失败，仍然未分类")
            
    except Exception as e:
        print(f"AI分类测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def check_ai_service_availability():
    """检查AI服务可用性"""
    print("\n=== 检查AI服务可用性 ===")
    
    try:
        from readify.ai_services.services import AIService
        
        # 创建一个测试用户
        test_user = User.objects.filter(username='test_user').first()
        if not test_user:
            print("测试用户不存在")
            return
        
        ai_service = AIService(user=test_user)
        
        # 测试简单的AI请求
        messages = [{"role": "user", "content": "这是一个测试消息，请回复'测试成功'"}]
        result = ai_service._make_api_request(messages, "你是一个测试助手")
        
        if result['success']:
            print("✅ AI服务可用")
            print(f"AI响应: {result['content']}")
        else:
            print("❌ AI服务不可用")
            print(f"错误: {result.get('error', '未知错误')}")
            
    except ImportError as e:
        print(f"❌ AI服务模块导入失败: {str(e)}")
    except Exception as e:
        print(f"❌ AI服务测试失败: {str(e)}")

if __name__ == "__main__":
    check_book_categories()
    test_ai_classification()
    check_ai_service_availability() 