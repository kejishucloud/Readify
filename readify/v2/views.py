"""Versioned, CSRF-protected V2 reader and optional voice APIs."""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from readify.books.models import Book, BookContent, ReadingProgress, BookNote
from .models import VoiceProfile
from .voice_service import CosyVoiceWorkerClient, PrivateVoiceStore, VoiceServiceError

logger = logging.getLogger(__name__)


def parse_json(request):
    """Parse a small JSON POST; reject malformed and oversized bodies."""
    if len(request.body) > 16 * 1024:
        raise ValueError("请求体过大")
    try:
        obj = json.loads(request.body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("无效的 JSON 请求") from exc
    if not isinstance(obj, dict):
        raise ValueError("请求必须为 JSON 对象")
    return obj


@login_required
@require_GET
def reader_page(request, book_id):
    """Responsive reader independent of missing legacy templates."""
    book = get_object_or_404(Book, pk=book_id, user=request.user)
    return render(request, "books/reader_v2.html", {"book": book})


@login_required
@require_GET
def books_api(request):
    books = Book.objects.filter(user=request.user).order_by("-last_read_at", "-uploaded_at")[:100]
    return JsonResponse({"books": [
        {"id": b.id, "title": b.title, "author": b.author, "format": b.format,
         "url": f"/books/{b.id}/v2/"}
        for b in books
    ]})


@login_required
@require_GET
@never_cache
def chapter_api(request, book_id, chapter_number):
    book = get_object_or_404(Book, pk=book_id, user=request.user)
    chapter = get_object_or_404(BookContent, book=book, chapter_number=chapter_number)
    chapters = list(BookContent.objects.filter(book=book).order_by("chapter_number")
                    .values("chapter_number", "chapter_title"))
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()
    response = JsonResponse({
        "book": {"id": book.id, "title": book.title},
        "chapter": {"number": chapter.chapter_number, "title": chapter.chapter_title, "content": chapter.content},
        "chapters": [{"number": x["chapter_number"], "title": x["chapter_title"]} for x in chapters],
        "progress": {"chapter": progress.current_chapter, "position": progress.current_position}
        if progress else {"chapter": chapters[0]["chapter_number"], "position": 0},
    })
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
def progress_api(request, book_id):
    book = get_object_or_404(Book, pk=book_id, user=request.user)
    try:
        data = parse_json(request)
        chapter_number, position = data.get("chapter"), data.get("position")
        if type(chapter_number) is not int or type(position) is not int:
            raise ValueError("章节和位置必须为整数")
        if not (0 <= position <= 10_000_000):
            raise ValueError("阅读位置超出范围")
        if not BookContent.objects.filter(book=book, chapter_number=chapter_number).exists():
            raise ValueError("章节不存在")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    with transaction.atomic():
        obj, _ = ReadingProgress.objects.update_or_create(
            user=request.user,
            book=book,
            defaults={
                "current_chapter": chapter_number,
                "current_position": position,
                "last_read_at": timezone.now(),
            },
        )
    return JsonResponse({"success": True, "chapter": obj.current_chapter, "position": obj.current_position})


@login_required
@require_GET
def voices_api(request):
    profiles = VoiceProfile.objects.filter(user=request.user, is_active=True).values("id", "name", "rights")
    worker = CosyVoiceWorkerClient()
    return JsonResponse({
        "browser_tts": True,
        "clone_available": worker.available,
        "clone_modes": ["clone", "cross_language", "instruct"] if worker.available else [],
        "voices": list(profiles),
    })


@login_required
@require_POST
def voice_create_api(request):
    if request.POST.get("consent") != "yes":
        return JsonResponse({"error": "必须确认本人拥有声音权利或已获得明确授权"}, status=400)
    name = request.POST.get("name", "").strip()[:80]
    prompt_text = request.POST.get("prompt_text", "").strip()
    rights = request.POST.get("rights", "")
    file = request.FILES.get("sample")
    if not name or not prompt_text or len(prompt_text) > 600 or rights not in {"self", "licensed"} or file is None:
        return JsonResponse({"error": "请输入音色名称、参考文本并上传 WAV 文件"}, status=400)
    if VoiceProfile.objects.filter(user=request.user, is_active=True).count() >= 10:
        return JsonResponse({"error": "单用户最多保存 10 个音色"}, status=400)
    store = PrivateVoiceStore()
    try:
        key = store.save_wav(file)
    except VoiceServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    try:
        profile = VoiceProfile.objects.create(
            user=request.user, name=name, prompt_text=prompt_text,
            rights=rights, sample_key=key, consent_confirmed_at=timezone.now()
        )
    except Exception:
        store.delete_sample(key)
        raise
    return JsonResponse({"id": profile.pk, "name": profile.name}, status=201)


@login_required
@require_POST
def voice_delete_api(request, voice_id):
    profile = get_object_or_404(VoiceProfile, pk=voice_id, user=request.user)
    key = profile.sample_key
    profile.delete()
    PrivateVoiceStore().delete_sample(key)
    return JsonResponse({"success": True})


@login_required
@require_POST
def synthesize_api(request):
    try:
        data = parse_json(request)
        text = data.get("text", "")
        mode = data.get("mode", "clone")
        voice_id = data.get("voice_id")
        if not isinstance(text, str) or not (1 <= len(text.strip()) <= 500):
            raise ValueError("单次合成文本必须为 1-500 字符")
        if mode not in {"clone", "cross_language", "instruct"} or type(voice_id) is not int:
            raise ValueError("不支持的语音模式或音色编号")
        style = data.get("style", "calm")
        if style not in {"calm", "warm", "cheerful", "serious"}:
            raise ValueError("不支持的语音风格")
        profile = get_object_or_404(VoiceProfile, pk=voice_id, user=request.user, is_active=True)
        audio = CosyVoiceWorkerClient().synthesize(text=text, profile=profile, mode=mode, style=style)
        response = HttpResponse(audio, content_type="audio/wav")
        response["Cache-Control"] = "private, no-store"
        response["Content-Disposition"] = 'inline; filename="readify-speech.wav"'
        return response
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except VoiceServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=503)


