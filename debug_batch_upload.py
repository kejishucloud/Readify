#!/usr/bin/env python
"""
调试批量上传功能的脚本
模拟Web界面的AJAX请求
"""

import os
import sys
import tempfile

# 设置Django环境 - 必须在导入Django模型之前
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')

import django
django.setup()

# 现在可以安全地导入Django模型
from django.test import Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

def create_test_file():
    """创建一个测试文件"""
    content = "这是一个测试书籍的内容。\n\n第一章：测试内容\n这是测试章节的内容。"
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    # 读取文件内容
    with open(temp_path, 'rb') as f:
        file_content = f.read()
    
    # 清理临时文件
    os.unlink(temp_path)
    
    return SimpleUploadedFile(
        name="调试测试书籍.txt",
        content=file_content,
        content_type='text/plain'
    )

def test_web_batch_upload():
    """测试Web界面的批量上传功能"""
    print("开始测试Web界面批量上传功能...")
    
    # 获取测试用户
    try:
        user = User.objects.get(username='test_user')
        print(f"使用测试用户: {user.username}")
    except User.DoesNotExist:
        print("测试用户不存在，请先运行 test_batch_upload.py")
        return
    
    # 创建Django测试客户端
    client = Client()
    
    # 登录用户
    client.force_login(user)
    print("用户已登录")
    
    # 创建测试文件
    test_file = create_test_file()
    print(f"创建测试文件: {test_file.name}")
    
    # 模拟AJAX批量上传请求
    response = client.post('/books/batch-upload/', {
        'batch_name': '调试测试批量上传',
        'auto_classify': True,
        'extract_content': True,
        'files': [test_file]
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_ACCEPT='application/json')
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容类型: {response.get('Content-Type', 'unknown')}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"JSON响应: {data}")
            
            if data.get('success'):
                print("✅ 批量上传成功！")
                batch_id = data.get('batch_id')
                print(f"批次ID: {batch_id}")
                
                # 检查状态页面
                status_response = client.get(f'/books/batch-upload/status/{batch_id}/')
                print(f"状态页面响应码: {status_response.status_code}")
                
                if status_response.status_code == 200:
                    print("✅ 状态页面访问成功！")
                else:
                    print("❌ 状态页面访问失败")
                    
            else:
                print(f"❌ 批量上传失败: {data.get('error', '未知错误')}")
                
        except ValueError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"响应内容: {response.content.decode()}")
    else:
        print(f"❌ 请求失败，状态码: {response.status_code}")
        print(f"响应内容: {response.content.decode()}")

def test_book_list_access():
    """测试书籍列表页面访问"""
    print("\n测试书籍列表页面访问...")
    
    try:
        user = User.objects.get(username='test_user')
        client = Client()
        client.force_login(user)
        
        response = client.get('/books/')
        print(f"书籍列表页面响应码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 书籍列表页面访问成功！")
            
            # 检查页面内容是否包含书籍
            content = response.content.decode()
            if '测试书籍' in content or '调试测试书籍' in content:
                print("✅ 页面包含测试书籍内容")
            else:
                print("⚠️ 页面不包含测试书籍内容")
        else:
            print("❌ 书籍列表页面访问失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    try:
        test_web_batch_upload()
        test_book_list_access()
        print("\n调试测试完成！")
    except Exception as e:
        print(f"调试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc() 