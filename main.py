import requests
from fastapi import FastAPI

import config

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok", "message": "Jarvis is running"}


@app.get("/voice/status")
def voice_status():
    """Return the current voice pipeline configuration."""
    return {
        "stt_backend": config.STT_BACKEND,
        "whisper_model": config.WHISPER_MODEL,
        "ollama_model": config.OLLAMA_MODEL,
    }


@app.get("/llm/status")
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
