"""
书籍渲染器插件系统
支持可扩展的插件化架构，动态加载不同格式的渲染器
"""

import os
import json
import logging
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Tuple
from pathlib import Path
from django.conf import settings
from django.utils.safestring import mark_safe
from .performance_optimizer import create_optimized_renderer, performance_monitor

logger = logging.getLogger(__name__)


class BookRendererPlugin(ABC):
    """书籍渲染器插件基类"""
    
    # 插件信息
    plugin_name: str = ""
    plugin_version: str = "1.0.0"
    supported_formats: List[str] = []
    priority: int = 0  # 优先级，数值越高优先级越高
    render_engine: str = "default"
    
    def __init__(self, book_file_path: str, book_format: str):
        self.book_file_path = book_file_path
        self.book_format = book_format.lower()
        self.temp_dir = None
        self.config = self._load_plugin_config()
        
    @abstractmethod
    def can_handle(self, book_format: str) -> bool:
        """检查插件是否可以处理指定格式"""
        pass
        
    @abstractmethod
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染指定章节和页面"""
        pass

    def render_chapter(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """兼容优化渲染器的章节渲染入口"""
        return self.render(chapter_number, page_number)
        
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """获取书籍元数据"""
        pass
        
    @abstractmethod
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取目录结构"""
        pass
        
    def preprocess(self) -> bool:
        """预处理步骤，返回是否成功"""
        return True
        
    def postprocess(self, render_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理步骤，可以修改渲染结果"""
        return render_result
        
    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
    def _load_plugin_config(self) -> Dict[str, Any]:
        """加载插件配置"""
        config_path = getattr(settings, 'BOOK_RENDERER_CONFIG', {})
        plugin_config = config_path.get(self.__class__.__name__, {})
        return plugin_config
        
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            'name': self.plugin_name,
            'version': self.plugin_version,
            'supported_formats': self.supported_formats,
            'priority': self.priority,
            'render_engine': self.render_engine,
            'class_name': self.__class__.__name__
        }


class EPUBRendererPlugin(BookRendererPlugin):
    """EPUB渲染器插件"""
    
    plugin_name = "EPUB 渲染器"
    plugin_version = "2.0.0"
    supported_formats = ['epub']
    priority = 100
    render_engine = "epub.js"
    
    def __init__(self, book_file_path: str, book_format: str = 'epub'):
        super().__init__(book_file_path, book_format)
        self.epub_data = None
        self.spine = []
        self.manifest = {}
        
    def can_handle(self, book_format: str) -> bool:
        return book_format.lower() in self.supported_formats
        
    def preprocess(self) -> bool:
        """预处理EPUB文件"""
        try:
            from .renderers import EPUBRenderer
            self._renderer = EPUBRenderer(self.book_file_path, self.book_format)
            return True
        except Exception as e:
            logger.error(f"EPUB插件预处理失败: {str(e)}")
            return False
            
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染EPUB内容"""
        if not hasattr(self, '_renderer'):
            if not self.preprocess():
                return {'error': 'EPUB插件初始化失败'}
                
        result = self._renderer.render(chapter_number, page_number)
        result['plugin_name'] = self.plugin_name
        result['plugin_version'] = self.plugin_version
        result['render_engine'] = self.render_engine
        return self.postprocess(result)
        
    def get_metadata(self) -> Dict[str, Any]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_metadata()
        return {}
        
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_table_of_contents()
        return []
        
    def cleanup(self):
        super().cleanup()
        if hasattr(self, '_renderer'):
            self._renderer.cleanup()


class PDFRendererPlugin(BookRendererPlugin):
    """PDF渲染器插件"""
    
    plugin_name = "PDF 渲染器"
    plugin_version = "2.0.0"
    supported_formats = ['pdf']
    priority = 90
    render_engine = "Vivliostyle"
    
    def can_handle(self, book_format: str) -> bool:
        return book_format.lower() in self.supported_formats
        
    def preprocess(self) -> bool:
        """预处理PDF文件"""
        try:
            from .renderers import PDFRenderer
            self._renderer = PDFRenderer(self.book_file_path, self.book_format)
            return True
        except Exception as e:
            logger.error(f"PDF插件预处理失败: {str(e)}")
            return False
            
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染PDF内容"""
        if not hasattr(self, '_renderer'):
            if not self.preprocess():
                return {'error': 'PDF插件初始化失败'}
                
        result = self._renderer.render(chapter_number, page_number)
        result['plugin_name'] = self.plugin_name
        result['plugin_version'] = self.plugin_version
        result['render_engine'] = self.render_engine
        return self.postprocess(result)
        
    def get_metadata(self) -> Dict[str, Any]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_metadata()
        return {}
        
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_table_of_contents()
        return []


class MOBIRendererPlugin(BookRendererPlugin):
    """MOBI渲染器插件"""
    
    plugin_name = "MOBI/AZW3 渲染器"
    plugin_version = "2.0.0"
    supported_formats = ['mobi', 'azw3']
    priority = 80
    render_engine = "Readium"
    
    def can_handle(self, book_format: str) -> bool:
        return book_format.lower() in self.supported_formats
        
    def preprocess(self) -> bool:
        """预处理MOBI文件"""
        try:
            from .renderers import MOBIRenderer
            self._renderer = MOBIRenderer(self.book_file_path, self.book_format)
            return True
        except Exception as e:
            logger.error(f"MOBI插件预处理失败: {str(e)}")
            return False
            
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染MOBI内容"""
        if not hasattr(self, '_renderer'):
            if not self.preprocess():
                return {'error': 'MOBI插件初始化失败'}
                
        result = self._renderer.render(chapter_number, page_number)
        result['plugin_name'] = self.plugin_name
        result['plugin_version'] = self.plugin_version
        result['render_engine'] = self.render_engine
        return self.postprocess(result)
        
    def get_metadata(self) -> Dict[str, Any]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_metadata()
        return {}
        
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_table_of_contents()
        return []


class FB2RendererPlugin(BookRendererPlugin):
    """FB2渲染器插件"""
    
    plugin_name = "FB2 渲染器"
    plugin_version = "2.0.0"
    supported_formats = ['fb2']
    priority = 70
    render_engine = "Vivliostyle"
    
    def can_handle(self, book_format: str) -> bool:
        return book_format.lower() in self.supported_formats
        
    def preprocess(self) -> bool:
        """预处理FB2文件"""
        try:
            from .renderers import FB2Renderer
            self._renderer = FB2Renderer(self.book_file_path, self.book_format)
            return True
        except Exception as e:
            logger.error(f"FB2插件预处理失败: {str(e)}")
            return False
            
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染FB2内容"""
        if not hasattr(self, '_renderer'):
            if not self.preprocess():
                return {'error': 'FB2插件初始化失败'}
                
        result = self._renderer.render(chapter_number, page_number)
        result['plugin_name'] = self.plugin_name
        result['plugin_version'] = self.plugin_version
        result['render_engine'] = self.render_engine
        return self.postprocess(result)
        
    def get_metadata(self) -> Dict[str, Any]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_metadata()
        return {}
        
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_table_of_contents()
        return []


class DocxRendererPlugin(BookRendererPlugin):
    """DOCX/DOC渲染器插件"""
    
    plugin_name = "Word 渲染器"
    plugin_version = "1.0.0"
    supported_formats = ['docx', 'doc']
    priority = 65
    render_engine = "Paged.js"
    
    def can_handle(self, book_format: str) -> bool:
        return book_format.lower() in self.supported_formats
        
    def preprocess(self) -> bool:
        """预处理DOCX/DOC文件"""
        try:
            from .renderers import DocxRenderer
            self._renderer = DocxRenderer(self.book_file_path, self.book_format)
            return True
        except Exception as e:
            logger.error(f"Word插件预处理失败: {str(e)}")
            return False
            
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染DOCX/DOC内容"""
        if not hasattr(self, '_renderer'):
            if not self.preprocess():
                return {'error': 'Word插件初始化失败'}
                
        result = self._renderer.render(chapter_number, page_number)
        result['plugin_name'] = self.plugin_name
        result['plugin_version'] = self.plugin_version
        result['render_engine'] = self.render_engine
        return self.postprocess(result)
        
    def get_metadata(self) -> Dict[str, Any]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_metadata()
        return {}
        
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_table_of_contents()
        return []


class TextRendererPlugin(BookRendererPlugin):
    """文本渲染器插件"""
    
    plugin_name = "文本渲染器"
    plugin_version = "2.0.0"
    supported_formats = ['txt', 'markdown', 'md', 'html', 'htm']
    priority = 60
    render_engine = "Paged.js"
    
    def can_handle(self, book_format: str) -> bool:
        return book_format.lower() in self.supported_formats
        
    def preprocess(self) -> bool:
        """预处理文本文件"""
        try:
            from .renderers import TextRenderer
            self._renderer = TextRenderer(self.book_file_path, self.book_format)
            return True
        except Exception as e:
            logger.error(f"文本插件预处理失败: {str(e)}")
            return False
            
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染文本内容"""
        if not hasattr(self, '_renderer'):
            if not self.preprocess():
                return {'error': '文本插件初始化失败'}
                
        result = self._renderer.render(chapter_number, page_number)
        result['plugin_name'] = self.plugin_name
        result['plugin_version'] = self.plugin_version
        result['render_engine'] = self.render_engine
        return self.postprocess(result)
        
    def get_metadata(self) -> Dict[str, Any]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_metadata()
        return {}
        
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        if hasattr(self, '_renderer'):
            return self._renderer.get_table_of_contents()
        return []


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, Type[BookRendererPlugin]] = {}
        self.plugin_instances: Dict[str, BookRendererPlugin] = {}
        self._load_builtin_plugins()
        self._load_external_plugins()
        
    def _load_builtin_plugins(self):
        """加载内置插件"""
        builtin_plugins = [
            EPUBRendererPlugin,
            PDFRendererPlugin,
            MOBIRendererPlugin,
            FB2RendererPlugin,
            DocxRendererPlugin,
            TextRendererPlugin,
        ]
        
        for plugin_class in builtin_plugins:
            self.register_plugin(plugin_class)
            
    def _load_external_plugins(self):
        """加载外部插件"""
        try:
            # 从配置中获取插件目录
            plugin_dirs = getattr(settings, 'BOOK_RENDERER_PLUGIN_DIRS', [])
            
            for plugin_dir in plugin_dirs:
                self._scan_plugin_directory(plugin_dir)
                
        except Exception as e:
            logger.error(f"加载外部插件失败: {str(e)}")
            
    def _scan_plugin_directory(self, plugin_dir: str):
        """扫描插件目录"""
        if not os.path.exists(plugin_dir):
            return
            
        for file_name in os.listdir(plugin_dir):
            if file_name.endswith('.py') and not file_name.startswith('__'):
                self._load_plugin_from_file(plugin_dir, file_name)
                
    def _load_plugin_from_file(self, plugin_dir: str, file_name: str):
        """从文件加载插件"""
        try:
            module_name = file_name[:-3]  # 移除.py扩展名
            spec = importlib.util.spec_from_file_location(
                module_name, 
                os.path.join(plugin_dir, file_name)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BookRendererPlugin) and 
                    obj != BookRendererPlugin):
                    self.register_plugin(obj)
                    
        except Exception as e:
            logger.error(f"加载插件文件 {file_name} 失败: {str(e)}")
            
    def register_plugin(self, plugin_class: Type[BookRendererPlugin]):
        """注册插件"""
        try:
            plugin_name = plugin_class.__name__
            self.plugins[plugin_name] = plugin_class
            logger.info(f"注册插件: {plugin_name}")
        except Exception as e:
            logger.error(f"注册插件失败: {str(e)}")
            
    def get_plugin_for_format(self, book_format: str) -> Optional[Type[BookRendererPlugin]]:
        """根据格式获取最适合的插件"""
        format_lower = book_format.lower()
        suitable_plugins = []
        
        for plugin_class in self.plugins.values():
            # 创建临时实例来检查是否支持该格式
            temp_instance = plugin_class("", format_lower)
            if temp_instance.can_handle(format_lower):
                suitable_plugins.append((plugin_class, temp_instance.priority))
                
        if suitable_plugins:
            # 按优先级排序，返回优先级最高的
            suitable_plugins.sort(key=lambda x: x[1], reverse=True)
            return suitable_plugins[0][0]
            
        return None
        
    def create_renderer(self, book_file_path: str, book_format: str) -> Optional[BookRendererPlugin]:
        """创建渲染器实例"""
        plugin_class = self.get_plugin_for_format(book_format)
        if plugin_class:
            try:
                return plugin_class(book_file_path, book_format)
            except Exception as e:
                logger.error(f"创建渲染器实例失败: {str(e)}")
                
        return None
        
    def get_supported_formats(self) -> List[str]:
        """获取所有支持的格式"""
        formats = set()
        for plugin_class in self.plugins.values():
            temp_instance = plugin_class("", "")
            formats.update(temp_instance.supported_formats)
            
        return sorted(list(formats))
        
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """获取所有插件信息"""
        info_list = []
        for plugin_class in self.plugins.values():
            temp_instance = plugin_class("", "")
            info_list.append(temp_instance.get_plugin_info())
            
        return info_list


# 全局插件管理器实例
plugin_manager = PluginManager()


class EnhancedBookRenderer:
    """增强的书籍渲染器，使用插件系统和性能优化"""
    
    def __init__(self, book, enable_optimization: bool = True):
        self.book = book
        self.renderer_plugin = None
        self.optimized_renderer = None
        self.enable_optimization = enable_optimization
        self._initialize_plugin()
        
    def _initialize_plugin(self):
        """初始化渲染插件"""
        try:
            file_path = self.book.file.path
            book_format = self.book.format
            
            self.renderer_plugin = plugin_manager.create_renderer(file_path, book_format)
            
            if self.renderer_plugin:
                # 执行预处理
                if not self.renderer_plugin.preprocess():
                    logger.error(f"插件预处理失败: {book_format}")
                    self.renderer_plugin = None
                else:
                    # 创建优化包装器
                    if self.enable_optimization:
                        self.optimized_renderer = create_optimized_renderer(
                            self.renderer_plugin, self.book.id
                        )
                        # 启用预加载
                        self.optimized_renderer.enable_preload(True)
            else:
                logger.warning(f"未找到支持格式 {book_format} 的插件")
                
        except Exception as e:
            logger.error(f"渲染插件初始化失败: {str(e)}")
            self.renderer_plugin = None
            
    @performance_monitor("enhanced_render_chapter")
    def render_chapter(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染指定章节（带性能优化）"""
        if not self.renderer_plugin:
            return {'error': '渲染插件未初始化'}
            
        try:
            # 使用优化渲染器或原始渲染器
            if self.optimized_renderer:
                result = self.optimized_renderer.render_chapter(chapter_number, page_number)
            else:
                result = self.renderer_plugin.render(chapter_number, page_number)
            
            # 添加书籍信息
            result.update({
                'book_id': self.book.id,
                'book_title': self.book.title,
                'book_author': self.book.author,
                'book_format': self.book.format,
                'plugin_info': self.renderer_plugin.get_plugin_info(),
                'optimized': self.enable_optimization,
                'from_cache': result.get('_from_cache', False)
            })
            if 'render_engine' not in result:
                result['render_engine'] = self.renderer_plugin.get_plugin_info().get('render_engine', 'default')
            
            return result
            
        except Exception as e:
            logger.error(f"章节渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
            
    def get_book_metadata(self) -> Dict[str, Any]:
        """获取书籍元数据"""
        if not self.renderer_plugin:
            return {}
            
        try:
            return self.renderer_plugin.get_metadata()
        except Exception as e:
            logger.error(f"元数据获取失败: {str(e)}")
            return {}
            
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取目录"""
        if not self.renderer_plugin:
            return []
            
        try:
            return self.renderer_plugin.get_table_of_contents()
        except Exception as e:
            logger.error(f"目录获取失败: {str(e)}")
            return []
            
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if self.optimized_renderer:
            return self.optimized_renderer.get_performance_stats()
        return {}
        
    def clear_cache(self) -> int:
        """清理缓存"""
        if self.enable_optimization:
            from .performance_optimizer import clear_book_cache
            return clear_book_cache(self.book.id)
        return 0
            
    def cleanup(self):
        """清理资源"""
        if self.optimized_renderer:
            self.optimized_renderer.cleanup()
        elif self.renderer_plugin:
            self.renderer_plugin.cleanup()
