"""
书籍格式检测器
自动检测上传文件的书籍格式，支持多种检测方式
"""

import os
import mimetypes
import zipfile
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BookFormatDetector:
    """书籍格式检测器"""
    
    # 支持的格式及其MIME类型映射
    MIME_TYPE_MAP = {
        'application/epub+zip': 'epub',
        'application/pdf': 'pdf',
        'application/x-mobipocket-ebook': 'mobi',
        'application/vnd.amazon.ebook': 'azw3',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'text/plain': 'txt',
        'text/html': 'html',
        'text/markdown': 'markdown',
        'application/xml': 'fb2',
        'text/xml': 'fb2',
    }
    
    # 文件扩展名映射
    EXTENSION_MAP = {
        '.epub': 'epub',
        '.pdf': 'pdf',
        '.mobi': 'mobi',
        '.azw': 'azw3',
        '.azw3': 'azw3',
        '.fb2': 'fb2',
        '.txt': 'txt',
        '.html': 'html',
        '.htm': 'html',
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.rtf': 'rtf',
        '.doc': 'doc',
        '.docx': 'docx',
    }
    
    # 文件头魔数检测
    MAGIC_NUMBERS = {
        b'PK\x03\x04': 'zip_based',  # ZIP格式（可能是EPUB）
        b'%PDF': 'pdf',
        b'TPZ': 'mobi',
        b'BOOKMOBI': 'mobi',
        b'\x1f\x8b': 'gzip',
        b'<?xml': 'xml_based',
    }
    
    def __init__(self):
        self.magic_detector = None
        self._init_magic_detector()
        
    def _init_magic_detector(self):
        """初始化magic检测器"""
        try:
            import magic
            self.magic_detector = magic.Magic(mime=True)
            logger.info("初始化python-magic检测器成功")
        except ImportError:
            logger.warning("python-magic未安装，将使用基础检测方法")
        except Exception as e:
            logger.warning(f"初始化magic检测器失败: {str(e)}")
            
    def detect_format(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        检测书籍格式
        返回: (格式名称, 检测详情)
        """
        detection_info = {
            'file_path': file_path,
            'file_size': 0,
            'extension_detected': None,
            'mime_detected': None,
            'magic_detected': None,
            'content_detected': None,
            'confidence': 0.0,
            'detection_methods': []
        }
        
        if not os.path.exists(file_path):
            return 'unknown', detection_info
            
        detection_info['file_size'] = os.path.getsize(file_path)
        
        # 方法1: 扩展名检测
        ext_format = self._detect_by_extension(file_path)
        if ext_format:
            detection_info['extension_detected'] = ext_format
            detection_info['detection_methods'].append('extension')
            
        # 方法2: MIME类型检测
        mime_format = self._detect_by_mime_type(file_path)
        if mime_format:
            detection_info['mime_detected'] = mime_format
            detection_info['detection_methods'].append('mime')
            
        # 方法3: 文件头魔数检测
        magic_format = self._detect_by_magic_number(file_path)
        if magic_format:
            detection_info['magic_detected'] = magic_format
            detection_info['detection_methods'].append('magic')
            
        # 方法4: 内容分析检测
        content_format = self._detect_by_content_analysis(file_path)
        if content_format:
            detection_info['content_detected'] = content_format
            detection_info['detection_methods'].append('content')
            
        # 综合判断最终格式
        final_format, confidence = self._determine_final_format(detection_info)
        detection_info['confidence'] = confidence
        
        logger.info(f"文件格式检测完成: {file_path} -> {final_format} (置信度: {confidence:.2f})")
        
        return final_format, detection_info
        
    def _detect_by_extension(self, file_path: str) -> Optional[str]:
        """通过文件扩展名检测"""
        try:
            extension = Path(file_path).suffix.lower()
            return self.EXTENSION_MAP.get(extension)
        except Exception as e:
            logger.error(f"扩展名检测失败: {str(e)}")
            return None
            
    def _detect_by_mime_type(self, file_path: str) -> Optional[str]:
        """通过MIME类型检测"""
        try:
            # 优先使用python-magic
            if self.magic_detector:
                mime_type = self.magic_detector.from_file(file_path)
                return self.MIME_TYPE_MAP.get(mime_type)
            
            # 备选方案：使用mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                return self.MIME_TYPE_MAP.get(mime_type)
                
        except Exception as e:
            logger.error(f"MIME类型检测失败: {str(e)}")
            
        return None
        
    def _detect_by_magic_number(self, file_path: str) -> Optional[str]:
        """通过文件头魔数检测"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # 读取前16字节
                
            for magic_bytes, format_type in self.MAGIC_NUMBERS.items():
                if header.startswith(magic_bytes):
                    if format_type == 'zip_based':
                        # 进一步检测ZIP格式的具体类型
                        return self._detect_zip_based_format(file_path)
                    elif format_type == 'xml_based':
                        # 进一步检测XML格式的具体类型
                        return self._detect_xml_based_format(file_path)
                    else:
                        return format_type
                        
        except Exception as e:
            logger.error(f"魔数检测失败: {str(e)}")
            
        return None
        
    def _detect_zip_based_format(self, file_path: str) -> Optional[str]:
        """检测ZIP格式的具体类型（EPUB等）"""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                file_list = zip_file.namelist()
                
                # 检查是否为EPUB
                if 'META-INF/container.xml' in file_list:
                    return 'epub'
                    
                # 检查是否为其他ZIP格式的电子书
                if any(f.endswith('.opf') for f in file_list):
                    return 'epub'
                    
        except Exception as e:
            logger.error(f"ZIP格式检测失败: {str(e)}")
            
        return 'zip'
        
    def _detect_xml_based_format(self, file_path: str) -> Optional[str]:
        """检测XML格式的具体类型（FB2等）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # 读取前1024字符
                
                # 检查是否为FB2
                if 'http://www.gribuser.ru/xml/fictionbook' in content:
                    return 'fb2'
                    
                # 检查是否为HTML
                if '<html' in content.lower() or '<body' in content.lower():
                    return 'html'
                    
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read(1024)
                    if 'http://www.gribuser.ru/xml/fictionbook' in content:
                        return 'fb2'
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"XML格式检测失败: {str(e)}")
            
        return 'xml'
        
    def _detect_by_content_analysis(self, file_path: str) -> Optional[str]:
        """通过内容分析检测"""
        try:
            file_size = os.path.getsize(file_path)
            
            # 对于小文件，尝试读取内容分析
            if file_size < 1024 * 1024:  # 小于1MB
                return self._analyze_small_file_content(file_path)
            else:
                return self._analyze_large_file_sample(file_path)
                
        except Exception as e:
            logger.error(f"内容分析失败: {str(e)}")
            
        return None
        
    def _analyze_small_file_content(self, file_path: str) -> Optional[str]:
        """分析小文件的完整内容"""
        try:
            # 尝试以文本方式读取
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
                    
            if content:
                # 分析文本特征
                content_lower = content.lower()
                
                # Markdown特征
                if ('# ' in content or '## ' in content or 
                    '```' in content or '**' in content):
                    return 'markdown'
                    
                # HTML特征
                if ('<html' in content_lower or '<body' in content_lower or
                    '<div' in content_lower or '<p>' in content_lower):
                    return 'html'
                    
                # FB2特征
                if 'fictionbook' in content_lower:
                    return 'fb2'
                    
                # 纯文本（默认）
                return 'txt'
                
        except Exception as e:
            logger.error(f"小文件内容分析失败: {str(e)}")
            
        return None
        
    def _analyze_large_file_sample(self, file_path: str) -> Optional[str]:
        """分析大文件的样本内容"""
        try:
            # 读取文件开头和结尾的样本
            sample_size = 4096
            
            with open(file_path, 'rb') as f:
                header_sample = f.read(sample_size)
                f.seek(-sample_size, 2)  # 移动到文件末尾
                footer_sample = f.read(sample_size)
                
            # 尝试解码样本
            sample_text = ""
            for sample in [header_sample, footer_sample]:
                for encoding in ['utf-8', 'gbk', 'latin-1']:
                    try:
                        sample_text += sample.decode(encoding, errors='ignore')
                        break
                    except:
                        continue
                        
            if sample_text:
                sample_lower = sample_text.lower()
                
                # PDF特征
                if '%pdf' in sample_lower or 'endobj' in sample_lower:
                    return 'pdf'
                    
                # EPUB特征
                if 'epub' in sample_lower or 'container.xml' in sample_lower:
                    return 'epub'
                    
                # HTML特征
                if '<html' in sample_lower or '</html>' in sample_lower:
                    return 'html'
                    
        except Exception as e:
            logger.error(f"大文件样本分析失败: {str(e)}")
            
        return None
        
    def _determine_final_format(self, detection_info: Dict[str, Any]) -> Tuple[str, float]:
        """综合判断最终格式"""
        formats = []
        weights = {
            'extension_detected': 0.3,
            'mime_detected': 0.4,
            'magic_detected': 0.5,
            'content_detected': 0.6
        }
        
        # 收集所有检测到的格式
        for key, weight in weights.items():
            format_type = detection_info.get(key)
            if format_type and format_type != 'unknown':
                formats.append((format_type, weight))
                
        if not formats:
            return 'unknown', 0.0
            
        # 统计各格式的权重
        format_scores = {}
        for format_type, weight in formats:
            format_scores[format_type] = format_scores.get(format_type, 0) + weight
            
        # 选择得分最高的格式
        best_format = max(format_scores.items(), key=lambda x: x[1])
        
        # 计算置信度
        total_weight = sum(weights.values())
        confidence = best_format[1] / total_weight
        
        return best_format[0], confidence
        
    def get_format_info(self, format_name: str) -> Dict[str, Any]:
        """获取格式信息"""
        format_info = {
            'epub': {
                'name': 'EPUB',
                'description': 'Electronic Publication - 标准电子书格式',
                'extensions': ['.epub'],
                'mime_types': ['application/epub+zip'],
                'features': ['章节导航', '字体调节', '书签', '搜索'],
                'reader_support': 'excellent'
            },
            'pdf': {
                'name': 'PDF',
                'description': 'Portable Document Format - 便携式文档格式',
                'extensions': ['.pdf'],
                'mime_types': ['application/pdf'],
                'features': ['固定布局', '高保真', '图文混排'],
                'reader_support': 'excellent'
            },
            'mobi': {
                'name': 'MOBI',
                'description': 'Mobipocket - Amazon Kindle格式',
                'extensions': ['.mobi'],
                'mime_types': ['application/x-mobipocket-ebook'],
                'features': ['章节导航', '字体调节', 'DRM保护'],
                'reader_support': 'good'
            },
            'azw3': {
                'name': 'AZW3',
                'description': 'Amazon Kindle Format 8',
                'extensions': ['.azw3', '.azw'],
                'mime_types': ['application/vnd.amazon.ebook'],
                'features': ['增强排版', '多媒体支持', 'DRM保护'],
                'reader_support': 'good'
            },
            'fb2': {
                'name': 'FB2',
                'description': 'FictionBook 2.0 - 俄罗斯电子书格式',
                'extensions': ['.fb2'],
                'mime_types': ['application/xml', 'text/xml'],
                'features': ['结构化内容', '元数据丰富', '开放格式'],
                'reader_support': 'limited'
            },
            'txt': {
                'name': 'TXT',
                'description': '纯文本格式',
                'extensions': ['.txt'],
                'mime_types': ['text/plain'],
                'features': ['简单', '通用', '小文件'],
                'reader_support': 'excellent'
            },
            'html': {
                'name': 'HTML',
                'description': 'HyperText Markup Language',
                'extensions': ['.html', '.htm'],
                'mime_types': ['text/html'],
                'features': ['网页格式', '样式支持', '链接'],
                'reader_support': 'excellent'
            },
            'markdown': {
                'name': 'Markdown',
                'description': '轻量级标记语言',
                'extensions': ['.md', '.markdown'],
                'mime_types': ['text/markdown'],
                'features': ['易编写', '格式简单', '广泛支持'],
                'reader_support': 'good'
            },
            'docx': {
                'name': 'DOCX',
                'description': 'Microsoft Word 文档格式',
                'extensions': ['.docx'],
                'mime_types': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                'features': ['段落样式', '表格', '图片'],
                'reader_support': 'good'
            },
            'doc': {
                'name': 'DOC',
                'description': 'Microsoft Word 旧版文档格式',
                'extensions': ['.doc'],
                'mime_types': ['application/msword'],
                'features': ['基础排版', '文本内容'],
                'reader_support': 'limited'
            }
        }
        
        return format_info.get(format_name, {
            'name': format_name.upper(),
            'description': '未知格式',
            'extensions': [],
            'mime_types': [],
            'features': [],
            'reader_support': 'unknown'
        })
        
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        formats = set()
        formats.update(self.EXTENSION_MAP.values())
        formats.update(self.MIME_TYPE_MAP.values())
        return sorted(list(formats))
        
    def validate_format(self, file_path: str, expected_format: str) -> bool:
        """验证文件是否为指定格式"""
        detected_format, detection_info = self.detect_format(file_path)
        return detected_format == expected_format.lower()


# 全局格式检测器实例
format_detector = BookFormatDetector()
