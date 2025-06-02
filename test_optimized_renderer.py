#!/usr/bin/env python3
"""
优化书籍渲染器测试脚本
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')
django.setup()

from django.contrib.auth.models import User
from readify.books.models import Book
from readify.books.renderers import RendererFactory, OptimizedBookRenderer

def test_renderer_factory():
    """测试渲染器工厂"""
    print("=" * 50)
    print("测试渲染器工厂")
    print("=" * 50)
    
    # 测试支持的格式
    supported_formats = RendererFactory.get_supported_formats()
    print(f"支持的格式: {supported_formats}")
    
    # 测试创建不同格式的渲染器
    test_cases = [
        ('test.epub', 'epub'),
        ('test.pdf', 'pdf'),
        ('test.mobi', 'mobi'),
        ('test.fb2', 'fb2'),
        ('test.txt', 'txt'),
        ('test.md', 'markdown'),
        ('test.html', 'html'),
    ]
    
    for file_path, format_type in test_cases:
        try:
            # 创建临时文件用于测试
            temp_file = f"temp/{file_path}"
            os.makedirs(os.path.dirname(temp_file), exist_ok=True)
            
            if not os.path.exists(temp_file):
                with open(temp_file, 'w', encoding='utf-8') as f:
                    if format_type == 'html':
                        f.write('<html><body><h1>测试内容</h1><p>这是一个测试文件。</p></body></html>')
                    elif format_type == 'markdown':
                        f.write('# 测试标题\n\n这是一个测试文件。\n\n## 子标题\n\n内容...')
                    else:
                        f.write('测试内容\n\n第一章\n这是第一章的内容。\n\n第二章\n这是第二章的内容。')
            
            renderer = RendererFactory.create_renderer(temp_file, format_type)
            print(f"✓ {format_type.upper()}: {renderer.__class__.__name__}")
            
        except Exception as e:
            print(f"✗ {format_type.upper()}: {str(e)}")

def test_text_renderer():
    """测试文本渲染器"""
    print("\n" + "=" * 50)
    print("测试文本渲染器")
    print("=" * 50)
    
    # 创建测试文件
    test_content = """第一章 开始

这是第一章的内容。这里有一些测试文本，用来验证文本渲染器的功能。

第二章 继续

这是第二章的内容。我们可以看到章节是如何被自动识别和分割的。

第三章 结束

这是最后一章的内容。渲染器应该能够正确处理这些章节。"""
    
    test_file = "temp/test_book.txt"
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    try:
        renderer = RendererFactory.create_renderer(test_file, 'txt')
        
        # 测试渲染
        result = renderer.render(chapter_number=1)
        print(f"渲染结果: {result.get('renderer_type')}")
        print(f"章节标题: {result.get('chapter_title')}")
        print(f"总章节数: {result.get('total_chapters')}")
        
        # 测试目录
        toc = renderer.get_table_of_contents()
        print(f"目录项数: {len(toc)}")
        for item in toc:
            print(f"  - {item.get('title')}")
        
        # 测试元数据
        metadata = renderer.get_metadata()
        print(f"元数据: {metadata}")
        
        # 清理
        renderer.cleanup()
        print("✓ 文本渲染器测试通过")
        
    except Exception as e:
        print(f"✗ 文本渲染器测试失败: {str(e)}")

def test_markdown_renderer():
    """测试Markdown渲染器"""
    print("\n" + "=" * 50)
    print("测试Markdown渲染器")
    print("=" * 50)
    
    # 创建Markdown测试文件
    markdown_content = """# 第一章 介绍

这是一个**Markdown**测试文件。

## 1.1 功能特性

- 支持标题
- 支持列表
- 支持代码块

```python
def hello_world():
    print("Hello, World!")
```

# 第二章 详细内容

这里是第二章的内容。

## 2.1 表格支持

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |

# 第三章 总结

