#!/usr/bin/env python
"""
UI一致性和跳转功能测试脚本
测试主页、个人资料、用户设置、书籍列表页面的风格一致性和跳转功能
"""

import os
import sys
import json
import re

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')

import django
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from readify.user_management.models import UserProfile
from readify.books.models import Book, BookNote, ReadingProgress

def test_ui_consistency():
    """测试UI一致性"""
    print("🎨 开始测试UI一致性...")
    
    # 定义需要检查的页面模板
    templates = {
        'home': 'frontend/templates/home.html',
        'profile': 'frontend/templates/user_management/profile.html',
        'settings': 'frontend/templates/user_management/settings.html',
        'books': 'frontend/templates/books/book_list.html'
    }
    
    # 定义一致性检查项
    consistency_checks = {
        'gradient_background': r'linear-gradient\(135deg, #667eea 0%, #764ba2 100%\)',
        'card_shadow': r'box-shadow: 0 2px 10px rgba\(0,0,0,0\.1\)',
        'border_radius': r'border-radius: 15px',
        'hover_transform': r'transform: translateY\(-5px\)',
        'btn_primary_gradient': r'background: linear-gradient\(135deg, #667eea 0%, #764ba2 100%\)',
        'form_border_radius': r'border-radius: 10px',
        'breadcrumb_style': r'breadcrumb',
        'section_title_border': r'border-bottom: 3px solid #667eea'
    }
    
    results = {}
    
    for page_name, template_path in templates.items():
        print(f"\n📄 检查 {page_name} 页面...")
        results[page_name] = {}
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for check_name, pattern in consistency_checks.items():
                if re.search(pattern, content):
                    results[page_name][check_name] = True
                    print(f"  ✅ {check_name}: 通过")
                else:
                    results[page_name][check_name] = False
                    print(f"  ❌ {check_name}: 未找到")
            
            # 检查英雄区域
            if 'hero' in content:
                results[page_name]['hero_section'] = True
                print(f"  ✅ hero_section: 通过")
            else:
                results[page_name]['hero_section'] = False
                print(f"  ❌ hero_section: 未找到")
            
            # 检查统计卡片
            if 'stat-card' in content:
                results[page_name]['stat_cards'] = True
                print(f"  ✅ stat_cards: 通过")
            else:
                results[page_name]['stat_cards'] = False
                print(f"  ❌ stat_cards: 未找到")
                
        except FileNotFoundError:
            print(f"  ❌ 模板文件未找到: {template_path}")
            results[page_name] = {'error': 'file_not_found'}
    
    return results

