#!/usr/bin/env python
"""
实时Web服务器AI配置测试
"""
import requests
import json
import time

def test_live_web_config():
    """测试实时Web服务器的AI配置"""
    print("🌐 测试实时Web服务器AI配置...")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # 创建会话
    session = requests.Session()
    
    try:
        # 1. 获取登录页面以获取CSRF令牌
        print("1️⃣ 获取登录页面...")
        login_page = session.get(f"{base_url}/auth/login/")
        
        if login_page.status_code != 200:
            print(f"❌ 无法访问登录页面: {login_page.status_code}")
            return False
        
        # 从页面中提取CSRF令牌
        csrf_token = None
        for line in login_page.text.split('\n'):
            if 'csrfmiddlewaretoken' in line and 'value=' in line:
                start = line.find('value="') + 7
                end = line.find('"', start)
                csrf_token = line[start:end]
                break
        
        if not csrf_token:
            print("❌ 无法获取CSRF令牌")
            return False
        
        print(f"✅ 获取CSRF令牌: {csrf_token[:8]}...")
        
        # 2. 登录
        print("2️⃣ 尝试登录...")
        login_data = {
            'username': 'kejishucloud',
            'password': 'your_password_here',  # 需要替换为实际密码
            'csrfmiddlewaretoken': csrf_token
        }
        
        login_response = session.post(f"{base_url}/auth/login/", data=login_data)
        
        if login_response.status_code == 200 and 'login' not in login_response.url:
            print("✅ 登录成功")
        else:
            print("❌ 登录失败，请检查用户名和密码")
            print("💡 请手动在浏览器中登录后再测试")
            return False
        
        # 3. 获取AI配置
        print("3️⃣ 获取AI配置...")
        config_response = session.get(f"{base_url}/user/ai-config/")
        
        if config_response.status_code == 200:
            config_data = config_response.json()
            print(f"✅ 获取配置成功: {json.dumps(config_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 获取配置失败: {config_response.status_code}")
            return False
        
        # 4. 测试AI配置
        print("4️⃣ 测试AI配置...")
        
        # 获取新的CSRF令牌
        csrf_token = session.cookies.get('csrftoken')
        
        test_response = session.post(
            f"{base_url}/user/ai-config/test/",
            headers={
                'X-CSRFToken': csrf_token,
                'Content-Type': 'application/json'
            }
        )
        
        print(f"📥 测试响应状态码: {test_response.status_code}")
        
        if test_response.status_code == 200:
            test_data = test_response.json()
            print(f"✅ AI配置测试成功!")
            print(f"📄 响应数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ AI配置测试失败: {test_response.status_code}")
            try:
                error_data = test_response.json()
                print(f"📄 错误数据: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"📄 错误文本: {test_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def test_without_login():
    """不登录直接测试API端点"""
    print("\n🔓 不登录直接测试API端点...")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    try:
        # 直接测试AI配置端点
        response = requests.post(f"{base_url}/user/ai-config/test/")
        
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 302:
            print("✅ 正确重定向到登录页面 (需要认证)")
            return True
        elif response.status_code == 403:
            print("✅ 正确返回403禁止访问 (需要认证)")
            return True
        else:
            print(f"⚠️ 意外的响应状态码: {response.status_code}")
            print(f"📄 响应内容: {response.text[:200]}...")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def check_server_status():
    """检查服务器状态"""
    print("🔍 检查服务器状态...")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(base_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ 服务器正在运行")
            return True
        else:
            print(f"⚠️ 服务器响应异常: {response.status_code}")
            return False
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        print("💡 请确保Django服务器正在运行:")
        print("   python manage.py runserver 0.0.0.0:8000")
        return False
    except Exception as e:
        print(f"❌ 检查服务器状态失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 实时Web服务器AI配置测试工具")
    print("=" * 60)
    
    # 检查服务器状态
    if not check_server_status():
        return
    
    # 不登录测试
    test_without_login()
    
    # 尝试登录测试
    print("\n" + "=" * 60)
    print("💡 注意: 以下测试需要正确的用户密码")
    print("如果您不想提供密码，请手动在浏览器中测试:")
    print("1. 访问 http://localhost:8000/user/settings/")
    print("2. 登录您的账户")
    print("3. 在AI配置部分点击'测试配置'按钮")
    print("4. 查看浏览器开发者工具的Network标签页")
    print("=" * 60)
    
    # test_live_web_config()

if __name__ == "__main__":
    main() 