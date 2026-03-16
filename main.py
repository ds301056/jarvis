import asyncio
import json
import subprocess
import threading

import requests
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import events

app = FastAPI()


class ChatRequest(BaseModel):
    text: str


@app.on_event("startup")
async def startup():
    """Store event loop ref and launch voice loop in background thread."""
    events.set_loop(asyncio.get_running_loop())

    from voice import voice_loop
    threading.Thread(target=voice_loop, daemon=True).start()

    # Start file indexer daemon
    if config.SEARCH_ENABLED:
        from indexer import start_indexer
        threading.Thread(target=start_indexer, daemon=True).start()


@app.websocket("/ws/voice")
async def websocket_voice(ws: WebSocket):
    """WebSocket endpoint for phone-based voice I/O."""
    if not config.WEB_VOICE_ENABLED:
        await ws.close(code=1008, reason="Web voice disabled")
        return
    from web_voice import WebVoiceHandler
    await ws.accept()
    handler = WebVoiceHandler(ws)
    await handler.run()


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


# ── Chat API endpoint ─────────────────────────────────────────────────

@app.post("/api/chat")
def api_chat(req: ChatRequest):
    """Accept text input, run through LLM pipeline, stream responses via WebSocket."""
    text = req.text.strip()
    if not text:
        return {"error": "Empty message"}

    def _run():
        from llm import stream_sentences
        events.publish({"type": "state", "state": "thinking"})
        events.publish({"type": "transcript", "role": "user", "text": text, "final": True})
        full_response = []
        events.publish({"type": "state", "state": "speaking"})
        for sentence in stream_sentences(text):
            full_response.append(sentence)
            events.publish({"type": "token", "text": sentence})
        response_text = " ".join(full_response)
        if response_text:
            events.publish({"type": "transcript", "role": "assistant", "text": response_text, "final": True})
        events.publish({"type": "state", "state": "idle"})

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "ok"}


# ── Settings API endpoints ────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    """Return current settings with API keys masked."""
    from settings import load_settings, mask_key
    s = load_settings()
    return {
        "llm_provider": s.get("llm_provider", config.LLM_PROVIDER),
        "ollama_model": s.get("ollama_model", config.OLLAMA_MODEL),
        "anthropic_api_key": mask_key(s.get("anthropic_api_key", config.ANTHROPIC_API_KEY)),
        "anthropic_model": s.get("anthropic_model", config.ANTHROPIC_MODEL),
        "openai_api_key": mask_key(s.get("openai_api_key", config.OPENAI_API_KEY)),
        "openai_model": s.get("openai_model", config.OPENAI_MODEL),
        "gemini_api_key": mask_key(s.get("gemini_api_key", config.GEMINI_API_KEY)),
        "gemini_model": s.get("gemini_model", config.GEMINI_MODEL),
        "tts_backend": s.get("tts_backend", config.TTS_BACKEND),
        "stt_backend": s.get("stt_backend", config.STT_BACKEND),
    }


@app.post("/api/settings")
def save_settings(body: dict):
    """Save settings and hot-patch config module."""
    from settings import save_settings as _save
    _save(body)
    return {"status": "ok"}


@app.get("/api/llm/models")
def llm_models(provider: str = Query("ollama")):
    """Return available models for a given provider."""
    if provider == "ollama":
        try:
            resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            return {"models": [m["name"] for m in resp.json().get("models", [])]}
        except requests.RequestException:
            return {"models": [], "error": "Ollama unreachable"}
    elif provider == "anthropic":
        return {"models": [
            "claude-sonnet-4-20250514",
            "claude-haiku-4-5-20251001",
            "claude-opus-4-20250514",
        ]}
    elif provider == "openai":
        return {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]}
    elif provider == "gemini":
        return {"models": ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"]}
    return {"models": []}


# ── Search API endpoints ─────────────────────────────────────────────

@app.get("/api/search")
def api_search(q: str = Query(""), limit: int = Query(10, ge=1, le=50)):
    """Hybrid keyword + semantic file search."""
    if not q.strip():
        return {"results": [], "query": q}
    from indexer.search import search
    results = search(q, limit=limit)
    return {"results": results, "query": q}


@app.get("/api/search/status")
def search_status():
    """Return indexer status."""
    from indexer import is_indexing, last_scan_time
    from indexer.db import file_count
    return {
        "enabled": config.SEARCH_ENABLED,
        "indexed_files": file_count() if config.SEARCH_ENABLED else 0,
        "last_scan": last_scan_time(),
        "indexing": is_indexing(),
    }


@app.post("/api/search/reindex")
def search_reindex():
    """Trigger an immediate re-index."""
    if not config.SEARCH_ENABLED:
        return {"status": "disabled"}
    from indexer import trigger_reindex
    threading.Thread(target=trigger_reindex, daemon=True).start()
    return {"status": "started"}


@app.get("/api/files/open")
def open_file(path: str = Query("")):
    """Open a file in the default macOS application."""
    if not path:
        return {"error": "No path provided"}
    import os
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return {"error": "File not found"}
    subprocess.run(["open", path])
    return {"status": "opened", "path": path}


# Serve frontend static files (production build) — must be last
import os
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
