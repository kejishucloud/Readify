#!/usr/bin/env python
"""
测试批量上传功能和进度条
"""

import os
import sys
import django
import requests
import time
import json
from pathlib import Path

# 设置Django环境
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from readify.books.models import Book, BatchUpload

def test_batch_upload_with_progress():
    """测试批量上传功能和进度显示"""
    print("=" * 60)
    print("测试批量上传功能和进度条")
    print("=" * 60)
    
    # 创建测试用户
    try:
        user = User.objects.get(username='testuser')
        print(f"✓ 使用现有测试用户: {user.username}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        print(f"✓ 创建测试用户: {user.username}")
    
    # 创建测试客户端
    client = Client()
    
    # 登录
    login_success = client.login(username='testuser', password='testpass123')
    if not login_success:
        print("✗ 登录失败")
        return False
    print("✓ 用户登录成功")
    
    # 检查测试文件
    test_files_dir = Path("D:/书籍文件夹")
    if not test_files_dir.exists():
        print(f"✗ 测试文件目录不存在: {test_files_dir}")
        return False
    
    test_files = list(test_files_dir.glob("*.txt"))
    if not test_files:
        print(f"✗ 测试文件目录中没有找到TXT文件: {test_files_dir}")
        return False
    
    print(f"✓ 找到 {len(test_files)} 个测试文件:")
    for file in test_files:
        print(f"  - {file.name} ({file.stat().st_size} bytes)")
    
    # 准备上传数据
    files_data = {}
    for i, file_path in enumerate(test_files):
        with open(file_path, 'rb') as f:
            files_data[f'files'] = (file_path.name, f.read(), 'text/plain')
    
    # 执行批量上传
    print("\n开始批量上传...")
    upload_data = {
        'batch_name': '测试批量上传_进度条',
        'auto_classify': True,
        'extract_content': True,
    }
    
    # 使用multipart/form-data格式上传
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    uploaded_files = []
    for file_path in test_files:
        with open(file_path, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                name=file_path.name,
                content=f.read(),
                content_type='text/plain'
            )
            uploaded_files.append(uploaded_file)
    
    # 构建POST数据
    post_data = upload_data.copy()
    post_data['files'] = uploaded_files
    
    response = client.post(
        reverse('batch_upload'),
        data=post_data,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        HTTP_ACCEPT='application/json'
    )
    
    if response.status_code != 200:
        print(f"✗ 上传请求失败: {response.status_code}")
        print(f"响应内容: {response.content.decode()}")
        return False
    
    try:
        response_data = response.json()
    except json.JSONDecodeError:
        print(f"✗ 响应不是有效的JSON: {response.content.decode()}")
        return False
    
    if not response_data.get('success'):
        print(f"✗ 上传失败: {response_data.get('error', '未知错误')}")
        return False
    
    batch_id = response_data.get('batch_id')
    print(f"✓ 批量上传开始成功，批次ID: {batch_id}")
    
    # 监控上传进度
    print("\n监控上传进度...")
    max_attempts = 30  # 最多等待30次，每次2秒
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        time.sleep(2)  # 等待2秒
        
        # 获取进度
        progress_response = client.get(
            reverse('get_batch_upload_progress', kwargs={'batch_id': batch_id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        if progress_response.status_code != 200:
            print(f"✗ 获取进度失败: {progress_response.status_code}")
            continue
        
        try:
            progress_data = progress_response.json()
        except json.JSONDecodeError:
            print(f"✗ 进度响应不是有效的JSON")
            continue
        
        if not progress_data.get('success'):
            print(f"✗ 获取进度失败: {progress_data.get('error')}")
            continue
        
        batch_info = progress_data.get('batch_upload', {})
        files_info = progress_data.get('files', [])
        
        print(f"\n--- 进度更新 (第{attempt}次) ---")
        print(f"批次状态: {batch_info.get('status')}")
        print(f"总体进度: {batch_info.get('processed_files')}/{batch_info.get('total_files')} ({batch_info.get('progress_percentage', 0):.1f}%)")
        print(f"成功: {batch_info.get('successful_files')}, 失败: {batch_info.get('failed_files')}")
        
        print("\n文件详细进度:")
        for file_info in files_info:
            filename = file_info.get('filename', 'Unknown')
            progress = file_info.get('progress', 0)
            status = file_info.get('status', 'unknown')
            message = file_info.get('message', '')
            print(f"  {filename}: {progress}% [{status}] {message}")
        
        # 检查是否完成
        if batch_info.get('status') in ['completed', 'failed', 'partial']:
            print(f"\n✓ 批量上传完成，最终状态: {batch_info.get('status')}")
            break
    else:
        print(f"\n⚠ 达到最大等待时间，停止监控")
    
    # 验证结果
    print("\n验证上传结果...")
    try:
        batch_upload = BatchUpload.objects.get(id=batch_id)
        print(f"✓ 批量上传记录: {batch_upload.upload_name}")
        print(f"  状态: {batch_upload.get_status_display()}")
        print(f"  总文件数: {batch_upload.total_files}")
        print(f"  成功: {batch_upload.successful_files}")
        print(f"  失败: {batch_upload.failed_files}")
        
        if batch_upload.error_log:
            print(f"  错误日志: {batch_upload.error_log}")
        
        # 检查创建的书籍
        books = Book.objects.filter(user=user, uploaded_at__gte=batch_upload.created_at)
        print(f"✓ 创建的书籍数量: {books.count()}")
        
        for book in books:
            print(f"  - {book.title} ({book.get_format_display()}) - {book.get_processing_status_display()}")
            if book.word_count > 0:
                print(f"    字数: {book.word_count:,}")
        
        return True
        
    except BatchUpload.DoesNotExist:
        print(f"✗ 找不到批量上传记录: {batch_id}")
        return False

def test_web_interface():
    """测试Web界面访问"""
    print("\n" + "=" * 60)
    print("测试Web界面访问")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # 测试批量上传页面
    try:
        response = requests.get(f"{base_url}/books/batch-upload/", timeout=5)
        if response.status_code == 200:
            print("✓ 批量上传页面可访问")
            if "批量上传书籍" in response.text:
                print("✓ 页面内容正确")
            else:
                print("⚠ 页面内容可能有问题")
        else:
            print(f"✗ 批量上传页面访问失败: {response.status_code}")
    except requests.RequestException as e:
        print(f"✗ 无法访问批量上传页面: {e}")
    
    # 测试书籍列表页面
    try:
        response = requests.get(f"{base_url}/books/", timeout=5)
        if response.status_code == 200:
            print("✓ 书籍列表页面可访问")
        else:
            print(f"✗ 书籍列表页面访问失败: {response.status_code}")
    except requests.RequestException as e:
        print(f"✗ 无法访问书籍列表页面: {e}")

def main():
    """主函数"""
    print("开始测试批量上传功能和进度条...")
    
    # 测试Web界面
    test_web_interface()
    
    # 测试批量上传功能
    success = test_batch_upload_with_progress()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n使用说明:")
        print("1. 访问 http://localhost:8000/books/batch-upload/ 进行批量上传")
        print("2. 选择D:/书籍文件夹中的文件进行测试")
        print("3. 观察实时进度条和状态更新")
        print("4. 查看 http://localhost:8000/books/ 确认上传的书籍")
    else:
        print("\n" + "=" * 60)
        print("✗ 测试失败，请检查错误信息")
        print("=" * 60)

if __name__ == '__main__':
    main() 