@login_required
@require_GET
@never_cache
def notes_api(request, book_id):
    """Read only the signed-in user's notes for a book."""
    book = get_object_or_404(Book, pk=book_id, user=request.user)
    notes = BookNote.objects.filter(user=request.user, book=book).order_by("-created_at")[:200]
    response = JsonResponse({"notes": [
        {"id": n.id, "chapter": n.chapter_number, "position": n.position_start,
         "selected_text": n.selected_text, "content": n.note_content,
         "type": n.note_type, "created_at": n.created_at.isoformat()}
        for n in notes
    ]})
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
def note_create_api(request, book_id):
    """Create a user-owned note from the current chapter selection."""
    book = get_object_or_404(Book, pk=book_id, user=request.user)
    try:
        data = parse_json(request)
        chapter = data.get("chapter")
        position = data.get("position")
        selection = data.get("selected_text", "")
        body = data.get("content", "")
        if type(chapter) is not int or type(position) is not int or position < 0:
            raise ValueError("笔记位置无效")
        if not BookContent.objects.filter(book=book, chapter_number=chapter).exists():
            raise ValueError("章节不存在")
        if not isinstance(selection, str) or not isinstance(body, str):
            raise ValueError("笔记内容必须为文字")
        if len(selection) > 1000 or len(body) > 2000 or not (selection.strip() or body.strip()):
            raise ValueError("笔记不能为空，选中文本最多1000字、笔记最多2000字")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    note = BookNote.objects.create(
        user=request.user, book=book, chapter_number=chapter,
        position_start=position, position_end=position,
        selected_text=selection, note_content=body,
        note_type="highlight" if selection.strip() else "note",
        is_public=False,
    )
    return JsonResponse({"success": True, "id": note.pk}, status=201)
