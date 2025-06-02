#!/usr/bin/env python3
"""
详细测试退出登录功能
"""

import requests
import time
from urllib.parse import urljoin

def test_logout_get_detailed():
    """详细测试GET请求退出登录"""
    print("🔍 详细测试GET请求退出登录")
    print("=" * 50)
    
    session = requests.Session()
    base_url = "http://localhost:8000"
    
    # 1. 登录
    print("1. 登录测试用户...")
    login_url = urljoin(base_url, '/user/login/')
    
    # 获取登录页面的CSRF token
    login_page = session.get(login_url)
    import re
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ 无法获取登录页面的CSRF token")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # 提交登录表单
    login_data = {
        'username': 'kejishucloud',
        'password': 'kjs123456',
        'csrfmiddlewaretoken': csrf_token
    }
    
    login_response = session.post(login_url, data=login_data)
    if login_response.status_code not in [200, 302]:
        print(f"❌ 登录失败，状态码: {login_response.status_code}")
        return False
    
    print("✅ 登录成功")
    
    # 2. 测试GET请求到logout URL
    print("\n2. 发送GET请求到 /user/logout/...")
    logout_url = urljoin(base_url, '/user/logout/')
    
    get_response = session.get(logout_url)
    print(f"   状态码: {get_response.status_code}")
    print(f"   最终URL: {get_response.url}")
    
    # 3. 检查响应内容
    print("\n3. 检查响应内容...")
    response_text = get_response.text
    
    # 检查是否包含确认页面的关键元素
    checks = [
        ('退出登录确认', '页面标题'),
        ('您确定要退出登录吗', '确认消息'),
        ('确认退出', '确认按钮'),
        ('取消', '取消按钮'),
        ('csrfmiddlewaretoken', 'CSRF token'),
        ('method="post"', 'POST表单')
    ]
    
    all_checks_passed = True
    for keyword, description in checks:
        if keyword in response_text:
            print(f"   ✅ {description}: 找到 '{keyword}'")
        else:
            print(f"   ❌ {description}: 未找到 '{keyword}'")
            all_checks_passed = False
    
    # 4. 检查页面结构
    print("\n4. 检查页面结构...")
    if '<form' in response_text and 'method="post"' in response_text:
        print("   ✅ 包含POST表单")
    else:
        print("   ❌ 缺少POST表单")
        all_checks_passed = False
    
    if 'btn-danger' in response_text or 'btn btn-danger' in response_text:
        print("   ✅ 包含确认按钮样式")
    else:
        print("   ❌ 缺少确认按钮样式")
    
    if 'btn-secondary' in response_text or 'btn btn-secondary' in response_text:
        print("   ✅ 包含取消按钮样式")
    else:
        print("   ❌ 缺少取消按钮样式")
    
    # 5. 测试确认页面的POST提交
    print("\n5. 测试确认页面的POST提交...")
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response_text)
    if csrf_match:
        csrf_token = csrf_match.group(1)
        print(f"   ✅ 提取到CSRF token: {csrf_token[:10]}...")
        
        # 提交确认表单
        logout_data = {
            'csrfmiddlewaretoken': csrf_token
        }
        
        post_response = session.post(logout_url, data=logout_data)
        print(f"   POST提交状态码: {post_response.status_code}")
        
        if post_response.status_code in [200, 302]:
            print("   ✅ POST提交成功")
        else:
            print(f"   ❌ POST提交失败")
            all_checks_passed = False
    else:
        print("   ❌ 无法从确认页面提取CSRF token")
        all_checks_passed = False
    
    # 6. 总结
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 GET请求退出登录功能完全正常！")
        print("   - 正确显示确认页面")
        print("   - 包含所有必要元素")
        print("   - POST提交正常工作")
    else:
        print("⚠️ GET请求退出登录功能存在问题")
    
    return all_checks_passed

if __name__ == "__main__":
    test_logout_get_detailed() 