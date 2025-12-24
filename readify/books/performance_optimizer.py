"""
书籍渲染性能优化模块
提供缓存、预加载、懒加载等性能优化功能
"""

import os
import json
import time
import hashlib
import threading
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


class RenderCache:
    """渲染结果缓存管理器"""
    
    def __init__(self, cache_prefix: str = "book_render"):
        self.cache_prefix = cache_prefix
        self.default_timeout = getattr(settings, 'BOOK_RENDER_CACHE_TIMEOUT', 3600)  # 1小时
        
    def _make_cache_key(self, book_id: int, chapter_number: int, page_number: int, 
                       renderer_version: str = "1.0") -> str:
        """生成缓存键"""
        key_data = f"{book_id}:{chapter_number}:{page_number}:{renderer_version}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{self.cache_prefix}:{key_hash}"
        
    def get(self, book_id: int, chapter_number: int, page_number: int, 
            renderer_version: str = "1.0") -> Optional[Dict[str, Any]]:
        """获取缓存的渲染结果"""
        try:
            cache_key = self._make_cache_key(book_id, chapter_number, page_number, renderer_version)
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.debug(f"缓存命中: {cache_key}")
                # 添加缓存标记
                cached_data['_from_cache'] = True
                cached_data['_cache_time'] = time.time()
                return cached_data
                
        except Exception as e:
            logger.error(f"获取缓存失败: {str(e)}")
            
        return None
        
    def set(self, book_id: int, chapter_number: int, page_number: int, 
            render_result: Dict[str, Any], renderer_version: str = "1.0", 
            timeout: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            cache_key = self._make_cache_key(book_id, chapter_number, page_number, renderer_version)
            
            # 添加元数据
            cache_data = render_result.copy()
            cache_data['_cached_at'] = timezone.now().isoformat()
            cache_data['_cache_key'] = cache_key
            
            cache_timeout = timeout or self.default_timeout
            cache.set(cache_key, cache_data, cache_timeout)
            
            logger.debug(f"缓存设置成功: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败: {str(e)}")
            return False
            
    def invalidate(self, book_id: int, chapter_number: Optional[int] = None) -> int:
        """失效缓存"""
        try:
            if chapter_number is not None:
                # 失效特定章节的所有页面缓存
                for page in range(1, 100):  # 假设最多99页
                    cache_key = self._make_cache_key(book_id, chapter_number, page)
                    cache.delete(cache_key)
                return 1
            else:
                # 失效整本书的缓存（较重的操作）
                # 这里简化处理，实际可以维护一个书籍-缓存键的映射表
                count = 0
                for chapter in range(1, 1000):  # 假设最多999章
                    for page in range(1, 100):
                        cache_key = self._make_cache_key(book_id, chapter, page)
                        if cache.get(cache_key):
                            cache.delete(cache_key)
                            count += 1
                return count
                
        except Exception as e:
            logger.error(f"缓存失效失败: {str(e)}")
            return 0
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            # 这里简化处理，实际实现需要根据缓存后端的API
            return {
                'cache_backend': cache.__class__.__name__,
                'cache_timeout': self.default_timeout,
                'cache_prefix': self.cache_prefix
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return {}


class PreloadManager:
    """预加载管理器"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.preload_tasks = {}
        
    def preload_chapters(self, renderer, book_id: int, current_chapter: int, 
                        preload_count: int = 2) -> Dict[str, Any]:
        """预加载相邻章节"""
        preload_results = {}
        futures = []
        
        # 预加载下几章
        for i in range(1, preload_count + 1):
            next_chapter = current_chapter + i
            future = self.executor.submit(
                self._safe_render_chapter, 
                renderer, book_id, next_chapter, 1
            )
            futures.append((f"chapter_{next_chapter}", future))
            
        # 预加载上几章（如果有）
        for i in range(1, min(preload_count + 1, current_chapter)):
            prev_chapter = current_chapter - i
            future = self.executor.submit(
                self._safe_render_chapter, 
                renderer, book_id, prev_chapter, 1
            )
            futures.append((f"chapter_{prev_chapter}", future))
            
        # 收集结果
        for name, future in futures:
            try:
                result = future.result(timeout=10)  # 10秒超时
                if result and not result.get('error'):
                    preload_results[name] = result
                    logger.debug(f"预加载成功: {name}")
            except Exception as e:
                logger.warning(f"预加载失败 {name}: {str(e)}")
                
        return preload_results
        
    def _safe_render_chapter(self, renderer, book_id: int, chapter_number: int, 
                           page_number: int) -> Optional[Dict[str, Any]]:
        """安全的章节渲染"""
        try:
            # 检查缓存
            cached_result = render_cache.get(book_id, chapter_number, page_number)
            if cached_result:
                return cached_result
                
            # 渲染
            result = renderer.render_chapter(chapter_number, page_number)
            
            # 缓存结果
            if result and not result.get('error'):
                render_cache.set(book_id, chapter_number, page_number, result)
                
            return result
            
        except Exception as e:
            logger.error(f"安全渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
            
    def cancel_preload_tasks(self, book_id: int):
        """取消预加载任务"""
        if book_id in self.preload_tasks:
            for future in self.preload_tasks[book_id]:
                future.cancel()
            del self.preload_tasks[book_id]
            
    def shutdown(self):
        """关闭预加载管理器"""
        self.executor.shutdown(wait=True)


class LazyLoader:
    """懒加载管理器"""
    
    def __init__(self):
        self.loaded_resources = set()
        self.loading_queue = []
        
    def should_load_images(self, content: str) -> bool:
        """判断是否需要加载图片"""
        return '<img' in content and 'data-lazy' not in content
        
    def process_lazy_images(self, content: str, base_path: str) -> str:
        """处理懒加载图片"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(content, 'html.parser')
            images = soup.find_all('img')
            
            for img in images:
                src = img.get('src')
                if src and not src.startswith(('http://', 'https://', 'data:')):
                    # 转换为懒加载
                    img['data-lazy-src'] = src
                    img['src'] = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMSIgaGVpZ2h0PSIxIiB2aWV3Qm94PSIwIDAgMSAxIiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxyZWN0IHdpZHRoPSIxIiBoZWlnaHQ9IjEiIGZpbGw9IiNGNUY1RjUiLz48L3N2Zz4='
                    img['data-lazy'] = 'true'
                    img['class'] = img.get('class', []) + ['lazy-image']
                    
            return str(soup)
            
        except Exception as e:
            logger.error(f"懒加载图片处理失败: {str(e)}")
            return content
            
    def get_lazy_load_script(self) -> str:
        """获取懒加载脚本"""
        return """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const lazyImages = document.querySelectorAll('img[data-lazy="true"]');
            
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const image = entry.target;
                            const src = image.getAttribute('data-lazy-src');
                            if (src) {
                                image.src = src;
                                image.removeAttribute('data-lazy-src');
                                image.removeAttribute('data-lazy');
                                image.classList.remove('lazy-image');
                            }
                            observer.unobserve(image);
                        }
                    });
                });
                
                lazyImages.forEach(image => {
                    imageObserver.observe(image);
                });
            } else {
                // 备用方案：直接加载所有图片
                lazyImages.forEach(image => {
                    const src = image.getAttribute('data-lazy-src');
                    if (src) {
                        image.src = src;
                    }
                });
            }
        });
        </script>
        """


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        
    def start_timing(self, operation_name: str, context: Dict[str, Any] = None):
        """开始计时"""
        self.start_times[operation_name] = {
            'start_time': time.time(),
            'context': context or {}
        }
        
    def end_timing(self, operation_name: str) -> float:
        """结束计时并返回耗时"""
        if operation_name not in self.start_times:
            return 0.0
            
        start_info = self.start_times[operation_name]
        duration = time.time() - start_info['start_time']
        
        # 记录指标
        if operation_name not in self.metrics:
            self.metrics[operation_name] = []
            
        self.metrics[operation_name].append({
            'duration': duration,
            'timestamp': time.time(),
            'context': start_info['context']
        })
        
        # 清理开始时间
        del self.start_times[operation_name]
        
        logger.debug(f"操作耗时 {operation_name}: {duration:.3f}s")
        return duration
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = {}
        
        for operation, measurements in self.metrics.items():
            if measurements:
                durations = [m['duration'] for m in measurements]
                stats[operation] = {
                    'count': len(durations),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'total_duration': sum(durations)
                }
                
        return stats
        
    def clear_metrics(self):
        """清理性能指标"""
        self.metrics.clear()
        self.start_times.clear()


def performance_monitor(operation_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            
            monitor.start_timing(name, {
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            })
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.end_timing(name)
                
        return wrapper
    return decorator


class OptimizedRenderer:
    """优化的渲染器包装器"""
    
    def __init__(self, base_renderer, book_id: int):
        self.base_renderer = base_renderer
        self.book_id = book_id
        self.performance_monitor = PerformanceMonitor()
        
    @performance_monitor("render_chapter")
    def render_chapter(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """优化的章节渲染"""
        # 1. 检查缓存
        cached_result = render_cache.get(
            self.book_id, chapter_number, page_number, 
            getattr(self.base_renderer, 'plugin_version', '1.0')
        )
        
        if cached_result:
            logger.info(f"使用缓存结果: 书籍{self.book_id} 章节{chapter_number} 页{page_number}")
            return cached_result
            
        # 2. 渲染内容
        self.performance_monitor.start_timing('actual_render')
        try:
            result = self.base_renderer.render_chapter(chapter_number, page_number)
        finally:
            self.performance_monitor.end_timing('actual_render')
            
        # 3. 优化内容
        if result and not result.get('error'):
            result = self._optimize_content(result)
            
            # 4. 缓存结果
            render_cache.set(
                self.book_id, chapter_number, page_number, result,
                getattr(self.base_renderer, 'plugin_version', '1.0')
            )
            
        # 5. 启动预加载
        if hasattr(self, '_preload_enabled') and self._preload_enabled:
            self._start_preload(chapter_number)
            
        return result
        
    def _optimize_content(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """优化内容"""
        if 'content' in result:
            # 懒加载图片
            result['content'] = lazy_loader.process_lazy_images(
                result['content'], 
                getattr(self.base_renderer, 'temp_dir', '')
            )
            
            # 添加懒加载脚本
            if lazy_loader.should_load_images(result['content']):
                result['lazy_load_script'] = lazy_loader.get_lazy_load_script()
                
        return result
        
    def _start_preload(self, current_chapter: int):
        """启动预加载"""
        try:
            preload_manager.preload_chapters(
                self.base_renderer, self.book_id, current_chapter
            )
        except Exception as e:
            logger.warning(f"预加载失败: {str(e)}")
            
    def enable_preload(self, enabled: bool = True):
        """启用/禁用预加载"""
        self._preload_enabled = enabled
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_monitor.get_performance_stats()
        
    def cleanup(self):
        """清理资源"""
        if hasattr(self.base_renderer, 'cleanup'):
            self.base_renderer.cleanup()
        self.performance_monitor.clear_metrics()


# 全局实例
render_cache = RenderCache()
preload_manager = PreloadManager()
lazy_loader = LazyLoader()
monitor = PerformanceMonitor()


def create_optimized_renderer(base_renderer, book_id: int) -> OptimizedRenderer:
    """创建优化的渲染器"""
    return OptimizedRenderer(base_renderer, book_id)


def clear_book_cache(book_id: int) -> int:
    """清理指定书籍的缓存"""
    return render_cache.invalidate(book_id)


def get_global_performance_stats() -> Dict[str, Any]:
    """获取全局性能统计"""
    return {
        'monitor_stats': monitor.get_performance_stats(),
        'cache_stats': render_cache.get_cache_stats(),
        'preload_manager': {
            'max_workers': preload_manager.max_workers,
            'active_tasks': len(preload_manager.preload_tasks)
        }
    }