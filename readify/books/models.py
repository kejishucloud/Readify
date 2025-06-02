from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os


def book_upload_path(instance, filename):
    """生成书籍文件上传路径"""
    return f'books/{instance.user.id}/{filename}'


def cover_upload_path(instance, filename):
    """生成封面图片上传路径"""
    return f'covers/{instance.user.id}/{filename}'


class BookCategory(models.Model):
    """书籍分类模型"""
    CATEGORY_TYPES = [
        ('science', '科学技术'),
        ('literature', '文学艺术'),
        ('history', '历史文化'),
        ('philosophy', '哲学宗教'),
        ('economics', '经济管理'),
        ('education', '教育学习'),
        ('medicine', '医学健康'),
        ('law', '法律政治'),
        ('engineering', '工程技术'),
        ('computer', '计算机科学'),
        ('mathematics', '数学'),
        ('physics', '物理学'),
        ('chemistry', '化学'),
        ('biology', '生物学'),
        ('psychology', '心理学'),
        ('sociology', '社会学'),
        ('language', '语言学'),
        ('art', '艺术设计'),
        ('music', '音乐'),
        ('sports', '体育运动'),
        ('cooking', '烹饪美食'),
        ('travel', '旅游地理'),
        ('biography', '传记'),
        ('fiction', '小说'),
        ('poetry', '诗歌'),
        ('drama', '戏剧'),
        ('children', '儿童读物'),
        ('reference', '工具书'),
        ('other', '其他'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='分类名称')
    code = models.CharField(max_length=20, choices=CATEGORY_TYPES, unique=True, verbose_name='分类代码')
    description = models.TextField(blank=True, verbose_name='分类描述')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name='父分类')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '书籍分类'
        verbose_name_plural = '书籍分类'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_full_name(self):
        """获取完整分类名称"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Book(models.Model):
    """书籍模型"""
    SUPPORTED_FORMATS = [
        ('pdf', 'PDF'),
        ('epub', 'EPUB'),
        ('mobi', 'MOBI'),
        ('txt', 'TXT'),
        ('docx', 'DOCX'),
        ('html', 'HTML'),
    ]
    
    PROCESSING_STATUS = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '处理失败'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='书名')
    author = models.CharField(max_length=100, blank=True, verbose_name='作者')
    description = models.TextField(blank=True, verbose_name='描述')
    isbn = models.CharField(max_length=20, blank=True, verbose_name='ISBN')
    language = models.CharField(max_length=10, default='zh', verbose_name='语言')
    format = models.CharField(max_length=10, choices=SUPPORTED_FORMATS, verbose_name='格式')
    file = models.FileField(upload_to=book_upload_path, verbose_name='文件')
    cover = models.ImageField(upload_to=cover_upload_path, blank=True, null=True, verbose_name='封面')
    file_size = models.BigIntegerField(default=0, verbose_name='文件大小')
    page_count = models.IntegerField(default=0, verbose_name='页数')
    word_count = models.IntegerField(default=0, verbose_name='字数')
    
    # AI处理相关字段
    processing_status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUS, 
        default='pending',
        verbose_name='处理状态'
    )
    summary = models.TextField(blank=True, verbose_name='AI生成摘要')
    keywords = models.JSONField(default=list, verbose_name='关键词')
    
    # 用户和时间字段
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='上传时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    # 阅读统计
    view_count = models.IntegerField(default=0, verbose_name='查看次数')
    last_read_at = models.DateTimeField(null=True, blank=True, verbose_name='最后阅读时间')
    
    # 分类相关
    category = models.ForeignKey(BookCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='主分类')
    tags = models.CharField(max_length=500, blank=True, verbose_name='标签')
    
    class Meta:
        verbose_name = '书籍'
        verbose_name_plural = '书籍'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title
    
    def get_file_extension(self):
        """获取文件扩展名"""
        return os.path.splitext(self.file.name)[1].lower()
    
    def increment_view_count(self):
        """增加查看次数"""
        self.view_count += 1
        self.last_read_at = timezone.now()
        self.save(update_fields=['view_count', 'last_read_at'])


class BookContent(models.Model):
    """书籍内容模型（分章节存储）"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='contents', verbose_name='书籍')
    chapter_number = models.IntegerField(verbose_name='章节号')
    chapter_title = models.CharField(max_length=200, blank=True, verbose_name='章节标题')
    content = models.TextField(verbose_name='内容')
    word_count = models.IntegerField(default=0, verbose_name='字数')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '书籍内容'
        verbose_name_plural = '书籍内容'
        ordering = ['book', 'chapter_number']
        unique_together = ['book', 'chapter_number']
    
    def __str__(self):
        return f'{self.book.title} - 第{self.chapter_number}章'


