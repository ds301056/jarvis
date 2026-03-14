"""Ollama LLM client with streaming support."""

import json
import re

import requests

import config


def query(prompt: str, stream: bool = True) -> str:
    """Send a prompt to Ollama and return the response. Streams to stdout by default."""
    url = f"{config.OLLAMA_URL}/api/generate"
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
    }

    if not stream:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"]

    # Streaming mode
    full_response = []
    with requests.post(url, json=payload, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                print(token, end="", flush=True)
                full_response.append(token)
                if chunk.get("done"):
                    break

    print()  # newline after streaming
    return "".join(full_response)


def stream_sentences(prompt: str):
    """Stream tokens from Ollama, yielding complete sentences as they form.

    Prints tokens to stdout for visual feedback, same as query().
    Yields each sentence once a sentence-ending boundary is detected.
    """
    url = f"{config.OLLAMA_URL}/api/generate"
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
    }

    sentence_end = re.compile(r"(?<=[.!?])\s+")
    buffer = ""

    with requests.post(url, json=payload, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("response", "")
            print(token, end="", flush=True)
            buffer += token

            # Split on sentence boundaries
            while True:
                match = sentence_end.search(buffer)
                if not match:
                    break
                sentence = buffer[: match.start() + 1].strip()
                buffer = buffer[match.end():]
                if sentence:
                    yield sentence

            if chunk.get("done"):
                break

    # Yield any remaining text
    remaining = buffer.strip()
    if remaining:
        yield remaining
    print()  # newline after streaming
