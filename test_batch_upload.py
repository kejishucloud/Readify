#!/usr/bin/env python
"""
批量上传功能测试脚本
用于验证批量上传是否正常工作，以及书籍是否正确添加到用户的书籍列表中
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import Book, BookContent, BatchUpload
from readify.books.services import BookProcessingService
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile

def create_test_files():
    """创建测试文件"""
    test_files = []
    
    # 创建测试TXT文件
    txt_content = """这是一本测试书籍的内容。

第一章：开始
这是第一章的内容，包含了一些基本的介绍信息。

第二章：发展
这是第二章的内容，描述了故事的发展过程。

第三章：结束
这是第三章的内容，讲述了故事的结局。

全书完。
"""
    
    for i in range(3):
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(f"测试书籍{i+1}\n\n{txt_content}")
            
        # 读取文件内容并创建SimpleUploadedFile
        with open(f.name, 'rb') as file:
            content = file.read()
            
        uploaded_file = SimpleUploadedFile(
            name=f"测试书籍{i+1}.txt",
            content=content,
            content_type='text/plain'
        )
        test_files.append(uploaded_file)
        
        # 清理临时文件
        os.unlink(f.name)
    
    return test_files

def test_batch_upload():
    """测试批量上传功能"""
    print("开始测试批量上传功能...")
    
    # 获取或创建测试用户
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@example.com',
            'first_name': '测试',
            'last_name': '用户'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"创建了测试用户: {user.username}")
    else:
        print(f"使用现有测试用户: {user.username}")
    
    # 记录上传前的书籍数量
    books_before = Book.objects.filter(user=user).count()
    print(f"上传前用户书籍数量: {books_before}")
    
    # 创建测试文件
    test_files = create_test_files()
    print(f"创建了 {len(test_files)} 个测试文件")
    
    # 执行批量上传
    processing_service = BookProcessingService(user)
    batch_upload = processing_service.process_batch_upload(test_files, "测试批量上传")
    
    print(f"批量上传完成:")
    print(f"  批次ID: {batch_upload.id}")
    print(f"  批次名称: {batch_upload.upload_name}")
    print(f"  总文件数: {batch_upload.total_files}")
    print(f"  已处理文件数: {batch_upload.processed_files}")
    print(f"  成功文件数: {batch_upload.successful_files}")
    print(f"  失败文件数: {batch_upload.failed_files}")
    print(f"  状态: {batch_upload.status}")
    
    if batch_upload.error_log:
        print(f"  错误日志: {batch_upload.error_log}")
    
    # 检查上传后的书籍数量
    books_after = Book.objects.filter(user=user).count()
    print(f"上传后用户书籍数量: {books_after}")
    print(f"新增书籍数量: {books_after - books_before}")
    
    # 列出新增的书籍
    new_books = Book.objects.filter(user=user).order_by('-uploaded_at')[:len(test_files)]
    print("\n新增的书籍:")
    for book in new_books:
        print(f"  - ID: {book.id}, 标题: {book.title}, 用户: {book.user.username}")
        print(f"    状态: {book.processing_status}, 字数: {book.word_count}")
        
        # 检查是否有内容
        content_count = BookContent.objects.filter(book=book).count()
        print(f"    内容章节数: {content_count}")
    
    # 验证书籍是否正确关联到用户
    user_books = Book.objects.filter(user=user)
    print(f"\n用户 {user.username} 的所有书籍:")
    for book in user_books:
        print(f"  - {book.title} (ID: {book.id})")
    
    return batch_upload, new_books

def test_book_list_view():
    """测试书籍列表视图是否能正确显示书籍"""
    print("\n测试书籍列表视图...")
    
    user = User.objects.get(username='test_user')
    books = Book.objects.filter(user=user).order_by('-uploaded_at')
    
    print(f"书籍列表查询结果: {books.count()} 本书")
    for book in books:
        print(f"  - {book.title} (上传时间: {book.uploaded_at})")

def cleanup_test_data():
    """清理测试数据"""
    print("\n清理测试数据...")
    
    try:
        user = User.objects.get(username='test_user')
        
        # 删除用户的所有书籍
        books = Book.objects.filter(user=user)
        book_count = books.count()
        books.delete()
        print(f"删除了 {book_count} 本书籍")
        
        # 删除用户的批量上传记录
        batch_uploads = BatchUpload.objects.filter(user=user)
        batch_count = batch_uploads.count()
        batch_uploads.delete()
        print(f"删除了 {batch_count} 个批量上传记录")
        
        # 可选：删除测试用户
        # user.delete()
        # print(f"删除了测试用户: {user.username}")
        
    except User.DoesNotExist:
        print("测试用户不存在，无需清理")

if __name__ == "__main__":
    try:
        # 运行测试
        batch_upload, new_books = test_batch_upload()
        test_book_list_view()
        
        print("\n测试完成！")
        print("如果看到新增的书籍数量与上传的文件数量一致，说明批量上传功能正常。")
        
        # 询问是否清理测试数据
        response = input("\n是否清理测试数据？(y/n): ")
        if response.lower() == 'y':
            cleanup_test_data()
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc() 