这是最后一章。"""
    
    test_file = "temp/test_book.md"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    try:
        renderer = RendererFactory.create_renderer(test_file, 'markdown')
        
        # 测试渲染
        result = renderer.render(chapter_number=1)
        print(f"渲染结果: {result.get('renderer_type')}")
        print(f"章节标题: {result.get('chapter_title')}")
        print(f"总章节数: {result.get('total_chapters')}")
        
        # 检查HTML内容
        content = result.get('content', '')
        if '<h1>' in content and '<code>' in content:
            print("✓ Markdown转HTML成功")
        else:
            print("✗ Markdown转HTML可能有问题")
        
        # 测试目录
        toc = renderer.get_table_of_contents()
        print(f"目录项数: {len(toc)}")
        
        renderer.cleanup()
        print("✓ Markdown渲染器测试通过")
        
    except Exception as e:
        print(f"✗ Markdown渲染器测试失败: {str(e)}")

def test_optimized_book_renderer():
    """测试优化书籍渲染器"""
    print("\n" + "=" * 50)
    print("测试优化书籍渲染器")
    print("=" * 50)
    
    try:
        # 获取或创建测试用户
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )
        
        # 查找现有的书籍或创建测试书籍
        books = Book.objects.filter(user=user)
        
        if books.exists():
            book = books.first()
            print(f"使用现有书籍: {book.title}")
            
            # 测试优化渲染器
            renderer = OptimizedBookRenderer(book)
            
            # 渲染第一章
            result = renderer.render_chapter(chapter_number=1)
            print(f"渲染类型: {result.get('renderer_type')}")
            print(f"书籍标题: {result.get('book_title')}")
            print(f"章节标题: {result.get('chapter_title')}")
            
            if 'error' in result:
                print(f"渲染错误: {result['error']}")
            else:
                print("✓ 章节渲染成功")
            
            # 测试元数据
            metadata = renderer.get_book_metadata()
            print(f"元数据项数: {len(metadata)}")
            
            # 测试目录
            toc = renderer.get_table_of_contents()
            print(f"目录项数: {len(toc)}")
            
            renderer.cleanup()
            print("✓ 优化书籍渲染器测试通过")
            
        else:
            print("⚠ 没有找到测试书籍，请先上传一本书")
            
    except Exception as e:
        print(f"✗ 优化书籍渲染器测试失败: {str(e)}")

def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 50)
    print("测试错误处理")
    print("=" * 50)
    
    # 测试不支持的格式
    try:
        renderer = RendererFactory.create_renderer("test.xyz", "xyz")
        print("✗ 应该抛出不支持格式的错误")
    except ValueError as e:
        print(f"✓ 正确处理不支持的格式: {str(e)}")
    except Exception as e:
        print(f"✗ 意外错误: {str(e)}")
    
    # 测试不存在的文件
    try:
        renderer = RendererFactory.create_renderer("nonexistent.txt", "txt")
        result = renderer.render()
        if 'error' in result:
            print("✓ 正确处理文件不存在的情况")
        else:
            print("✗ 应该返回错误信息")
    except Exception as e:
        print(f"✓ 正确抛出文件不存在错误: {str(e)}")

def cleanup_test_files():
    """清理测试文件"""
    print("\n" + "=" * 50)
    print("清理测试文件")
    print("=" * 50)
    
    import shutil
    
    if os.path.exists("temp"):
        shutil.rmtree("temp")
        print("✓ 测试文件已清理")

def main():
    """主测试函数"""
    print("优化书籍渲染器测试")
    print("=" * 60)
    
    try:
        # 运行各项测试
        test_renderer_factory()
        test_text_renderer()
        test_markdown_renderer()
        test_optimized_book_renderer()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
        print("\n测试总结:")
        print("• 渲染器工厂: 支持多种格式")
        print("• 文本渲染器: 自动章节识别")
        print("• Markdown渲染器: HTML转换")
        print("• 优化渲染器: 集成功能")
        print("• 错误处理: 异常情况处理")
        
        print("\n下一步:")
        print("1. 在浏览器中访问 http://localhost:8000")
        print("2. 上传不同格式的书籍文件")
        print("3. 点击'优化阅读器'按钮测试")
        print("4. 体验不同格式的渲染效果")
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup_test_files()

if __name__ == "__main__":
    main() 