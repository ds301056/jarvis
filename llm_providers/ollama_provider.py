"""Ollama LLM provider — wraps existing HTTP logic."""

import json
from typing import Iterator

import requests

import config


class LLMError(Exception):
    pass


def chat(messages: list[dict], tools: list | None = None) -> dict:
    """Non-streaming chat. Returns {"content": "...", "tool_calls": [...]}."""
    url = f"{config.OLLAMA_URL}/api/chat"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise LLMError(f"Ollama request failed: {e}") from e

    msg = resp.json()["message"]
    return {
        "content": msg.get("content", ""),
        "tool_calls": msg.get("tool_calls", []),
    }


def stream_chat(messages: list[dict], tools: list | None = None) -> Iterator[dict]:
    """Streaming chat. Yields {"content": "..."}, {"tool_calls": [...]}, or {"done": True}."""
    url = f"{config.OLLAMA_URL}/api/chat"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
    try:
        resp = requests.post(url, json=payload, stream=True, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise LLMError(f"Ollama request failed: {e}") from e

    with resp:
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            msg = chunk.get("message", {})
            token = msg.get("content", "")
            if token:
                yield {"content": token}
            if msg.get("tool_calls"):
                yield {"tool_calls": msg["tool_calls"]}
            if chunk.get("done"):
                yield {"done": True}
                break


def convert_tools(ollama_tools: list[dict]) -> list[dict]:
    """Ollama tools are already in Ollama format — passthrough."""
    return ollama_tools
