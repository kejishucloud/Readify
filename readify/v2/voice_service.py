"""Consent-bound voice samples and an OPTIONAL CosyVoice HTTP worker.

The worker URL and bearer token are server-controlled. Never accept a URL
from a browser or store reference audio underneath MEDIA_ROOT/STATIC_ROOT.
"""
from __future__ import annotations

import io
import logging
import uuid
import wave
from pathlib import Path

import httpx
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)
MAX_REFERENCE_BYTES = 8 * 1024 * 1024
MAX_AUDIO_RESPONSE_BYTES = 12 * 1024 * 1024


class VoiceServiceError(Exception):
    """Validation or provider failure suitable for a short client message."""


class PrivateVoiceStore:
    """Stores sample bytes under a non-served directory; no public URL exists."""

    def __init__(self):
        root = Path(getattr(settings, "PRIVATE_VOICE_STORAGE_ROOT", settings.BASE_DIR / "private_voice_samples"))
        self.storage = FileSystemStorage(location=str(root), base_url=None)

    def save_wav(self, uploaded) -> str:
        if uploaded.size is None or not (0 < uploaded.size <= MAX_REFERENCE_BYTES):
            raise VoiceServiceError("参考音频必须小于 8MB")
        payload = uploaded.read(MAX_REFERENCE_BYTES + 1)
        if len(payload) > MAX_REFERENCE_BYTES or payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
            raise VoiceServiceError("仅支持有效的 WAV 参考音频")
        try:
            with wave.open(io.BytesIO(payload), "rb") as wav:
                seconds = wav.getnframes() / max(wav.getframerate(), 1)
                if not (3 <= seconds <= 30) or wav.getnchannels() not in (1, 2):
                    raise VoiceServiceError("需要 3-30 秒、单声道或双声道的 WAV 音频")
                if not 8000 <= wav.getframerate() <= 48000:
                    raise VoiceServiceError("参考音频采样率必须在 8-48kHz")
        except (wave.Error, EOFError) as exc:
            raise VoiceServiceError("WAV 音频格式损坏") from exc
        key = f"{uuid.uuid4().hex}.wav"
        return self.storage.save(key, ContentFile(payload))

    def open_sample(self, key: str):
        if not key or Path(key).name != key or not key.endswith(".wav"):
            raise VoiceServiceError("无效的音色样本")
        return self.storage.open(key, "rb")

    def delete_sample(self, key: str) -> None:
        if key and Path(key).name == key:
            self.storage.delete(key)


class CosyVoiceWorkerClient:
    """Proxy cloning requests to a separately deployed trusted GPU worker."""

    def __init__(self):
        self.url = getattr(settings, "READIFY_VOICE_WORKER_URL", "").rstrip("/")
        self.token = getattr(settings, "READIFY_VOICE_WORKER_TOKEN", "")

    @property
    def available(self) -> bool:
        return bool(self.url and self.token and self.url.startswith(("https://", "http://")))

    def synthesize(self, *, text: str, profile, mode: str, style: str = "calm") -> bytes:
        if not self.available:
            raise VoiceServiceError("尚未配置声音克隆服务，请使用设备语音模式")
        with PrivateVoiceStore().open_sample(profile.sample_key) as sample:
            try:
                with httpx.Client(timeout=httpx.Timeout(180, connect=8), follow_redirects=False) as client:
                    response = client.post(
                        f"{self.url}/v1/synthesize",
                        headers={"Authorization": f"Bearer {self.token}"},
                        data={
                            "text": text,
                            "prompt_text": profile.prompt_text,
                            "mode": mode,
                            "style": style,
                        },
                        files={"reference": ("reference.wav", sample, "audio/wav")},
                    )
                if response.status_code != 200:
                    logger.warning("Voice worker returned HTTP %d", response.status_code)
                    raise VoiceServiceError("语音合成暂不可用")
                if len(response.content) > MAX_AUDIO_RESPONSE_BYTES or not response.content.startswith(b"RIFF"):
                    raise VoiceServiceError("语音服务返回了无效音频")
                return response.content
            except httpx.HTTPError as exc:
                logger.warning("Voice worker connection failed: %s", type(exc).__name__)
                raise VoiceServiceError("语音服务连接失败") from exc
