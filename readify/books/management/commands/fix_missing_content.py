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
                    success = processing_service.create_book_chapters(book)
                    
                    if success:
                        # 成功创建章节
                        chapter_count = book.contents.count()
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ 成功修复: {book.title} ({chapter_count}个章节)')
                        )
                    else:
                        # 创建失败，但已有默认内容
                        self.stdout.write(
                            self.style.WARNING(f'⚠ 创建默认内容: {book.title}')
                        )
                    
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