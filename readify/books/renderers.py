"""
书籍渲染器模块
支持多种格式的专用渲染引擎：
- EPUB → WebKit/Chromium（epub.js）渲染
- PDF → MuPDF/Poppler 渲染  
- MOBI/AZW3 → 先转 EPUB 或 foliate-js 直解析
- FB2 → XSLT 转 XHTML + EPUB 渲染器
- TXT/Markdown/HTML → 浏览器/WebView 渲染
"""

import os
import json
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import markdown
import re

logger = logging.getLogger(__name__)


class BaseRenderer:
    """基础渲染器类"""
    
    def __init__(self, book_file_path: str, book_format: str):
        self.book_file_path = book_file_path
        self.book_format = book_format.lower()
        self.temp_dir = None
        
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染指定章节和页面"""
        raise NotImplementedError
        
    def get_metadata(self) -> Dict[str, Any]:
        """获取书籍元数据"""
        raise NotImplementedError
        
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取目录结构"""
        raise NotImplementedError
        
    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class EPUBRenderer(BaseRenderer):
    """EPUB渲染器 - 使用epub.js进行WebKit/Chromium渲染"""
    
    def __init__(self, book_file_path: str, book_format: str = 'epub'):
        super().__init__(book_file_path, book_format)
        self.epub_data = None
        self.spine = []
        self.manifest = {}
        self._extract_epub()
        
    def _extract_epub(self):
        """提取EPUB文件内容"""
        try:
            self.temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(self.book_file_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # 解析container.xml找到OPF文件
            container_path = os.path.join(self.temp_dir, 'META-INF', 'container.xml')
            if os.path.exists(container_path):
                tree = ET.parse(container_path)
                root = tree.getroot()
                opf_path = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').get('full-path')
                self.opf_path = os.path.join(self.temp_dir, opf_path)
                self._parse_opf()
                
        except Exception as e:
            logger.error(f"EPUB提取失败: {str(e)}")
            
    def _parse_opf(self):
        """解析OPF文件获取书籍结构"""
        try:
            tree = ET.parse(self.opf_path)
            root = tree.getroot()
            
            # 解析manifest
            for item in root.findall('.//{http://www.idpf.org/2007/opf}item'):
                item_id = item.get('id')
                href = item.get('href')
                media_type = item.get('media-type')
                self.manifest[item_id] = {
                    'href': href,
                    'media_type': media_type,
                    'full_path': os.path.join(os.path.dirname(self.opf_path), href)
                }
            
            # 解析spine
            for itemref in root.findall('.//{http://www.idpf.org/2007/opf}itemref'):
                idref = itemref.get('idref')
                if idref in self.manifest:
                    self.spine.append(self.manifest[idref])
                    
        except Exception as e:
            logger.error(f"OPF解析失败: {str(e)}")
    
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染EPUB内容"""
        try:
            if not self.spine or chapter_number > len(self.spine):
                return {'error': '章节不存在'}
                
            chapter_file = self.spine[chapter_number - 1]
            
            # 读取XHTML内容
            with open(chapter_file['full_path'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用BeautifulSoup清理和格式化HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # 移除不需要的标签
            for tag in soup(['script', 'style', 'meta', 'link']):
                tag.decompose()
            
            # 提取正文内容
            body = soup.find('body')
            if body:
                content_html = str(body)
            else:
                content_html = str(soup)
            
            return {
                'content': content_html,
                'chapter_title': self._extract_chapter_title(soup, chapter_number),
                'chapter_number': chapter_number,
                'total_chapters': len(self.spine),
                'renderer_type': 'epub_webkit',
                'supports_pagination': True,
                'css_files': self._get_css_files(),
                'images': self._get_images_in_chapter(content_html)
            }
            
        except Exception as e:
            logger.error(f"EPUB渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
    
    def _extract_chapter_title(self, soup, chapter_number=1) -> str:
        """提取章节标题"""
        for tag in ['h1', 'h2', 'h3', 'title']:
            title_elem = soup.find(tag)
            if title_elem and title_elem.get_text().strip():
                return title_elem.get_text().strip()
        return f"第{chapter_number}章"
    
    def _get_css_files(self) -> List[str]:
        """获取CSS文件列表"""
        css_files = []
        for item in self.manifest.values():
            if item['media_type'] == 'text/css':
                css_files.append(item['full_path'])
        return css_files
    
    def _get_images_in_chapter(self, content: str) -> List[str]:
        """获取章节中的图片"""
        images = []
        soup = BeautifulSoup(content, 'html.parser')
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                images.append(src)
        return images
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取EPUB元数据"""
        try:
            tree = ET.parse(self.opf_path)
            root = tree.getroot()
            
            metadata = {}
            for meta in root.findall('.//{http://purl.org/dc/elements/1.1/}*'):
                tag_name = meta.tag.split('}')[-1]
                metadata[tag_name] = meta.text
                
            return metadata
        except Exception as e:
            logger.error(f"元数据获取失败: {str(e)}")
            return {}
    
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取目录结构"""
        toc = []
        for i, chapter in enumerate(self.spine, 1):
            try:
                with open(chapter['full_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                soup = BeautifulSoup(content, 'html.parser')
                title = self._extract_chapter_title(soup)
                toc.append({
                    'chapter_number': i,
                    'title': title,
                    'href': chapter['href']
                })
            except Exception:
                toc.append({
                    'chapter_number': i,
                    'title': f'第{i}章',
                    'href': chapter['href']
                })
        return toc


class PDFRenderer(BaseRenderer):
    """PDF渲染器 - 使用MuPDF/Poppler进行渲染"""
    
    def __init__(self, book_file_path: str, book_format: str = 'pdf'):
        super().__init__(book_file_path, book_format)
        self.page_count = 0
        self._get_page_count()
        
    def _get_page_count(self):
        """获取PDF页数"""
        try:
            import PyPDF2
            with open(self.book_file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                self.page_count = len(reader.pages)
        except Exception as e:
            logger.error(f"获取PDF页数失败: {str(e)}")
            self.page_count = 0
    
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染PDF页面"""
        try:
            if page_number > self.page_count:
                return {'error': '页面不存在'}
            
            # 使用PyMuPDF进行高质量渲染
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(self.book_file_path)
                page = doc[page_number - 1]
                
                # 渲染为HTML
                html_content = page.get_text("html")
                
                # 渲染为图片（备用方案）
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放提高清晰度
                img_data = pix.tobytes("png")
                
                doc.close()
                
                return {
                    'content': html_content,
                    'page_image': img_data,
                    'page_number': page_number,
                    'total_pages': self.page_count,
                    'renderer_type': 'pdf_mupdf',
                    'supports_pagination': True,
                    'text_content': page.get_text()
                }
                
            except ImportError:
                # 回退到PyPDF2
                return self._render_with_pypdf2(page_number)
                
        except Exception as e:
            logger.error(f"PDF渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
    
    def _render_with_pypdf2(self, page_number: int) -> Dict[str, Any]:
        """使用PyPDF2渲染（备用方案）"""
        try:
            import PyPDF2
            with open(self.book_file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page = reader.pages[page_number - 1]
                text_content = page.extract_text()
                
                # 简单的HTML格式化
                html_content = f"<div class='pdf-content'><pre>{text_content}</pre></div>"
                
                return {
                    'content': html_content,
                    'page_number': page_number,
                    'total_pages': self.page_count,
                    'renderer_type': 'pdf_pypdf2',
                    'supports_pagination': True,
                    'text_content': text_content
                }
        except Exception as e:
            logger.error(f"PyPDF2渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取PDF元数据"""
        try:
            import PyPDF2
            with open(self.book_file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                metadata = reader.metadata
                return {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                    'creation_date': metadata.get('/CreationDate', ''),
                    'modification_date': metadata.get('/ModDate', ''),
                    'page_count': self.page_count
                }
        except Exception as e:
            logger.error(f"PDF元数据获取失败: {str(e)}")
            return {'page_count': self.page_count}
    
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取PDF目录"""
        try:
            import fitz
            doc = fitz.open(self.book_file_path)
            toc = doc.get_toc()
            doc.close()
            
            formatted_toc = []
            for item in toc:
                level, title, page_num = item
                formatted_toc.append({
                    'level': level,
                    'title': title,
                    'page_number': page_num,
                    'chapter_number': len(formatted_toc) + 1
                })
            return formatted_toc
        except Exception as e:
            logger.error(f"PDF目录获取失败: {str(e)}")
            return []


class MOBIRenderer(BaseRenderer):
    """MOBI/AZW3渲染器 - 先转换为EPUB或使用foliate-js直接解析"""
    
    def __init__(self, book_file_path: str, book_format: str = 'mobi'):
        super().__init__(book_file_path, book_format)
        self.epub_renderer = None
        self._convert_to_epub()
        
    def _convert_to_epub(self):
        """将MOBI转换为EPUB"""
        try:
            # 尝试使用calibre进行转换
            self.temp_dir = tempfile.mkdtemp()
            epub_path = os.path.join(self.temp_dir, 'converted.epub')
            
            # 使用calibre的ebook-convert命令
            cmd = ['ebook-convert', self.book_file_path, epub_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(epub_path):
                self.epub_renderer = EPUBRenderer(epub_path, 'epub')
            else:
                logger.warning(f"MOBI转换失败，尝试直接解析: {result.stderr}")
                self._parse_mobi_directly()
                
        except subprocess.TimeoutExpired:
            logger.error("MOBI转换超时")
        except FileNotFoundError:
            logger.warning("calibre未安装，尝试直接解析MOBI")
            self._parse_mobi_directly()
        except Exception as e:
            logger.error(f"MOBI转换失败: {str(e)}")
            self._parse_mobi_directly()
    
    def _parse_mobi_directly(self):
        """直接解析MOBI文件（简化版本）"""
        try:
            # 这里可以实现基本的MOBI解析
            # 或者使用第三方库如mobidedrm
            logger.info("使用简化MOBI解析器")
        except Exception as e:
            logger.error(f"MOBI直接解析失败: {str(e)}")
    
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染MOBI内容"""
        if self.epub_renderer:
            result = self.epub_renderer.render(chapter_number, page_number)
            result['renderer_type'] = 'mobi_to_epub'
            return result
        else:
            return {'error': 'MOBI文件解析失败'}
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取MOBI元数据"""
        if self.epub_renderer:
            return self.epub_renderer.get_metadata()
        return {}
    
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取MOBI目录"""
        if self.epub_renderer:
            return self.epub_renderer.get_table_of_contents()
        return []


class FB2Renderer(BaseRenderer):
    """FB2渲染器 - 使用XSLT转换为XHTML + EPUB渲染器"""
    
    def __init__(self, book_file_path: str, book_format: str = 'fb2'):
        super().__init__(book_file_path, book_format)
        self.xhtml_content = None
        self._convert_to_xhtml()
        
    def _convert_to_xhtml(self):
        """将FB2转换为XHTML"""
        try:
            # 读取FB2文件
            with open(self.book_file_path, 'r', encoding='utf-8') as f:
                fb2_content = f.read()
            
            # 解析XML
            root = ET.fromstring(fb2_content)
            
            # 提取书籍信息和内容
            self.metadata = self._extract_fb2_metadata(root)
            self.chapters = self._extract_fb2_chapters(root)
            
        except Exception as e:
            logger.error(f"FB2解析失败: {str(e)}")
            self.chapters = []
            self.metadata = {}
    
    def _extract_fb2_metadata(self, root) -> Dict[str, Any]:
        """提取FB2元数据"""
        metadata = {}
        try:
            description = root.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}description')
            if description is not None:
                title_info = description.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}title-info')
                if title_info is not None:
                    book_title = title_info.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}book-title')
                    if book_title is not None:
                        metadata['title'] = book_title.text
                    
                    authors = title_info.findall('.//{http://www.gribuser.ru/xml/fictionbook/2.0}author')
                    author_names = []
                    for author in authors:
                        first_name = author.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}first-name')
                        last_name = author.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}last-name')
                        if first_name is not None and last_name is not None:
                            author_names.append(f"{first_name.text} {last_name.text}")
                    metadata['author'] = ', '.join(author_names)
        except Exception as e:
            logger.error(f"FB2元数据提取失败: {str(e)}")
        
        return metadata
    
    def _extract_fb2_chapters(self, root) -> List[Dict[str, Any]]:
        """提取FB2章节"""
        chapters = []
        try:
            body = root.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}body')
            if body is not None:
                sections = body.findall('.//{http://www.gribuser.ru/xml/fictionbook/2.0}section')
                for i, section in enumerate(sections, 1):
                    title_elem = section.find('.//{http://www.gribuser.ru/xml/fictionbook/2.0}title')
                    title = title_elem.text if title_elem is not None else f"第{i}章"
                    
                    # 提取段落内容
                    paragraphs = section.findall('.//{http://www.gribuser.ru/xml/fictionbook/2.0}p')
                    content_parts = []
                    for p in paragraphs:
                        if p.text:
                            content_parts.append(f"<p>{p.text}</p>")
                    
                    chapters.append({
                        'chapter_number': i,
                        'title': title,
                        'content': '\n'.join(content_parts)
                    })
        except Exception as e:
            logger.error(f"FB2章节提取失败: {str(e)}")
        
        return chapters
    
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染FB2内容"""
        try:
            if not self.chapters or chapter_number > len(self.chapters):
                return {'error': '章节不存在'}
            
            chapter = self.chapters[chapter_number - 1]
            
            return {
                'content': chapter['content'],
                'chapter_title': chapter['title'],
                'chapter_number': chapter_number,
                'total_chapters': len(self.chapters),
                'renderer_type': 'fb2_xhtml',
                'supports_pagination': True
            }
            
        except Exception as e:
            logger.error(f"FB2渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取FB2元数据"""
        return self.metadata
    
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取FB2目录"""
        return [{'chapter_number': ch['chapter_number'], 'title': ch['title']} 
                for ch in self.chapters]


class TextRenderer(BaseRenderer):
    """文本渲染器 - 处理TXT/Markdown/HTML，使用浏览器/WebView渲染"""
    
    def __init__(self, book_file_path: str, book_format: str):
        super().__init__(book_file_path, book_format)
        self.content = ""
        self.chapters = []
        self._load_content()
        
    def _load_content(self):
        """加载文本内容"""
        try:
            # 尝试不同编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            for encoding in encodings:
                try:
                    with open(self.book_file_path, 'r', encoding=encoding) as f:
                        self.content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            # 根据格式处理内容
            if self.book_format == 'markdown':
                self._process_markdown()
            elif self.book_format == 'html':
                self._process_html()
            else:
                self._process_text()
                
        except Exception as e:
            logger.error(f"文本加载失败: {str(e)}")
            self.content = ""
    
    def _process_markdown(self):
        """处理Markdown内容"""
        try:
            # 转换为HTML
            md = markdown.Markdown(extensions=['toc', 'tables', 'fenced_code'])
            html_content = md.convert(self.content)
            
            # 分章节（基于标题）
            self._split_by_headers(html_content)
            
        except Exception as e:
            logger.error(f"Markdown处理失败: {str(e)}")
            self._process_text()
    
    def _process_html(self):
        """处理HTML内容"""
        try:
            soup = BeautifulSoup(self.content, 'html.parser')
            
            # 清理不需要的标签
            for tag in soup(['script', 'style', 'meta', 'link']):
                tag.decompose()
            
            # 提取body内容
            body = soup.find('body')
            if body:
                content = str(body)
            else:
                content = str(soup)
            
            self._split_by_headers(content)
            
        except Exception as e:
            logger.error(f"HTML处理失败: {str(e)}")
            self._process_text()
    
    def _process_text(self):
        """处理纯文本内容"""
        try:
            # 按章节分割（寻找章节标记）
            chapter_patterns = [
                r'第[一二三四五六七八九十\d]+章',
                r'Chapter\s+\d+',
                r'第\d+章',
                r'章节\s*\d+',
            ]
            
            chapters_found = False
            for pattern in chapter_patterns:
                matches = list(re.finditer(pattern, self.content, re.IGNORECASE))
                if matches:
                    self._split_by_pattern(matches, pattern)
                    chapters_found = True
                    break
            
            if not chapters_found:
                # 按段落数量分割
                self._split_by_paragraphs()
                
        except Exception as e:
            logger.error(f"文本处理失败: {str(e)}")
            self.chapters = [{'chapter_number': 1, 'title': '全文', 'content': self.content}]
    
    def _split_by_headers(self, html_content: str):
        """按HTML标题分割章节"""
        soup = BeautifulSoup(html_content, 'html.parser')
        headers = soup.find_all(['h1', 'h2', 'h3'])
        
        if not headers:
            self.chapters = [{'chapter_number': 1, 'title': '全文', 'content': html_content}]
            return
        
        chapters = []
        for i, header in enumerate(headers):
            title = header.get_text().strip()
            
            # 获取章节内容
            content_parts = []
            current = header.next_sibling
            
            while current and current != (headers[i + 1] if i + 1 < len(headers) else None):
                if hasattr(current, 'name'):
                    content_parts.append(str(current))
                current = current.next_sibling
            
            chapters.append({
                'chapter_number': i + 1,
                'title': title,
                'content': ''.join(content_parts)
            })
        
        self.chapters = chapters
    
    def _split_by_pattern(self, matches, pattern: str):
        """按模式分割章节"""
        chapters = []
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(self.content)
            
            chapter_content = self.content[start_pos:end_pos].strip()
            title = match.group()
            
            # 转换为HTML段落
            paragraphs = chapter_content.split('\n\n')
            html_content = ''.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())
            
            chapters.append({
                'chapter_number': i + 1,
                'title': title,
                'content': html_content
            })
        
        self.chapters = chapters
    
    def _split_by_paragraphs(self, max_paragraphs_per_chapter: int = 50):
        """按段落数量分割章节"""
        paragraphs = [p.strip() for p in self.content.split('\n\n') if p.strip()]
        
        chapters = []
        for i in range(0, len(paragraphs), max_paragraphs_per_chapter):
            chapter_paragraphs = paragraphs[i:i + max_paragraphs_per_chapter]
            html_content = ''.join(f'<p>{p}</p>' for p in chapter_paragraphs)
            
            chapters.append({
                'chapter_number': len(chapters) + 1,
                'title': f'第{len(chapters) + 1}部分',
                'content': html_content
            })
        
        self.chapters = chapters
    
    def render(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染文本内容"""
        try:
            if not self.chapters or chapter_number > len(self.chapters):
                return {'error': '章节不存在'}
            
            chapter = self.chapters[chapter_number - 1]
            
            return {
                'content': chapter['content'],
                'chapter_title': chapter['title'],
                'chapter_number': chapter_number,
                'total_chapters': len(self.chapters),
                'renderer_type': f'text_{self.book_format}',
                'supports_pagination': True
            }
            
        except Exception as e:
            logger.error(f"文本渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取文本元数据"""
        return {
            'format': self.book_format,
            'character_count': len(self.content),
            'word_count': len(self.content.split()),
            'chapter_count': len(self.chapters)
        }
    
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取文本目录"""
        return [{'chapter_number': ch['chapter_number'], 'title': ch['title']} 
                for ch in self.chapters]


class RendererFactory:
    """渲染器工厂类"""
    
    RENDERER_MAP = {
        'epub': EPUBRenderer,
        'pdf': PDFRenderer,
        'mobi': MOBIRenderer,
        'azw3': MOBIRenderer,
        'fb2': FB2Renderer,
        'txt': TextRenderer,
        'markdown': TextRenderer,
        'md': TextRenderer,
        'html': TextRenderer,
        'htm': TextRenderer,
    }
    
    @classmethod
    def create_renderer(cls, book_file_path: str, book_format: str) -> BaseRenderer:
        """创建对应格式的渲染器"""
        format_lower = book_format.lower()
        
        if format_lower not in cls.RENDERER_MAP:
            raise ValueError(f"不支持的格式: {book_format}")
        
        renderer_class = cls.RENDERER_MAP[format_lower]
        return renderer_class(book_file_path, format_lower)
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """获取支持的格式列表"""
        return list(cls.RENDERER_MAP.keys())


class OptimizedBookRenderer:
    """优化的书籍渲染服务"""
    
    def __init__(self, book):
        self.book = book
        self.renderer = None
        self._initialize_renderer()
    
    def _initialize_renderer(self):
        """初始化渲染器"""
        try:
            file_path = self.book.file.path
            book_format = self.book.format
            
            self.renderer = RendererFactory.create_renderer(file_path, book_format)
            
        except Exception as e:
            logger.error(f"渲染器初始化失败: {str(e)}")
            self.renderer = None
    
    def render_chapter(self, chapter_number: int = 1, page_number: int = 1) -> Dict[str, Any]:
        """渲染指定章节"""
        if not self.renderer:
            return {'error': '渲染器未初始化'}
        
        try:
            result = self.renderer.render(chapter_number, page_number)
            
            # 添加书籍信息
            result.update({
                'book_id': self.book.id,
                'book_title': self.book.title,
                'book_author': self.book.author,
                'book_format': self.book.format
            })
            
            return result
            
        except Exception as e:
            logger.error(f"章节渲染失败: {str(e)}")
            return {'error': f'渲染失败: {str(e)}'}
    
    def get_book_metadata(self) -> Dict[str, Any]:
        """获取书籍元数据"""
        if not self.renderer:
            return {}
        
        try:
            return self.renderer.get_metadata()
        except Exception as e:
            logger.error(f"元数据获取失败: {str(e)}")
            return {}
    
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """获取目录"""
        if not self.renderer:
            return []
        
        try:
            return self.renderer.get_table_of_contents()
        except Exception as e:
            logger.error(f"目录获取失败: {str(e)}")
            return []
    
    def cleanup(self):
        """清理资源"""
        if self.renderer:
            self.renderer.cleanup() 