class ReadingProgress(models.Model):
    """阅读进度模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    current_chapter = models.IntegerField(default=1, verbose_name='当前章节')
    current_position = models.IntegerField(default=0, verbose_name='当前位置')
    progress_percentage = models.FloatField(default=0.0, verbose_name='进度百分比')
    reading_time = models.IntegerField(default=0, verbose_name='阅读时间（秒）')
    last_read_at = models.DateTimeField(default=timezone.now, verbose_name='最后阅读时间')
    
    class Meta:
        verbose_name = '阅读进度'
        verbose_name_plural = '阅读进度'
        unique_together = ['user', 'book']
    
    def __str__(self):
        return f'{self.user.username} - {self.book.title}'


class ReadingSession(models.Model):
    """阅读会话模型 - 用于统计阅读时长"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    start_time = models.DateTimeField(default=timezone.now, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration_seconds = models.IntegerField(default=0, verbose_name='阅读时长(秒)')
    chapter_number = models.IntegerField(null=True, blank=True, verbose_name='章节号')
    pages_read = models.IntegerField(default=0, verbose_name='阅读页数')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    
    class Meta:
        verbose_name = '阅读会话'
        verbose_name_plural = '阅读会话'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'book']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.book.title} - {self.start_time.strftime("%Y-%m-%d %H:%M")}'
    
    def end_session(self):
        """结束阅读会话"""
        if self.is_active and not self.end_time:
            self.end_time = timezone.now()
            self.duration_seconds = int((self.end_time - self.start_time).total_seconds())
            self.is_active = False
            self.save()


