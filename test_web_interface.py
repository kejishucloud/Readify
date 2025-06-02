#!/usr/bin/env python
"""
完整的Web界面测试，包括登录和批量上传功能
"""
import os
import sys
import django
import requests
from bs4 import BeautifulSoup
import tempfile
import time

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import BatchUpload, Book

class WebInterfaceTest:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = 'http://127.0.0.1:8000'
        
    def get_csrf_token(self, url):
        """获取CSRF token"""
        response = self.session.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrf_token:
                return csrf_token.get('value')
        return None
    
    def login(self, username='test_user', password='testpass123'):
        """登录用户"""
        print(f"\n=== 登录测试 (用户: {username}) ===")
        
        # 获取登录页面
        login_url = f'{self.base_url}/user/login/'
        csrf_token = self.get_csrf_token(login_url)
        
        if not csrf_token:
            print("❌ 无法获取CSRF token")
            return False
        
        # 提交登录表单
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200 and 'login' not in response.url:
            print("✅ 登录成功")
            return True
        elif response.status_code == 302:
            print("✅ 登录成功（重定向）")
            return True
        else:
            print(f"❌ 登录失败，状态码: {response.status_code}")
            print(f"最终URL: {response.url}")
            return False
    
    def test_batch_upload_page(self):
        """测试批量上传页面"""
        print("\n=== 批量上传页面测试 ===")
        
        upload_url = f'{self.base_url}/books/batch-upload/'
        response = self.session.get(upload_url)
        
        print(f"批量上传页面状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 批量上传页面可访问")
            
            # 检查页面内容
            soup = BeautifulSoup(response.content, 'html.parser')
            file_input = soup.find('input', {'type': 'file', 'name': 'files'})
            if file_input:
                print("✅ 文件上传控件存在")
            else:
                print("❌ 文件上传控件不存在")
                
            return True
        else:
            print(f"❌ 批量上传页面访问失败，状态码: {response.status_code}")
            return False
    
    def create_test_files(self):
        """创建测试文件"""
        test_files = []
        
        # 创建3个测试TXT文件
        for i in range(1, 4):
            content = f"""测试书籍{i}

这是一本测试书籍的内容。

第一章：介绍
这是第一章的内容，介绍了这本书的主要内容和目标。

第二章：详细内容
这里是第二章的详细内容，包含了更多的信息和示例。

第三章：总结
最后一章总结了前面章节的内容，并提供了一些建议。

作者：测试作者{i}
出版年份：2024
"""
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'_test_book_{i}.txt', delete=False, encoding='utf-8')
            temp_file.write(content)
            temp_file.close()
            
            test_files.append(temp_file.name)
        
        return test_files
    
    def test_batch_upload_functionality(self):
        """测试批量上传功能"""
        print("\n=== 批量上传功能测试 ===")
        
        # 创建测试文件
        test_files = self.create_test_files()
        print(f"创建了 {len(test_files)} 个测试文件")
        
        try:
            # 获取批量上传页面的CSRF token
            upload_url = f'{self.base_url}/books/batch-upload/'
            csrf_token = self.get_csrf_token(upload_url)
            
            if not csrf_token:
                print("❌ 无法获取CSRF token")
                return False
            
            # 准备上传数据
            files = []
            for file_path in test_files:
                files.append(('files', (os.path.basename(file_path), open(file_path, 'rb'), 'text/plain')))
            
            data = {
                'batch_name': 'Web界面测试批量上传',
                'csrfmiddlewaretoken': csrf_token
            }
            
            # 设置正确的请求头
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
            
            print("正在上传文件...")
            response = self.session.post(upload_url, data=data, files=files, headers=headers)
            
            # 关闭文件
            for _, file_tuple in files:
                file_tuple[1].close()
            
            print(f"上传响应状态码: {response.status_code}")
            print(f"响应内容类型: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print("✅ 收到JSON响应")
                    print(f"成功: {result.get('success', False)}")
                    
                    if result.get('success'):
                        batch_id = result.get('batch_id')
                        print(f"批量上传ID: {batch_id}")
                        
                        if batch_id:
                            return self.test_status_page(batch_id)
                    else:
                        print(f"上传失败: {result.get('error', '未知错误')}")
                        
                except ValueError:
                    print("⚠️ 响应不是JSON格式")
                    print(f"响应内容: {response.text[:500]}")
            else:
                print(f"❌ 上传失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}")
                
        finally:
            # 清理测试文件
            for file_path in test_files:
                try:
                    os.unlink(file_path)
                except:
                    pass
        
        return False
    
    def test_status_page(self, batch_id):
        """测试状态页面"""
        print(f"\n=== 状态页面测试 (批量ID: {batch_id}) ===")
        
        status_url = f'{self.base_url}/books/batch-upload/{batch_id}/status/'
        response = self.session.get(status_url)
        
        print(f"状态页面状态码: {response.status_code}")
        print(f"最终URL: {response.url}")
        
        if response.status_code == 200:
            print("✅ 状态页面可访问")
            
            # 检查页面内容
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找批量上传信息
            batch_name = soup.find('h4')
            if batch_name:
                print(f"批量上传名称: {batch_name.get_text().strip()}")
            
            # 查找进度信息
            progress_bars = soup.find_all('div', class_='progress-bar')
            if progress_bars:
                print("✅ 找到进度条")
            
            # 查找书籍列表
            book_rows = soup.find_all('tr', class_='book-row')
            if book_rows:
                print(f"✅ 找到 {len(book_rows)} 本书籍")
                for row in book_rows:
                    book_title = row.find('a')
                    if book_title:
                        print(f"  - {book_title.get_text().strip()}")
            else:
                print("⚠️ 没有找到书籍列表")
            
            return True
        else:
            print(f"❌ 状态页面访问失败，状态码: {response.status_code}")
            return False
    
    def test_book_list_page(self):
        """测试书籍列表页面"""
        print("\n=== 书籍列表页面测试 ===")
        
        list_url = f'{self.base_url}/books/'
        response = self.session.get(list_url)
        
        print(f"书籍列表页面状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 书籍列表页面可访问")
            
            # 检查页面内容
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找书籍卡片
            book_cards = soup.find_all('div', class_='card')
            if book_cards:
                print(f"✅ 找到 {len(book_cards)} 个书籍卡片")
                
                # 显示前几本书的信息
                for i, card in enumerate(book_cards[:5]):
                    title_link = card.find('a')
                    if title_link:
                        title = title_link.get_text().strip()
                        print(f"  {i+1}. {title}")
            else:
                print("⚠️ 没有找到书籍卡片")
                
            return True
        else:
            print(f"❌ 书籍列表页面访问失败，状态码: {response.status_code}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始Web界面完整测试...")
        
        # 1. 登录测试
        if not self.login():
            print("❌ 登录失败，停止测试")
            return
        
        # 2. 批量上传页面测试
        if not self.test_batch_upload_page():
            print("❌ 批量上传页面测试失败")
            return
        
        # 3. 批量上传功能测试
        if not self.test_batch_upload_functionality():
            print("⚠️ 批量上传功能测试未完全成功")
        
        # 4. 书籍列表页面测试
        self.test_book_list_page()
        
        print("\n=== 测试完成 ===")

def main():
    # 检查服务器是否运行
    try:
        response = requests.get('http://127.0.0.1:8000', timeout=5)
        print("✅ Django服务器正在运行")
    except requests.exceptions.ConnectionError:
        print("❌ Django服务器未运行，请先启动服务器")
        print("运行命令: python manage.py runserver 8000")
        return
    
    # 运行测试
    tester = WebInterfaceTest()
    tester.run_all_tests()

if __name__ == '__main__':
    main() 