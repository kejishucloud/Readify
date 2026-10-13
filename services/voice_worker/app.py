"""Authorized voice cloning proxy for the upstream CosyVoice runtime.

Prerequisite: clone QwenAudio/CosyVoice (with submodules), install its official
requirements in an ISOLATED Python environment, and download the matching
model weights. This module does not bundle upstream model code or weights.

Run with a SINGLE Uvicorn worker on a protected private network. The endpoint
accepts authenticated WAV samples only, emits audio/wav, and never stores audio.
"""
from __future__ import annotations

import io
import os
import threading
import wave
from functools import lru_cache
from secrets import compare_digest

import numpy as np
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

APP = FastAPI(title="Readify Voice Worker", docs_url=None, redoc_url=None, openapi_url=None)
MODEL_LOCK = threading.Lock()
MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_SAMPLES = 24_000 * 60
EMOTIONS = {
    "calm": "用平静、自然、舒缓的语气朗读。",
    "warm": "用亲切、温柔、有感染力的语气朗读。",
    "cheerful": "用轻快、愉悦、明亮的语气朗读。",
    "serious": "用清晰、严肃、专业的语气朗读。",
}


def require_token(authorization: str | None) -> None:
    """Reject unauthenticated requests before decoding or running the model."""
    token = os.environ.get("READIFY_VOICE_WORKER_TOKEN", "")
    if not token or not authorization or not compare_digest(authorization, "Bearer " + token):
        raise HTTPException(status_code=401, detail="Unauthorized")


@lru_cache(maxsize=1)
def load_model():
    """Load upstream model lazily once; only the worker depends on its GPU stack."""
    from cosyvoice.cli.cosyvoice import AutoModel

    model_dir = os.environ.get("READIFY_COSYVOICE_MODEL_DIR", "pretrained_models/CosyVoice2-0.5B")
    return AutoModel(model_dir=model_dir, load_jit=False, load_trt=False, fp16=False)


def load_reference(data: bytes):
    """Convert a bounded, validated WAV into the 16-kHz model prompt tensor."""
    if len(data) < 44 or len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, "Invalid reference audio size")
    try:
        import torch
        import torchaudio

        with wave.open(io.BytesIO(data), "rb") as w:
            duration = w.getnframes() / max(1, w.getframerate())
            if not (3 <= duration <= 30) or w.getnchannels() not in (1, 2):
                raise HTTPException(400, "Audio must be 3-30 seconds, mono/stereo")
            if w.getsampwidth() != 2 or w.getframerate() not in range(8000, 48001):
                raise HTTPException(400, "16-bit WAV, 8-48kHz required")
            pcm = w.readframes(w.getnframes())
            samples = np.frombuffer(pcm, dtype=np.int16).copy().astype(np.float32) / 32768
            tensor = torch.from_numpy(samples).reshape(-1, w.getnchannels()).mean(dim=1, keepdim=True).T
            rate = w.getframerate()
        if rate != 16_000:
            tensor = torchaudio.functional.resample(tensor, rate, 16_000)
        return tensor
    except HTTPException:
        raise
    except (wave.Error, EOFError, ValueError) as exc:
        raise HTTPException(400, "Invalid WAV reference file") from exc


def make_wav(pcm, rate: int) -> bytes:
    """Assemble a valid PCM16 RIFF/WAVE container, not raw PCM bytes."""
    array = np.asarray(pcm, dtype=np.float32).reshape(-1)
    if array.size > MAX_SAMPLES * max(1, rate // 24000):
        raise HTTPException(status_code=413, detail="Audio output exceeded safety limit")
    data = (np.clip(array, -1, 1) * 32767).astype("<i2").tobytes()
    out = io.BytesIO()
    with wave.open(out, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(data)
    return out.getvalue()


@APP.get("/health")
def health(authorization: str | None = Header(default=None)):
    require_token(authorization)
    return {"status": "ready", "model_loaded": load_model.cache_info().currsize > 0}


@APP.post("/v1/synthesize")
def synthesize(
    text: str = Form(..., min_length=1, max_length=500),
    prompt_text: str = Form(..., max_length=600),
    mode: str = Form(default="clone"),
    style: str = Form(default="calm"),
    reference: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    require_token(authorization)
    if mode not in {"clone", "cross_language", "instruct"}:
        raise HTTPException(400, "Unsupported voice mode")
    if mode == "instruct" and style not in EMOTIONS:
        raise HTTPException(400, "Unsupported emotion")
    payload = reference.file.read(MAX_FILE_SIZE + 1)
    if len(payload) > MAX_FILE_SIZE:
        raise HTTPException(413, "Reference audio too large")
    prompt = load_reference(payload)

    try:
        with MODEL_LOCK:
            model = load_model()
            if mode == "clone":
                segments = model.inference_zero_shot(text, prompt_text, prompt, stream=False)
            elif mode == "cross_language":
                segments = model.inference_cross_lingual(text, prompt, stream=False)
            else:
                segments = model.inference_instruct2(text, EMOTIONS[style], prompt, stream=False)
            waves = [part["tts_speech"].detach().cpu().float().numpy().reshape(-1) for part in segments]
            rate = int(model.sample_rate)
        if not waves:
            raise HTTPException(503, "Model returned empty audio")
        content = make_wav(np.concatenate(waves), rate)
        return Response(content=content, media_type="audio/wav", headers={"Cache-Control": "no-store"})
    except HTTPException:
        raise
    except Exception as exc:
        # Avoid reflecting model paths, audio content and internal error details.
        raise HTTPException(status_code=503, detail="Voice synthesis unavailable") from exc


app = APP