class ReadingStatistics(models.Model):
    """阅读统计模型"""
    PERIOD_CHOICES = [
        ('daily', '日'),
        ('weekly', '周'),
        ('monthly', '月'),
        ('yearly', '年'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, verbose_name='统计周期')
    period_start = models.DateField(verbose_name='周期开始')
    period_end = models.DateField(verbose_name='周期结束')
    total_reading_time = models.IntegerField(default=0, verbose_name='总阅读时长(秒)')
    books_read = models.IntegerField(default=0, verbose_name='阅读书籍数')
    pages_read = models.IntegerField(default=0, verbose_name='阅读页数')
    sessions_count = models.IntegerField(default=0, verbose_name='阅读会话数')
    average_session_time = models.IntegerField(default=0, verbose_name='平均会话时长(秒)')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '阅读统计'
        verbose_name_plural = '阅读统计'
        unique_together = ['user', 'period_type', 'period_start']
        ordering = ['-period_start']
    
    def __str__(self):
        return f'{self.user.username} - {self.get_period_type_display()} - {self.period_start}'


class ParagraphSummary(models.Model):
    """段落总结模型"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='paragraph_summaries', verbose_name='书籍')
    chapter_number = models.IntegerField(verbose_name='章节号')
    paragraph_start = models.IntegerField(verbose_name='段落开始位置')
    paragraph_end = models.IntegerField(verbose_name='段落结束位置')
    original_text = models.TextField(verbose_name='原文')
    summary_text = models.TextField(verbose_name='总结文本')
    summary_type = models.CharField(
        max_length=20, 
        choices=[
            ('brief', '简要总结'),
            ('detailed', '详细总结'),
            ('key_points', '要点提取'),
        ],
        default='brief',
        verbose_name='总结类型'
    )
    ai_model_used = models.CharField(max_length=100, blank=True, verbose_name='使用的AI模型')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '段落总结'
        verbose_name_plural = '段落总结'
        ordering = ['book', 'chapter_number', 'paragraph_start']
        indexes = [
            models.Index(fields=['book', 'chapter_number']),
        ]
    
    def __str__(self):
        return f'{self.book.title} - 第{self.chapter_number}章 段落总结'


class BookSummary(models.Model):
    """全书总结模型"""
    SUMMARY_TYPES = [
        ('overview', '概览总结'),
        ('chapter_wise', '分章总结'),
        ('thematic', '主题总结'),
        ('key_insights', '核心洞察'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='book_summaries', verbose_name='书籍')
    summary_type = models.CharField(max_length=20, choices=SUMMARY_TYPES, verbose_name='总结类型')
    title = models.CharField(max_length=200, verbose_name='总结标题')
    content = models.TextField(verbose_name='总结内容')
    key_points = models.JSONField(default=list, verbose_name='关键要点')
    themes = models.JSONField(default=list, verbose_name='主要主题')
    word_count = models.IntegerField(default=0, verbose_name='字数')
    ai_model_used = models.CharField(max_length=100, blank=True, verbose_name='使用的AI模型')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '全书总结'
        verbose_name_plural = '全书总结'
        ordering = ['-created_at']
        unique_together = ['book', 'summary_type']
    
    def __str__(self):
        return f'{self.book.title} - {self.get_summary_type_display()}'


class BookNote(models.Model):
    """书籍笔记模型 - 扩展版本"""
    NOTE_TYPES = [
        ('highlight', '高亮标注'),
        ('note', '文字笔记'),
        ('bookmark', '书签'),
        ('question', '疑问'),
        ('insight', '感悟'),
    ]
    
    COLOR_CHOICES = [
        ('yellow', '黄色'),
        ('green', '绿色'),
        ('blue', '蓝色'),
        ('red', '红色'),
        ('purple', '紫色'),
        ('orange', '橙色'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    chapter_number = models.IntegerField(verbose_name='章节号')
    position_start = models.IntegerField(verbose_name='开始位置')
    position_end = models.IntegerField(verbose_name='结束位置')
    selected_text = models.TextField(verbose_name='选中文本')
    note_content = models.TextField(blank=True, verbose_name='笔记内容')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='note', verbose_name='笔记类型')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='yellow', verbose_name='标注颜色')
    is_public = models.BooleanField(default=False, verbose_name='是否公开')
    tags = models.CharField(max_length=200, blank=True, verbose_name='标签')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '书籍笔记'
        verbose_name_plural = '书籍笔记'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'book']),
            models.Index(fields=['note_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.book.title} - {self.get_note_type_display()}'


class NoteCollection(models.Model):
    """笔记集合模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    name = models.CharField(max_length=100, verbose_name='集合名称')
    description = models.TextField(blank=True, verbose_name='描述')
    notes = models.ManyToManyField(BookNote, blank=True, verbose_name='笔记')
    is_public = models.BooleanField(default=False, verbose_name='是否公开')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '笔记集合'
        verbose_name_plural = '笔记集合'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.name}'


