#!/usr/bin/env python
"""
测试Web界面AI功能
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from readify.user_management.models import UserAIConfig
from readify.user_management.views import test_ai_config_view

def test_web_ai_functionality():
    """测试Web界面AI功能"""
    print("🌐 测试Web界面AI功能...")
    print("=" * 60)
    
    try:
        # 获取用户
        user = User.objects.get(username='kejishu')
        print(f"👤 用户: {user.username}")
        
        # 创建模拟请求
        factory = RequestFactory()
        request = factory.post('/user/ai-config/test/', content_type='application/json')
        request.user = user
        
        print(f"📡 发送AI配置测试请求...")
        
        # 调用视图
        response = test_ai_config_view(request)
        response_data = json.loads(response.content.decode())
        
        print(f"📊 响应结果:")
        print(f"   状态码: {response.status_code}")
        print(f"   成功: {response_data.get('success', False)}")
        
        if response_data.get('success'):
            print(f"   ✅ AI配置测试成功!")
            if 'response' in response_data:
                print(f"   AI回复: {response_data['response'][:100]}...")
            if 'processing_time' in response_data:
                print(f"   处理时间: {response_data['processing_time']:.2f}秒")
            if 'tokens_used' in response_data:
                print(f"   使用令牌: {response_data['tokens_used']}")
        else:
            print(f"   ❌ AI配置测试失败: {response_data.get('message', '未知错误')}")
        
        return response_data.get('success', False)
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_book_classification():
    """测试书籍分类功能"""
    print(f"\n📚 测试书籍分类功能...")
    print("=" * 60)
    
    try:
        from readify.books.models import Book
        from readify.ai_services.services import AIService
        
        # 获取用户和一本书
        user = User.objects.get(username='kejishu')
        books = Book.objects.filter(user=user)[:1]
        
        if not books:
            print("❌ 没有找到用户的书籍")
            return False
        
        book = books[0]
        print(f"📖 测试书籍: {book.title}")
        
        # 创建AI服务实例
        ai_service = AIService(user=user)
        
        # 测试书籍关键词提取（使用实例方法）
        print(f"🔍 执行关键词提取...")
        result = ai_service.extract_keywords(book)
        
        if result['success']:
            print(f"✅ 关键词提取成功!")
            print(f"   关键词: {result.get('keywords', [])[:5]}...")  # 只显示前5个关键词
            print(f"   处理时间: {result.get('processing_time', 0):.2f}秒")
            return True
        else:
            print(f"❌ 关键词提取失败: {result.get('error', '未知错误')}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始全面测试AI功能...")
    print("=" * 80)
    
    # 测试Web界面AI功能
    web_test_success = test_web_ai_functionality()
    
    # 测试书籍分类功能
    classification_test_success = test_book_classification()
    
    print(f"\n📋 测试总结:")
    print("=" * 80)
    print(f"Web界面AI测试: {'✅ 成功' if web_test_success else '❌ 失败'}")
    print(f"书籍分类测试: {'✅ 成功' if classification_test_success else '❌ 失败'}")
    
    if web_test_success and classification_test_success:
        print(f"\n🎉 所有AI功能测试通过！")
    else:
        print(f"\n⚠️ 部分AI功能测试失败，请检查配置。") 