import asyncio
import json
import subprocess
import threading

import requests
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
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
