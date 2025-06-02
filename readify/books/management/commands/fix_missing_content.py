from django.core.management.base import BaseCommand
from django.db import transaction
from readify.books.models import Book, BookContent
from readify.books.services import BookProcessingService


class Command(BaseCommand):
    help = '修复缺失BookContent的书籍'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示需要修复的书籍，不实际修复',
        )
        parser.add_argument(
            '--book-id',
            type=int,
            help='指定要修复的书籍ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        book_id = options.get('book_id')
        
        # 查找没有BookContent的书籍
        if book_id:
            books_without_content = Book.objects.filter(
                id=book_id,
                contents__isnull=True
            ).distinct()
        else:
            books_without_content = Book.objects.filter(
                contents__isnull=True
            ).distinct()
        
        if not books_without_content.exists():
            self.stdout.write(
                self.style.SUCCESS('没有发现缺失内容的书籍')
            )
            return
        
        self.stdout.write(
            f'发现 {books_without_content.count()} 本书籍缺失内容'
        )
        
        if dry_run:
            for book in books_without_content:
                self.stdout.write(
                    f'- ID: {book.id}, 标题: {book.title}, 用户: {book.user.username}'
                )
            return
        
        # 修复书籍内容
        fixed_count = 0
        failed_count = 0
        
        for book in books_without_content:
            try:
                with transaction.atomic():
                    # 使用BookProcessingService来处理内容提取
                    processing_service = BookProcessingService(book.user)
                    content = processing_service._extract_text_content(book)
                    
                    if content:
                        # 成功提取到内容
                        BookContent.objects.create(
                            book=book,
                            chapter_number=1,
                            chapter_title="全文内容",
                            content=content[:50000],  # 限制长度
                            word_count=len(content)
                        )
                        book.word_count = len(content)
                        book.processing_status = 'completed'
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ 成功修复: {book.title}')
                        )
                    else:
                        # 提取失败，创建默认内容
                        default_content = f"抱歉，无法自动解析《{book.title}》的文本内容。\n\n可能的原因：\n1. 文件格式不支持自动解析\n2. 文件内容为图片或扫描版\n3. 文件已加密或损坏\n\n请尝试：\n- 转换为TXT格式后重新上传\n- 联系管理员获取帮助"
                        
                        BookContent.objects.create(
                            book=book,
                            chapter_number=1,
                            chapter_title="内容解析说明",
                            content=default_content,
                            word_count=len(default_content)
                        )
                        book.word_count = len(default_content)
                        book.processing_status = 'failed'
                        self.stdout.write(
                            self.style.WARNING(f'⚠ 创建默认内容: {book.title}')
                        )
                    
                    book.save()
                    fixed_count += 1
                    
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ 修复失败: {book.title} - {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n修复完成: 成功 {fixed_count} 本，失败 {failed_count} 本'
            )
        ) 