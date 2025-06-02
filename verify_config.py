#!/usr/bin/env python
"""
验证AI配置是否正确保存
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

def verify_config():
    """验证AI配置"""
    try:
        from readify.user_management.models import UserAIConfig
        from django.contrib.auth.models import User
        
        user = User.objects.first()
        if not user:
            print("❌ 没有找到用户")
            return False
        
        try:
            config = UserAIConfig.objects.get(user=user)
            print("✅ AI配置验证成功！")
            print(f"👤 用户: {user.username}")
            print(f"🔧 提供商: {config.provider}")
            print(f"🌐 API地址: {config.api_url}")
            print(f"🤖 模型: {config.model_id}")
            print(f"📊 最大令牌: {config.max_tokens}")
            print(f"🌡️  温度: {config.temperature}")
            print(f"⏱️  超时: {config.timeout}秒")
            print(f"🔄 状态: {'启用' if config.is_active else '禁用'}")
            return True
        except UserAIConfig.DoesNotExist:
            print("❌ 没有找到AI配置")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        return False

def test_ai_service():
    """测试AI服务"""
    try:
        from readify.ai_services.services import AIService
        from django.contrib.auth.models import User
        
        user = User.objects.first()
        if not user:
            print("❌ 没有找到用户")
            return False
        
        print("\n🧪 测试AI服务...")
        ai_service = AIService(user=user)
        
        result = ai_service._make_api_request(
            [{"role": "user", "content": "请简单回复'测试成功'"}],
            "你是一个AI助手。"
        )
        
        if result['success']:
            print("✅ AI服务测试成功！")
            print(f"📝 AI回复: {result['content'][:100]}...")
            print(f"⏱️  处理时间: {result['processing_time']:.2f}秒")
            print(f"🔢 使用令牌: {result['tokens_used']}")
            return True
        else:
            print(f"❌ AI服务测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ AI服务测试异常: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 验证AI配置...")
    print("=" * 50)
    
    config_ok = verify_config()
    
    if config_ok:
        service_ok = test_ai_service()
        
        if service_ok:
            print("\n🎉 所有测试通过！您的AI配置已正确设置。")
            print("\n💡 现在您可以在Readify中使用以下AI功能:")
            print("   - 📚 书籍智能摘要")
            print("   - ❓ 基于内容的问答")
            print("   - 🔍 关键词提取")
            print("   - 📊 文本分析")
        else:
            print("\n⚠️  配置已保存但AI服务测试失败")
    else:
        print("\n❌ 配置验证失败") 