class BookQuestion(models.Model):
    """用户提问模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    question = models.TextField(verbose_name='问题')
    answer = models.TextField(blank=True, verbose_name='AI回答')
    context_chapters = models.JSONField(default=list, verbose_name='相关章节')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    answered_at = models.DateTimeField(null=True, blank=True, verbose_name='回答时间')
    
    class Meta:
        verbose_name = '书籍问答'
        verbose_name_plural = '书籍问答'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.book.title} 问题'


class BatchUpload(models.Model):
    """批量上传记录"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('partial', '部分成功'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    upload_name = models.CharField(max_length=200, verbose_name='上传批次名称')
    total_files = models.IntegerField(default=0, verbose_name='总文件数')
    processed_files = models.IntegerField(default=0, verbose_name='已处理文件数')
    successful_files = models.IntegerField(default=0, verbose_name='成功文件数')
    failed_files = models.IntegerField(default=0, verbose_name='失败文件数')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_log = models.TextField(blank=True, verbose_name='错误日志')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '批量上传'
        verbose_name_plural = '批量上传'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.upload_name}'
    
    @property
    def progress_percentage(self):
        if self.total_files == 0:
            return 0
        return (self.processed_files / self.total_files) * 100


class ReadingAssistant(models.Model):
    """AI阅读助手会话模型"""
    SESSION_STATUS = [
        ('active', '活跃'),
        ('paused', '暂停'),
        ('ended', '结束'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    session_name = models.CharField(max_length=200, blank=True, verbose_name='会话名称')
    current_chapter = models.IntegerField(default=1, verbose_name='当前章节')
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='active', verbose_name='状态')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用AI助手')
    auto_summary = models.BooleanField(default=False, verbose_name='自动生成章节总结')
    context_memory = models.JSONField(default=dict, verbose_name='上下文记忆')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    last_active_at = models.DateTimeField(default=timezone.now, verbose_name='最后活跃时间')
    
    class Meta:
        verbose_name = 'AI阅读助手'
        verbose_name_plural = 'AI阅读助手'
        unique_together = ['user', 'book']
        ordering = ['-last_active_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.book.title} 阅读助手'
    
    def update_activity(self):
        """更新最后活跃时间"""
        self.last_active_at = timezone.now()
        self.save(update_fields=['last_active_at'])


class ReadingQA(models.Model):
    """阅读问答记录模型"""
    QUESTION_TYPES = [
        ('text', '文本问答'),
        ('paragraph', '段落问答'),
        ('chapter', '章节问答'),
        ('book', '全书问答'),
        ('concept', '概念解释'),
        ('summary', '内容总结'),
    ]
    
    assistant = models.ForeignKey(ReadingAssistant, on_delete=models.CASCADE, related_name='qa_records', verbose_name='阅读助手')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='text', verbose_name='问题类型')
    question = models.TextField(verbose_name='问题')
    selected_text = models.TextField(blank=True, verbose_name='选中文本')
    chapter_number = models.IntegerField(null=True, blank=True, verbose_name='章节号')
    position_start = models.IntegerField(null=True, blank=True, verbose_name='开始位置')
    position_end = models.IntegerField(null=True, blank=True, verbose_name='结束位置')
    answer = models.TextField(blank=True, verbose_name='AI回答')
    context_used = models.TextField(blank=True, verbose_name='使用的上下文')
    ai_model_used = models.CharField(max_length=100, blank=True, verbose_name='使用的AI模型')
    processing_time = models.FloatField(default=0.0, verbose_name='处理时间(秒)')
    tokens_used = models.IntegerField(default=0, verbose_name='使用的令牌数')
    is_helpful = models.BooleanField(null=True, blank=True, verbose_name='是否有帮助')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '阅读问答'
        verbose_name_plural = '阅读问答'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assistant', 'question_type']),
            models.Index(fields=['chapter_number']),
        ]
    
    def __str__(self):
        return f'{self.assistant.book.title} - {self.get_question_type_display()}'


