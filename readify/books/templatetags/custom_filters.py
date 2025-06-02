from django import template
from django.utils.safestring import mark_safe
import re
import base64

register = template.Library()


@register.filter
def add_line_numbers(text):
    """为文本添加行号"""
    if not text:
        return ""
    
    lines = text.split('\n')
    numbered_lines = []
    
    for i, line in enumerate(lines, 1):
        # 清理空行
        if line.strip():
            numbered_lines.append(
                f'<span class="line-number" data-line="{i}">{i:03d}</span><span class="line-content" data-line="{i}">{line}</span>'
            )
        else:
            numbered_lines.append('<br>')
    
    return mark_safe('<div class="numbered-content">' + '<br>'.join(numbered_lines) + '</div>')


@register.filter
def format_book_content(text, book_type='general'):
    """根据书籍类型格式化内容"""
    if not text:
        return ""
    
    # 基本清理
    text = text.strip()
    
    if book_type == 'poetry':
        # 诗歌格式：保持原有换行，居中对齐
        lines = text.split('\n')
        formatted_lines = []
        for i, line in enumerate(lines, 1):
            if line.strip():
                formatted_lines.append(f'<p class="text-center poetry-line" data-line="{i}">{line.strip()}</p>')
            else:
                formatted_lines.append('<br>')
        return mark_safe('<div class="poetry-content">' + ''.join(formatted_lines) + '</div>')
    
    elif book_type == 'novel' or book_type == 'fiction':
        # 小说格式：段落缩进，适当间距
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        line_count = 1
        for para in paragraphs:
            if para.strip():
                # 清理段落内的换行
                para = para.replace('\n', ' ').strip()
                formatted_paragraphs.append(f'<p class="novel-paragraph" data-line="{line_count}">{para}</p>')
                line_count += 1
        return mark_safe('<div class="novel-content">' + ''.join(formatted_paragraphs) + '</div>')
    
    elif book_type in ['technical', 'computer', 'science']:
        # 技术书籍格式：保持代码块，列表等格式
        # 检测代码块
        text = re.sub(r'```(.*?)```', r'<pre class="code-block"><code>\1</code></pre>', text, flags=re.DOTALL)
        
        # 检测列表
        lines = text.split('\n')
        formatted_lines = []
        in_list = False
        line_count = 1
        
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line) or line.startswith('- ') or line.startswith('* '):
                if not in_list:
                    formatted_lines.append('<ul class="technical-list">')
                    in_list = True
                formatted_lines.append(f'<li data-line="{line_count}">{line[2:].strip()}</li>')
            else:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                if line:
                    formatted_lines.append(f'<p class="technical-paragraph" data-line="{line_count}">{line}</p>')
                    line_count += 1
                else:
                    formatted_lines.append('<br>')
        
        if in_list:
            formatted_lines.append('</ul>')
        
        return mark_safe('<div class="technical-content">' + ''.join(formatted_lines) + '</div>')
    
    else:
        # 默认格式：简单的段落分割，添加行号
        lines = text.split('\n')
        formatted_lines = []
        for i, line in enumerate(lines, 1):
            if line.strip():
                formatted_lines.append(f'<p class="general-paragraph" data-line="{i}">{line}</p>')
            else:
                formatted_lines.append('<br>')
        return mark_safe('<div class="general-content">' + ''.join(formatted_lines) + '</div>')


@register.filter
def highlight_search_terms(text, search_term):
    """高亮搜索词"""
    if not search_term or not text:
        return text
    
    # 使用正则表达式进行不区分大小写的替换
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    highlighted = pattern.sub(f'<mark class="search-highlight">{search_term}</mark>', text)
    return mark_safe(highlighted)


@register.filter
def truncate_smart(text, length=100):
    """智能截断文本，在句号或逗号处截断"""
    if not text or len(text) <= length:
        return text
    
    # 在指定长度附近寻找合适的截断点
    truncated = text[:length]
    
    # 寻找最后的句号或逗号
    for i in range(len(truncated) - 1, max(0, len(truncated) - 20), -1):
        if truncated[i] in '。，！？.!?':
            return truncated[:i + 1] + '...'
    
    # 如果没找到合适的截断点，就在最后一个空格处截断
    last_space = truncated.rfind(' ')
    if last_space > length * 0.8:
        return truncated[:last_space] + '...'
    
    return truncated + '...'


@register.filter
def reading_time_estimate(text, words_per_minute=200):
    """估算阅读时间"""
    if not text:
        return "0分钟"
    
    # 简单的字数统计（中文按字符数，英文按单词数）
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
    
    # 中文字符按每分钟300字计算，英文按每分钟200词计算
    total_minutes = (chinese_chars / 300) + (english_words / words_per_minute)
    
    if total_minutes < 1:
        return "不到1分钟"
    elif total_minutes < 60:
        return f"{int(total_minutes)}分钟"
    else:
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        return f"{hours}小时{minutes}分钟"


@register.filter
def get_book_type(book):
    """获取书籍类型"""
    if hasattr(book, 'category') and book.category:
        return book.category.code
    return 'general'


@register.filter
def b64encode(value):
    """Base64编码过滤器"""
    if isinstance(value, bytes):
        return base64.b64encode(value).decode('utf-8')
    elif isinstance(value, str):
        return base64.b64encode(value.encode('utf-8')).decode('utf-8')
    return '' 