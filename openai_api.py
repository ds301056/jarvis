"""OpenAI-compatible API server for local TTS (Kokoro) and STT (faster-whisper).

Exposes endpoints that Open WebUI (and other OpenAI-compatible clients) can use
for text-to-speech and speech-to-text without paying for OpenAI APIs.

Usage:
    python openai_api.py              # default: 0.0.0.0:8100
    python openai_api.py --port 9000  # custom port
"""

import argparse
import io
import os
import tempfile
import wave

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

import config
import tts

app = FastAPI(title="Jarvis OpenAI-Compatible Audio API")

# ── Cached Whisper model (singleton) ─────────────────────────────────

_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        print(f"[STT] Loading faster-whisper ({config.WHISPER_MODEL})...")
        _whisper_model = WhisperModel(config.WHISPER_MODEL, compute_type="int8")
        print("[STT] Ready")
    return _whisper_model


# ── Request models ───────────────────────────────────────────────────

class SpeechRequest(BaseModel):
    input: str
    model: str = "kokoro"
    voice: str = "af_heart"
    response_format: str = "wav"
    speed: float = 1.0


# ── Startup ──────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    tts.warm_up()


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "kokoro", "object": "model", "created": 0, "owned_by": "local"},
            {"id": "whisper-base", "object": "model", "created": 0, "owned_by": "local"},
        ],
    }


@app.post("/v1/audio/speech")
def create_speech(req: SpeechRequest):
    pcm_bytes = tts.synthesize(req.input)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(config.TTS_SAMPLE_RATE)
        wf.writeframes(pcm_bytes)
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.post("/v1/audio/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form("whisper-base"),
    language: str = Form(None),
    response_format: str = Form("json"),
):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        tmp.write(await file.read())
        tmp.close()
        whisper = _get_whisper()
        segments, _ = whisper.transcribe(tmp.name)
        text = " ".join(seg.text for seg in segments).strip()
        return {"text": text}
    finally:
        os.unlink(tmp.name)


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenAI-compatible audio API")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    print(f"Starting OpenAI-compatible audio API on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
