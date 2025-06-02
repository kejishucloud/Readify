#!/usr/bin/env python
"""
批量上传功能演示脚本
"""

import os
import sys
import django
import webbrowser
import time
from pathlib import Path

# 设置Django环境
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import Book, BatchUpload

def create_demo_user():
    """创建演示用户"""
    try:
        user = User.objects.get(username='demo')
        print(f"✓ 使用现有演示用户: {user.username}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='demo',
            email='demo@example.com',
            password='demo123',
            first_name='演示',
            last_name='用户'
        )
        print(f"✓ 创建演示用户: {user.username}")
    return user

def check_test_files():
    """检查测试文件"""
    test_files_dir = Path("D:/书籍文件夹")
    if not test_files_dir.exists():
        print(f"✗ 测试文件目录不存在: {test_files_dir}")
        print("请先创建测试文件目录并添加一些书籍文件")
        return False
    
    test_files = list(test_files_dir.glob("*.txt"))
    if not test_files:
        print(f"✗ 测试文件目录中没有找到TXT文件: {test_files_dir}")
        print("请在目录中添加一些TXT格式的书籍文件")
        return False
    
    print(f"✓ 找到 {len(test_files)} 个测试文件:")
    for file in test_files:
        print(f"  - {file.name} ({file.stat().st_size} bytes)")
    
    return True

def show_existing_uploads():
    """显示现有的批量上传记录"""
    uploads = BatchUpload.objects.all().order_by('-created_at')[:5]
    if uploads:
        print("\n最近的批量上传记录:")
        for upload in uploads:
            print(f"  - {upload.upload_name} ({upload.get_status_display()})")
            print(f"    时间: {upload.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    文件: {upload.successful_files}/{upload.total_files} 成功")
    else:
        print("\n暂无批量上传记录")

def show_books_count():
    """显示书籍统计"""
    total_books = Book.objects.count()
    recent_books = Book.objects.filter().order_by('-uploaded_at')[:5]
    
    print(f"\n当前书库统计:")
    print(f"  总书籍数: {total_books}")
    
    if recent_books:
        print("  最近上传的书籍:")
        for book in recent_books:
            print(f"    - {book.title} ({book.get_format_display()}) - {book.user.username}")

def main():
    """主函数"""
    print("=" * 60)
    print("Readify 批量上传功能演示")
    print("=" * 60)
    
    # 创建演示用户
    user = create_demo_user()
    
    # 检查测试文件
    if not check_test_files():
        return
    
    # 显示现有数据
    show_existing_uploads()
    show_books_count()
    
    print("\n" + "=" * 60)
    print("批量上传功能特性:")
    print("=" * 60)
    print("✓ 支持多种格式: PDF、EPUB、MOBI、TXT、DOC、DOCX")
    print("✓ 拖拽上传: 直接拖拽文件到上传区域")
    print("✓ 实时进度: 每个文件独立的进度条显示")
    print("✓ 状态跟踪: 上传、处理、成功、失败状态实时更新")
    print("✓ AI处理: 自动内容提取和智能分类")
    print("✓ 错误处理: 详细的错误信息和重试机制")
    print("✓ 批次管理: 支持批次命名和状态查看")
    
    print("\n" + "=" * 60)
    print("使用步骤:")
    print("=" * 60)
    print("1. 访问批量上传页面")
    print("2. 设置批次名称（可选）")
    print("3. 选择或拖拽多个书籍文件")
    print("4. 配置上传选项（AI分类、内容提取）")
    print("5. 点击开始上传")
    print("6. 观察实时进度和状态更新")
    print("7. 查看上传结果和书籍列表")
    
    print("\n" + "=" * 60)
    print("演示环境信息:")
    print("=" * 60)
    print(f"服务器地址: http://localhost:8000")
    print(f"批量上传页面: http://localhost:8000/books/batch-upload/")
    print(f"书籍列表页面: http://localhost:8000/books/")
    print(f"演示用户: demo / demo123")
    print(f"测试文件目录: D:/书籍文件夹")
    
    # 询问是否打开浏览器
    try:
        choice = input("\n是否打开浏览器进行演示？(y/n): ").lower().strip()
        if choice in ['y', 'yes', '是']:
            print("正在打开浏览器...")
            webbrowser.open('http://localhost:8000/books/batch-upload/')
            time.sleep(2)
            print("请在浏览器中:")
            print("1. 使用用户名 'demo' 和密码 'demo123' 登录")
            print("2. 选择D:/书籍文件夹中的文件进行批量上传")
            print("3. 观察进度条和状态更新")
    except KeyboardInterrupt:
        print("\n演示结束")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

if __name__ == '__main__':
    main() 