class ChapterSummary(models.Model):
    """章节总结模型"""
    SUMMARY_TYPES = [
        ('auto', '自动总结'),
        ('manual', '手动总结'),
        ('key_points', '要点提取'),
        ('detailed', '详细总结'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapter_summaries', verbose_name='书籍')
    chapter_number = models.IntegerField(verbose_name='章节号')
    chapter_title = models.CharField(max_length=200, blank=True, verbose_name='章节标题')
    summary_type = models.CharField(max_length=20, choices=SUMMARY_TYPES, default='auto', verbose_name='总结类型')
    summary_content = models.TextField(verbose_name='总结内容')
    key_points = models.JSONField(default=list, verbose_name='关键要点')
    word_count = models.IntegerField(default=0, verbose_name='总结字数')
    original_word_count = models.IntegerField(default=0, verbose_name='原文字数')
    compression_ratio = models.FloatField(default=0.0, verbose_name='压缩比')
    ai_model_used = models.CharField(max_length=100, blank=True, verbose_name='使用的AI模型')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '章节总结'
        verbose_name_plural = '章节总结'
        unique_together = ['book', 'chapter_number', 'summary_type']
        ordering = ['book', 'chapter_number']
        indexes = [
            models.Index(fields=['book', 'chapter_number']),
        ]
    
    def __str__(self):
        return f'{self.book.title} - 第{self.chapter_number}章总结'
    
    def calculate_compression_ratio(self):
        """计算压缩比"""
        if self.original_word_count > 0:
            self.compression_ratio = self.word_count / self.original_word_count
        else:
            self.compression_ratio = 0.0


class ReadingTimeTracker(models.Model):
    """阅读时间追踪模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    chapter_number = models.IntegerField(verbose_name='章节号')
    start_time = models.DateTimeField(default=timezone.now, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration_seconds = models.IntegerField(default=0, verbose_name='阅读时长(秒)')
    words_read = models.IntegerField(default=0, verbose_name='阅读字数')
    reading_speed = models.FloatField(default=0.0, verbose_name='阅读速度(字/分钟)')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    pause_count = models.IntegerField(default=0, verbose_name='暂停次数')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '阅读时间追踪'
        verbose_name_plural = '阅读时间追踪'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'book']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.book.title} 第{self.chapter_number}章'
    
    def end_tracking(self):
        """结束时间追踪"""
        if self.is_active and not self.end_time:
            self.end_time = timezone.now()
            self.duration_seconds = int((self.end_time - self.start_time).total_seconds())
            self.is_active = False
            
            # 计算阅读速度
            if self.duration_seconds > 0:
                self.reading_speed = (self.words_read / self.duration_seconds) * 60
            
            self.save()


class ReadingGoal(models.Model):
    """阅读目标模型"""
    GOAL_TYPES = [
        ('daily', '每日目标'),
        ('weekly', '每周目标'),
        ('monthly', '每月目标'),
        ('yearly', '年度目标'),
    ]
    
    GOAL_METRICS = [
        ('time', '阅读时间'),
        ('pages', '阅读页数'),
        ('books', '阅读书籍数'),
        ('words', '阅读字数'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES, verbose_name='目标类型')
    metric_type = models.CharField(max_length=20, choices=GOAL_METRICS, verbose_name='指标类型')
    target_value = models.IntegerField(verbose_name='目标值')
    current_value = models.IntegerField(default=0, verbose_name='当前值')
    start_date = models.DateField(verbose_name='开始日期')
    end_date = models.DateField(verbose_name='结束日期')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    is_completed = models.BooleanField(default=False, verbose_name='是否完成')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '阅读目标'
        verbose_name_plural = '阅读目标'
        ordering = ['-created_at']
        unique_together = ['user', 'goal_type', 'metric_type', 'start_date']
    
    def __str__(self):
        return f'{self.user.username} - {self.get_goal_type_display()}{self.get_metric_type_display()}目标'
    
    @property
    def progress_percentage(self):
        """计算完成百分比"""
        if self.target_value == 0:
            return 0
        return min((self.current_value / self.target_value) * 100, 100)
    
    def update_progress(self, value):
        """更新进度"""
        self.current_value += value
        if self.current_value >= self.target_value and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
        self.save()
