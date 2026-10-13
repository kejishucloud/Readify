"""Regression tests for V2 authorization and chapter/progress endpoints.

Requires the legacy books tables to be migrated/synchronized first.
"""
import json
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from readify.books.models import Book, BookContent, ReadingProgress


@override_settings(ALLOWED_HOSTS=["testserver"])
class ReaderV2SecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user("reader_owner", password="safe-test-password")
        self.other = user_model.objects.create_user("reader_other", password="safe-test-password")
        self.book = Book.objects.create(
            user=self.owner, title="A test book", format="txt",
            file=SimpleUploadedFile("a.txt", b"hello"),
        )
        BookContent.objects.create(book=self.book, chapter_number=1, chapter_title="Start", content="Hello world.")

    def test_user_can_read_owned_book(self):
        self.client.force_login(self.owner)
        res = self.client.get(reverse("v2_chapter", args=[self.book.pk, 1]))
        self.assertEqual(res.status_code, 200)
        self.assertIn("Hello world", res.json()["chapter"]["content"])

    def test_cannot_access_another_users_book(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("v2_chapter", args=[self.book.pk, 1])).status_code, 404)

    def test_progress_rejects_non_integer_and_missing_chapter(self):
        self.client.force_login(self.owner)
        url = reverse("v2_progress", args=[self.book.pk])
        for payload in [{"chapter": 1, "position": -5}, {"chapter": 999, "position": 0}, {"chapter": "1", "position": 0}]:
            res = self.client.post(url, json.dumps(payload), content_type="application/json")
            self.assertEqual(res.status_code, 400)
        self.assertFalse(ReadingProgress.objects.filter(user=self.owner).exists())

    def test_progress_updates_existing_reading_session(self):
        self.client.force_login(self.owner)
        url = reverse("v2_progress", args=[self.book.pk])
        res = self.client.post(url, json.dumps({"chapter": 1, "position": 7}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ReadingProgress.objects.get(user=self.owner, book=self.book).current_position, 7)

    def test_voice_creation_requires_consent(self):
        self.client.force_login(self.owner)
        res = self.client.post(reverse("v2_voice_create"), {"name": "voice"})
        self.assertEqual(res.status_code, 400)
