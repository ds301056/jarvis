import asyncio
import json
import threading

import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

import config
import events

app = FastAPI()


@app.on_event("startup")
async def startup():
    """Store event loop ref and launch voice loop in background thread."""
    events.set_loop(asyncio.get_running_loop())

    from voice import voice_loop
    threading.Thread(target=voice_loop, daemon=True).start()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    q = events.subscribe()
    try:
        while True:
            event = await q.get()
            await ws.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    finally:
        events.unsubscribe(q)


@app.get("/api/status")
def root():
    return {"status": "ok", "message": "Jarvis is running"}


@app.get("/api/voice/status")
def voice_status():
    """Return the current voice pipeline configuration."""
    return {
        "stt_backend": config.STT_BACKEND,
        "whisper_model": config.WHISPER_MODEL,
        "ollama_model": config.OLLAMA_MODEL,
        "tts_enabled": config.TTS_ENABLED,
        "tts_backend": config.TTS_BACKEND,
    }


@app.get("/api/tts/status")
def tts_status():
    """Return the current TTS model status."""
    from tts import model_status
    return model_status()


@app.get("/api/llm/status")
def llm_status():
    """Check if Ollama is reachable and the configured model is available."""
    try:
        resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {
            "ollama": "connected",
            "configured_model": config.OLLAMA_MODEL,
            "model_available": config.OLLAMA_MODEL in models,
            "available_models": models,
        }
    except requests.ConnectionError:
        return {"ollama": "unreachable", "configured_model": config.OLLAMA_MODEL}


# Serve frontend static files (production build) — must be last
import os
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
