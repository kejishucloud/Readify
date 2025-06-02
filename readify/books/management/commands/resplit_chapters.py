from django.core.management.base import BaseCommand
from django.db import transaction, models
from readify.books.models import Book, BookContent
from readify.books.services import BookProcessingService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '重新分割现有书籍的章节'

    def add_arguments(self, parser):
        parser.add_argument(
            '--book-id',
            type=int,
            help='指定要重新分割的书籍ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要处理的书籍，不实际执行'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新分割所有书籍，包括已有多章节的'
        )

    def handle(self, *args, **options):
        book_id = options.get('book_id')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        if book_id:
            # 处理指定书籍
            try:
                book = Book.objects.get(id=book_id)
                books_to_process = Book.objects.filter(id=book_id)
            except Book.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'书籍ID {book_id} 不存在')
                )
                return
        else:
            # 查找需要重新分割的书籍
            if force:
                # 强制模式：处理所有书籍
                books_to_process = Book.objects.filter(
                    processing_status__in=['completed', 'failed']
                )
            else:
                # 只处理单章节书籍
                books_to_process = Book.objects.filter(
                    processing_status__in=['completed', 'failed']
                ).annotate(
                    chapter_count=models.Count('contents')
                ).filter(
                    chapter_count=1
                )

        total_books = books_to_process.count()
        
        if total_books == 0:
            self.stdout.write(
                self.style.WARNING('没有找到需要重新分割的书籍')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'找到 {total_books} 本书籍需要重新分割章节')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('预览模式，不会实际执行操作：')
            )
            for book in books_to_process:
                chapter_count = book.contents.count()
                self.stdout.write(f'  - {book.title} (当前章节数: {chapter_count})')
            return

        # 实际处理
        processed_count = 0
        failed_count = 0

        for book in books_to_process:
            try:
                with transaction.atomic():
                    old_chapter_count = book.contents.count()
                    
                    # 使用BookProcessingService重新分割章节
                    processing_service = BookProcessingService(book.user)
                    success = processing_service.create_book_chapters(book)
                    
                    if success:
                        new_chapter_count = book.contents.count()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ {book.title}: {old_chapter_count} → {new_chapter_count} 章节'
                            )
                        )
                        processed_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'⚠ {book.title}: 重新分割失败，保持原状')
                        )
                        failed_count += 1
                        
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ {book.title}: 处理失败 - {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n重新分割完成: 成功 {processed_count} 本，失败 {failed_count} 本'
            )
        ) 