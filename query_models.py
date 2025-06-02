#!/usr/bin/env python
"""
查询AI服务器可用模型
"""
import requests
import json

def query_available_models():
    """查询可用的模型"""
    print("🔍 查询可用模型...")
    print("=" * 50)
    
    config = {
        'api_url': 'http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1',
        'api_key': '90a07e44-8cb3-4e83-bb92-056e271b0307'
    }
    
    # 尝试查询模型列表
    models_endpoint = f"{config['api_url'].rstrip('/')}/models"
    headers = {
        'Authorization': f"Bearer {config['api_key']}",
        'Content-Type': 'application/json'
    }
    
    print(f"📡 查询端点: {models_endpoint}")
    
    try:
        response = requests.get(models_endpoint, headers=headers, timeout=30)
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 查询成功！")
            print(f"📝 可用模型: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 提取模型ID
            if 'data' in result:
                models = [model['id'] for model in result['data']]
                print(f"\n🎯 模型列表:")
                for i, model in enumerate(models, 1):
                    print(f"   {i}. {model}")
                return models
            else:
                print("⚠️  响应格式不符合预期")
                return []
        else:
            print(f"❌ 查询失败: HTTP {response.status_code}")
            try:
                error_info = response.json()
                print(f"📄 错误详情: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
            except:
                print(f"📄 错误详情: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ 查询失败: {str(e)}")
        return []

def test_common_model_names():
    """测试常见的模型名称"""
    print("\n🧪 测试常见模型名称...")
    print("=" * 50)
    
    config = {
        'api_url': 'http://serving-soagrp-656.cd001-2176.idc-2.saas.gzzsy.com.cn/v1',
        'api_key': '90a07e44-8cb3-4e83-bb92-056e271b0307'
    }
    
    # 常见的模型名称
    common_models = [
        'qwen',
        'Qwen',
        'qwen-30b',
        'Qwen-30B',
        'qwen3-30b',
        'Qwen3-30B',
        'qwen3-30b-a3b',
        'Qwen3-30B-A3B',
        '@Qwen3-30B-A3B',
        'gpt-3.5-turbo',
        'gpt-4',
        'default'
    ]
    
    endpoint = f"{config['api_url'].rstrip('/')}/chat/completions"
    headers = {
        'Authorization': f"Bearer {config['api_key']}",
        'Content-Type': 'application/json'
    }
    
    working_models = []
    
    for model in common_models:
        print(f"\n🔍 测试模型: {model}")
        
        data = {
            'model': model,
            'messages': [{'role': 'user', 'content': '测试'}],
            'max_tokens': 10
        }
        
        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=10)
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ 模型 {model} 可用")
                working_models.append(model)
            else:
                try:
                    error_info = response.json()
                    if 'error' in error_info:
                        print(f"   ❌ {error_info['error'].get('message', '未知错误')}")
                    else:
                        print(f"   ❌ HTTP {response.status_code}")
                except:
                    print(f"   ❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ 异常: {str(e)}")
    
    return working_models

def main():
    """主函数"""
    print("🚀 AI模型查询工具")
    print("=" * 50)
    
    # 查询可用模型
    available_models = query_available_models()
    
    # 测试常见模型名称
    working_models = test_common_model_names()
    
    print("\n" + "=" * 50)
    print("📊 总结:")
    
    if available_models:
        print(f"✅ 服务器报告的可用模型: {len(available_models)} 个")
        for model in available_models:
            print(f"   - {model}")
    
    if working_models:
        print(f"✅ 测试可用的模型: {len(working_models)} 个")
        for model in working_models:
            print(f"   - {model}")
        
        print(f"\n💡 建议使用模型: {working_models[0]}")
    else:
        print("❌ 没有找到可用的模型")
        print("\n💡 建议:")
        print("   1. 检查API密钥是否正确")
        print("   2. 联系服务提供商确认模型名称")
        print("   3. 检查服务器状态")

if __name__ == "__main__":
    main() 