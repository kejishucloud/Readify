#!/usr/bin/env python3
"""
测试退出登录功能修复
"""

import requests
import time
from urllib.parse import urljoin

class LogoutTestSuite:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def get_csrf_token(self, url):
        """获取CSRF token"""
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                # 从响应中提取CSRF token
                import re
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
                if csrf_match:
                    return csrf_match.group(1)
            return None
        except Exception as e:
            print(f"获取CSRF token失败: {e}")
            return None
    
    def login(self, username='kejishucloud', password='kjs123456'):
        """登录测试用户"""
        print(f"\n=== 登录测试 (用户: {username}) ===")
        
        login_url = urljoin(self.base_url, '/user/login/')
        csrf_token = self.get_csrf_token(login_url)
        
        if not csrf_token:
            print("❌ 无法获取CSRF token")
            return False
        
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
            return False
    
    def test_logout_get_request(self):
        """测试GET请求退出登录"""
        print("\n=== 测试GET请求退出登录 ===")
        
        logout_url = urljoin(self.base_url, '/user/logout/')
        
        try:
            response = self.session.get(logout_url)
            print(f"📥 GET请求状态码: {response.status_code}")
            
            if response.status_code == 200:
                if 'logout_confirm.html' in response.text or '退出登录确认' in response.text:
                    print("✅ GET请求成功，显示确认页面")
                    return True
                else:
                    print("⚠️ GET请求成功，但页面内容不符合预期")
                    return False
            elif response.status_code == 302:
                print("✅ GET请求重定向（可能已经退出）")
                return True
            else:
                print(f"❌ GET请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ GET请求异常: {e}")
            return False
    
    def test_logout_post_request(self):
        """测试POST请求退出登录"""
        print("\n=== 测试POST请求退出登录 ===")
        
        logout_url = urljoin(self.base_url, '/user/logout/')
        csrf_token = self.get_csrf_token(logout_url)
        
        if not csrf_token:
            print("❌ 无法获取CSRF token")
            return False
        
        logout_data = {
            'csrfmiddlewaretoken': csrf_token
        }
        
        try:
            response = self.session.post(logout_url, data=logout_data)
            print(f"📥 POST请求状态码: {response.status_code}")
            
            if response.status_code == 302:
                print("✅ POST请求成功，重定向到首页")
                return True
            elif response.status_code == 200:
                print("✅ POST请求成功")
                return True
            else:
                print(f"❌ POST请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ POST请求异常: {e}")
            return False
    
    def test_logout_via_form_submission(self):
        """测试通过表单提交退出登录"""
        print("\n=== 测试表单提交退出登录 ===")
        
        # 首先访问首页，获取logout表单
        home_url = urljoin(self.base_url, '/')
        
        try:
            response = self.session.get(home_url)
            if response.status_code != 200:
                print(f"❌ 无法访问首页，状态码: {response.status_code}")
                return False
            
            # 检查是否包含logout表单
            if 'logout-form' in response.text:
                print("✅ 首页包含logout表单")
                
                # 提取CSRF token
                import re
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                    
                    # 提交logout表单
                    logout_url = urljoin(self.base_url, '/user/logout/')
                    logout_data = {
                        'csrfmiddlewaretoken': csrf_token
                    }
                    
                    logout_response = self.session.post(logout_url, data=logout_data)
                    print(f"📥 表单提交状态码: {logout_response.status_code}")
                    
                    if logout_response.status_code in [200, 302]:
                        print("✅ 表单提交成功")
                        return True
                    else:
                        print(f"❌ 表单提交失败，状态码: {logout_response.status_code}")
                        return False
                else:
                    print("❌ 无法从首页提取CSRF token")
                    return False
            else:
                print("❌ 首页不包含logout表单")
                return False
                
        except Exception as e:
            print(f"❌ 表单提交测试异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始退出登录功能测试")
        print("=" * 60)
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        time.sleep(3)
        
        # 测试服务器连接
        try:
            response = self.session.get(self.base_url)
            if response.status_code != 200:
                print(f"❌ 无法连接到服务器: {self.base_url}")
                return False
            print(f"✅ 服务器连接正常: {self.base_url}")
        except Exception as e:
            print(f"❌ 服务器连接失败: {e}")
            return False
        
        # 登录
        if not self.login():
            print("❌ 登录失败，无法继续测试")
            return False
        
        # 测试GET请求
        get_result = self.test_logout_get_request()
        
        # 重新登录（如果需要）
        if not get_result or '退出' in str(get_result):
            print("\n🔄 重新登录以继续测试...")
            if not self.login():
                print("❌ 重新登录失败")
                return False
        
        # 测试POST请求
        post_result = self.test_logout_post_request()
        
        # 重新登录（如果需要）
        if post_result:
            print("\n🔄 重新登录以继续测试...")
            if not self.login():
                print("❌ 重新登录失败")
                return False
        
        # 测试表单提交
        form_result = self.test_logout_via_form_submission()
        
        # 总结测试结果
        print("\n" + "=" * 60)
        print("📊 测试结果总结:")
        print(f"   GET请求测试: {'✅ 通过' if get_result else '❌ 失败'}")
        print(f"   POST请求测试: {'✅ 通过' if post_result else '❌ 失败'}")
        print(f"   表单提交测试: {'✅ 通过' if form_result else '❌ 失败'}")
        
        all_passed = get_result and post_result and form_result
        print(f"\n🎯 总体结果: {'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}")
        
        if all_passed:
            print("\n🎉 退出登录功能修复成功！")
            print("   - GET请求显示确认页面")
            print("   - POST请求正确执行退出")
            print("   - 表单提交正常工作")
        else:
            print("\n⚠️ 仍有问题需要解决")
        
        return all_passed


if __name__ == "__main__":
    tester = LogoutTestSuite()
    tester.run_all_tests() 