def test_navigation_links():
    """测试页面间的导航链接"""
    print("\n🔗 开始测试页面导航链接...")
    
    # 定义页面间的导航关系
    navigation_tests = {
        'home': {
            'template': 'frontend/templates/home.html',
            'expected_links': [
                r'href="{% url \'user_management:settings\' %}"',
                r'href="{% url \'user_management:update_profile\' %}"',
                r'href="{% url \'book_list\' %}"',
                r'href="{% url \'batch_upload\' %}"'
            ]
        },
        'profile': {
            'template': 'frontend/templates/user_management/profile.html',
            'expected_links': [
                r'href="{% url \'home\' %}"',
                r'href="{% url \'user_management:settings\' %}"'
            ]
        },
        'settings': {
            'template': 'frontend/templates/user_management/settings.html',
            'expected_links': [
                r'href="{% url \'home\' %}"',
                r'href="{% url \'user_management:update_profile\' %}"',
                r'href="{% url \'book_list\' %}"',
                r'href="{% url \'batch_upload\' %}"'
            ]
        },
        'books': {
            'template': 'frontend/templates/books/book_list.html',
            'expected_links': [
                r'href="{% url \'home\' %}"',
                r'href="{% url \'book_upload\' %}"',
                r'href="{% url \'batch_upload\' %}"',
                r'href="{% url \'user_management:settings\' %}"'
            ]
        }
    }
    
    results = {}
    
    for page_name, test_config in navigation_tests.items():
        print(f"\n📄 检查 {page_name} 页面导航...")
        results[page_name] = {}
        
        try:
            with open(test_config['template'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            for i, link_pattern in enumerate(test_config['expected_links']):
                if re.search(link_pattern, content):
                    results[page_name][f'link_{i+1}'] = True
                    print(f"  ✅ 导航链接 {i+1}: 通过")
                else:
                    results[page_name][f'link_{i+1}'] = False
                    print(f"  ❌ 导航链接 {i+1}: 未找到 - {link_pattern}")
                    
        except FileNotFoundError:
            print(f"  ❌ 模板文件未找到: {test_config['template']}")
            results[page_name] = {'error': 'file_not_found'}
    
    return results

def test_functional_navigation():
    """测试功能性导航"""
    print("\n🚀 开始测试功能性导航...")
    
    # 清理可能存在的测试数据
    try:
        existing_user = User.objects.filter(username='testuser_nav').first()
        if existing_user:
            Book.objects.filter(user=existing_user).delete()
            UserProfile.objects.filter(user=existing_user).delete()
            existing_user.delete()
    except Exception as e:
        print(f"⚠️  清理测试数据时出现警告: {e}")
    
    # 创建测试用户
    user = User.objects.create_user(
        username='testuser_nav',
        email='test_nav@example.com',
        password='testpass123',
        first_name='导航',
        last_name='测试'
    )
    
    # 创建用户配置文件
    profile = UserProfile.objects.create(
        user=user,
        bio='导航测试用户',
        location='测试城市'
    )
    
    # 创建测试客户端
    client = Client()
    client.login(username='testuser_nav', password='testpass123')
    
    # 定义要测试的页面
    test_pages = [
        ('home', reverse('home')),
        ('profile', reverse('user_management:update_profile')),
        ('settings', reverse('user_management:settings')),
        ('books', reverse('book_list'))
    ]
    
    results = {}
    
    for page_name, url in test_pages:
        print(f"\n📄 测试 {page_name} 页面访问...")
        
        try:
            response = client.get(url)
            
            if response.status_code == 200:
                results[page_name] = {
                    'status': 'success',
                    'status_code': response.status_code,
                    'has_content': len(response.content) > 0
                }
                print(f"  ✅ 页面加载成功 (状态码: {response.status_code})")
                
                # 检查页面内容
                content = response.content.decode('utf-8')
                
                # 检查是否包含英雄区域
                if 'hero' in content:
                    results[page_name]['has_hero'] = True
                    print(f"  ✅ 包含英雄区域")
                else:
                    results[page_name]['has_hero'] = False
                    print(f"  ❌ 缺少英雄区域")
                
                # 检查是否包含面包屑导航
                if 'breadcrumb' in content:
                    results[page_name]['has_breadcrumb'] = True
                    print(f"  ✅ 包含面包屑导航")
                else:
                    results[page_name]['has_breadcrumb'] = False
                    print(f"  ❌ 缺少面包屑导航")
                
                # 检查是否包含用户名
                if user.username in content:
                    results[page_name]['has_username'] = True
                    print(f"  ✅ 显示用户名")
                else:
                    results[page_name]['has_username'] = False
                    print(f"  ❌ 未显示用户名")
                    
            else:
                results[page_name] = {
                    'status': 'error',
                    'status_code': response.status_code
                }
                print(f"  ❌ 页面加载失败 (状态码: {response.status_code})")
                
        except Exception as e:
            results[page_name] = {
                'status': 'exception',
                'error': str(e)
            }
            print(f"  ❌ 页面访问异常: {e}")
    
    # 清理测试数据
    try:
        Book.objects.filter(user=user).delete()
        UserProfile.objects.filter(user=user).delete()
        User.objects.filter(username='testuser_nav').delete()
        print("\n🧹 测试数据清理完成")
    except Exception as e:
        print(f"⚠️  清理测试数据时出现警告: {e}")
    
    return results

def test_responsive_design():
    """测试响应式设计元素"""
    print("\n📱 开始测试响应式设计...")
    
    templates = [
        'frontend/templates/home.html',
        'frontend/templates/user_management/profile.html',
        'frontend/templates/user_management/settings.html',
        'frontend/templates/books/book_list.html'
    ]
    
    responsive_patterns = [
        r'col-md-\d+',  # Bootstrap网格系统
        r'col-lg-\d+',
        r'col-sm-\d+',
        r'd-flex',      # Flexbox
        r'justify-content-',
        r'align-items-',
        r'@media',      # 媒体查询
        r'container',   # 容器类
        r'row'          # 行类
    ]
    
    results = {}
    
    for template_path in templates:
        page_name = os.path.basename(template_path).replace('.html', '')
        print(f"\n📄 检查 {page_name} 响应式设计...")
        results[page_name] = {}
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern in responsive_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    results[page_name][pattern] = len(matches)
                    print(f"  ✅ {pattern}: 找到 {len(matches)} 个匹配")
                else:
                    results[page_name][pattern] = 0
                    print(f"  ❌ {pattern}: 未找到")
                    
        except FileNotFoundError:
            print(f"  ❌ 模板文件未找到: {template_path}")
            results[page_name] = {'error': 'file_not_found'}
    
    return results

def generate_report(ui_results, nav_results, func_results, responsive_results):
    """生成测试报告"""
    print("\n" + "="*80)
    print("📊 UI一致性和导航功能测试报告")
    print("="*80)
    
    # UI一致性报告
    print("\n🎨 UI一致性测试结果:")
    for page, checks in ui_results.items():
        if 'error' not in checks:
            passed = sum(1 for v in checks.values() if v)
            total = len(checks)
            percentage = (passed / total) * 100 if total > 0 else 0
            print(f"  {page}: {passed}/{total} 项通过 ({percentage:.1f}%)")
        else:
            print(f"  {page}: 测试失败 - {checks['error']}")
    
    # 导航链接报告
    print("\n🔗 导航链接测试结果:")
    for page, checks in nav_results.items():
        if 'error' not in checks:
            passed = sum(1 for v in checks.values() if v)
            total = len(checks)
            percentage = (passed / total) * 100 if total > 0 else 0
            print(f"  {page}: {passed}/{total} 个链接正确 ({percentage:.1f}%)")
        else:
            print(f"  {page}: 测试失败 - {checks['error']}")
    
    # 功能性导航报告
    print("\n🚀 功能性导航测试结果:")
    for page, result in func_results.items():
        if result.get('status') == 'success':
            features = []
            if result.get('has_hero'): features.append('英雄区域')
            if result.get('has_breadcrumb'): features.append('面包屑')
            if result.get('has_username'): features.append('用户名')
            print(f"  {page}: ✅ 成功 - 包含: {', '.join(features)}")
        else:
            print(f"  {page}: ❌ 失败 - {result.get('error', '未知错误')}")
    
    # 响应式设计报告
    print("\n📱 响应式设计测试结果:")
    for page, checks in responsive_results.items():
        if 'error' not in checks:
            total_matches = sum(v for v in checks.values() if isinstance(v, int))
            print(f"  {page}: 找到 {total_matches} 个响应式元素")
        else:
            print(f"  {page}: 测试失败 - {checks['error']}")
    
    # 总体评估
    print("\n📋 总体评估:")
    
    # 计算UI一致性得分
    ui_scores = []
    for page, checks in ui_results.items():
        if 'error' not in checks:
            passed = sum(1 for v in checks.values() if v)
            total = len(checks)
            ui_scores.append((passed / total) * 100 if total > 0 else 0)
    
    avg_ui_score = sum(ui_scores) / len(ui_scores) if ui_scores else 0
    
    # 计算导航得分
    nav_scores = []
    for page, checks in nav_results.items():
        if 'error' not in checks:
            passed = sum(1 for v in checks.values() if v)
            total = len(checks)
            nav_scores.append((passed / total) * 100 if total > 0 else 0)
    
    avg_nav_score = sum(nav_scores) / len(nav_scores) if nav_scores else 0
    
    # 计算功能得分
    func_success = sum(1 for result in func_results.values() if result.get('status') == 'success')
    func_total = len(func_results)
    func_score = (func_success / func_total) * 100 if func_total > 0 else 0
    
    print(f"  UI一致性平均得分: {avg_ui_score:.1f}%")
    print(f"  导航链接平均得分: {avg_nav_score:.1f}%")
    print(f"  功能性导航得分: {func_score:.1f}%")
    
    overall_score = (avg_ui_score + avg_nav_score + func_score) / 3
    print(f"  总体得分: {overall_score:.1f}%")
    
    if overall_score >= 90:
        print("  🎉 优秀！UI一致性和导航功能表现出色")
    elif overall_score >= 80:
        print("  👍 良好！大部分功能正常，有少量改进空间")
    elif overall_score >= 70:
        print("  ⚠️  一般，需要进一步优化")
    else:
        print("  ❌ 需要重点改进UI一致性和导航功能")

def main():
    """主函数"""
    print("🎯 Readify UI一致性和导航功能测试")
    print("="*60)
    
    try:
        # 运行各项测试
        ui_results = test_ui_consistency()
        nav_results = test_navigation_links()
        func_results = test_functional_navigation()
        responsive_results = test_responsive_design()
        
        # 生成报告
        generate_report(ui_results, nav_results, func_results, responsive_results)
        
        print("\n" + "="*60)
        print("🎉 UI一致性和导航功能测试完成!")
        print("="*60)
        
        # 保存详细结果到文件
        detailed_results = {
            'ui_consistency': ui_results,
            'navigation_links': nav_results,
            'functional_navigation': func_results,
            'responsive_design': responsive_results,
            'timestamp': str(django.utils.timezone.now())
        }
        
        with open('ui_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2)
        
        print("\n📄 详细测试结果已保存到 ui_test_results.json")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 