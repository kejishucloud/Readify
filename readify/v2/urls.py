from django.urls import path
from . import views

urlpatterns = [
    path("books/", views.books_api, name="v2_books"),
    path("books/<int:book_id>/chapters/<int:chapter_number>/", views.chapter_api, name="v2_chapter"),
    path("books/<int:book_id>/progress/", views.progress_api, name="v2_progress"),
    path("books/<int:book_id>/notes/", views.notes_api, name="v2_notes"),
    path("books/<int:book_id>/notes/create/", views.note_create_api, name="v2_note_create"),
    path("voices/", views.voices_api, name="v2_voices"),
    path("voices/create/", views.voice_create_api, name="v2_voice_create"),
    path("voices/<int:voice_id>/delete/", views.voice_delete_api, name="v2_voice_delete"),
    path("tts/synthesize/", views.synthesize_api, name="v2_tts_synthesize"),
]
