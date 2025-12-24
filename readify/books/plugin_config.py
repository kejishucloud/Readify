"""
书籍渲染器插件配置
集中管理插件系统的配置项
"""

from django.conf import settings

# 默认插件配置
DEFAULT_PLUGIN_CONFIG = {
    # 缓存配置
    'CACHE_ENABLED': True,
    'CACHE_TIMEOUT': 3600,  # 1小时
    'CACHE_PREFIX': 'book_render',
    
    # 预加载配置
    'PRELOAD_ENABLED': True,
    'PRELOAD_COUNT': 2,  # 预加载章节数
    'PRELOAD_MAX_WORKERS': 3,
    
    # 懒加载配置
    'LAZY_LOAD_IMAGES': True,
    'LAZY_LOAD_THRESHOLD': '10px',
    
    # 性能监控配置
    'PERFORMANCE_MONITORING': True,
    'PERFORMANCE_LOG_SLOW_QUERIES': True,
    'PERFORMANCE_SLOW_THRESHOLD': 2.0,  # 秒
    
    # 插件目录配置
    'PLUGIN_DIRECTORIES': [],
    
    # 渲染器特定配置
    'EPUB_CONFIG': {
        'extract_images': True,
        'process_css': True,
        'font_embedding': False,
    },
    
    'PDF_CONFIG': {
        'use_mupdf': True,  # 优先使用PyMuPDF
        'fallback_pypdf2': True,
        'image_quality': 2.0,  # 图片缩放倍数
        'extract_text': True,
    },
    
    'MOBI_CONFIG': {
        'convert_to_epub': True,
        'use_calibre': True,
        'conversion_timeout': 300,  # 5分钟
    },
    
    'FB2_CONFIG': {
        'encoding_detection': True,
        'supported_encodings': ['utf-8', 'windows-1251', 'cp1251'],
    },
    
    'TEXT_CONFIG': {
        'auto_detect_chapters': True,
        'chapter_patterns': [
            r'第[一二三四五六七八九十\d]+章',
            r'Chapter\s+\d+',
            r'第\d+章',
            r'章节\s*\d+',
        ],
        'max_paragraphs_per_chapter': 50,
        'markdown_extensions': ['toc', 'tables', 'fenced_code'],
    },
}


def get_plugin_config():
    """获取插件配置"""
    # 从Django设置中获取配置，如果没有则使用默认配置
    user_config = getattr(settings, 'BOOK_RENDERER_CONFIG', {})
    
    # 合并配置
    config = DEFAULT_PLUGIN_CONFIG.copy()
    config.update(user_config)
    
    return config


def get_renderer_config(renderer_name: str):
    """获取特定渲染器的配置"""
    config = get_plugin_config()
    renderer_key = f"{renderer_name.upper()}_CONFIG"
    return config.get(renderer_key, {})


def is_feature_enabled(feature_name: str) -> bool:
    """检查功能是否启用"""
    config = get_plugin_config()
    return config.get(feature_name, False)


# 配置验证函数
def validate_config(config: dict) -> list:
    """验证配置有效性，返回错误列表"""
    errors = []
    
    # 检查缓存配置
    if config.get('CACHE_TIMEOUT', 0) < 0:
        errors.append("CACHE_TIMEOUT 必须大于等于0")
        
    # 检查预加载配置
    if config.get('PRELOAD_COUNT', 0) < 0:
        errors.append("PRELOAD_COUNT 必须大于等于0")
        
    if config.get('PRELOAD_MAX_WORKERS', 0) <= 0:
        errors.append("PRELOAD_MAX_WORKERS 必须大于0")
        
    # 检查性能阈值
    if config.get('PERFORMANCE_SLOW_THRESHOLD', 0) < 0:
        errors.append("PERFORMANCE_SLOW_THRESHOLD 必须大于等于0")
        
    # 检查PDF配置
    pdf_config = config.get('PDF_CONFIG', {})
    if pdf_config.get('image_quality', 1.0) <= 0:
        errors.append("PDF_CONFIG.image_quality 必须大于0")
        
    # 检查MOBI配置
    mobi_config = config.get('MOBI_CONFIG', {})
    if mobi_config.get('conversion_timeout', 60) <= 0:
        errors.append("MOBI_CONFIG.conversion_timeout 必须大于0")
        
    # 检查文本配置
    text_config = config.get('TEXT_CONFIG', {})
    if text_config.get('max_paragraphs_per_chapter', 1) <= 0:
        errors.append("TEXT_CONFIG.max_paragraphs_per_chapter 必须大于0")
        
    return errors


# 示例配置文件模板
EXAMPLE_CONFIG = """
# 在Django settings.py中添加以下配置

BOOK_RENDERER_CONFIG = {
    # 启用缓存
    'CACHE_ENABLED': True,
    'CACHE_TIMEOUT': 7200,  # 2小时缓存
    
    # 启用预加载
    'PRELOAD_ENABLED': True,
    'PRELOAD_COUNT': 3,  # 预加载3个章节
    
    # 性能监控
    'PERFORMANCE_MONITORING': True,
    'PERFORMANCE_SLOW_THRESHOLD': 1.5,  # 1.5秒算慢查询
    
    # PDF渲染优化
    'PDF_CONFIG': {
        'use_mupdf': True,
        'image_quality': 2.5,  # 更高的图片质量
    },
    
    # EPUB处理配置
    'EPUB_CONFIG': {
        'extract_images': True,
        'process_css': True,
    },
    
    # 文本处理配置
    'TEXT_CONFIG': {
        'auto_detect_chapters': True,
        'max_paragraphs_per_chapter': 30,
    },
    
    # 外部插件目录
    'PLUGIN_DIRECTORIES': [
        '/path/to/custom/plugins',
    ],
}

# 缓存后端配置（推荐使用Redis）
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
"""


if __name__ == "__main__":
    # 配置验证示例
    config = get_plugin_config()
    errors = validate_config(config)
    
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("配置验证通过")
        
    print("\n当前配置:")
    import json
    print(json.dumps(config, indent=2, ensure_ascii=False))