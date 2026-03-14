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


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BREAK = re.compile(r"(?<=[,;:\u2014])\s+")
_MIN_CLAUSE_LEN = 30  # only split on clause breaks when buffer exceeds this


def stream_sentences(prompt: str):
    """Stream tokens from Ollama, yielding clauses/sentences for TTS.

    Splits on sentence boundaries (.!?) always, and on clause boundaries
    (,;:—) when the buffered text is long enough. This keeps TTS chunks
    small (~5-10 words) for low-latency synthesis.
    """
    url = f"{config.OLLAMA_URL}/api/generate"
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
    }

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

            # Always split on sentence boundaries
            while True:
                match = _SENTENCE_END.search(buffer)
                if match:
                    sentence = buffer[: match.start() + 1].strip()
                    buffer = buffer[match.end():]
                    if sentence:
                        yield sentence
                    continue

                # Split on clause boundaries if buffer is long enough
                if len(buffer) >= _MIN_CLAUSE_LEN:
                    cmatch = _CLAUSE_BREAK.search(buffer)
                    if cmatch:
                        clause = buffer[: cmatch.start() + 1].strip()
                        buffer = buffer[cmatch.end():]
                        if clause:
                            yield clause
                        continue
                break

            if chunk.get("done"):
                break

    # Yield any remaining text
    remaining = buffer.strip()
    if remaining:
        yield remaining
    print()  # newline after streaming
