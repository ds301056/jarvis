"""Ollama embedding wrapper — batch embed via /api/embed."""

import requests
import config


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts via Ollama. Returns list of float vectors."""
    if not texts:
        return []

    all_embeddings = []
    batch_size = config.SEARCH_BATCH_SIZE

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = requests.post(
            f"{config.OLLAMA_URL}/api/embed",
            json={"model": config.SEARCH_EMBEDDING_MODEL, "input": batch},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        all_embeddings.extend(data["embeddings"])

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]


def ensure_model():
    """Pull the embedding model if not already available."""
    try:
        resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        model = config.SEARCH_EMBEDDING_MODEL
        # Check both with and without :latest tag
        if model not in models and f"{model}:latest" not in models:
            print(f"[indexer] Pulling embedding model: {model}")
            requests.post(
                f"{config.OLLAMA_URL}/api/pull",
                json={"name": model},
                timeout=600,
            )
            print(f"[indexer] Model {model} ready")
    except requests.ConnectionError:
        print("[indexer] WARNING: Ollama not reachable, embeddings will be skipped")
