"""Ollama LLM client with streaming support and tool calling."""

import json
import re

import requests

import config

# Lazy-load skills to avoid circular imports
_tools_cache = None


def _get_tools():
    """Get Ollama tool definitions (cached)."""
    global _tools_cache
    if _tools_cache is None and config.SKILLS_ENABLED:
        from skills import get_ollama_tools
        _tools_cache = get_ollama_tools()
    return _tools_cache or []


def _build_messages(prompt: str) -> list[dict]:
    """Build the messages list for /api/chat."""
    messages = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return messages


def _chat_request(messages: list[dict], stream: bool = True, tools: list | None = None):
    """Make a request to Ollama's /api/chat endpoint."""
    url = f"{config.OLLAMA_URL}/api/chat"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": stream,
    }
    if tools:
        payload["tools"] = tools
    return requests.post(url, json=payload, stream=stream, timeout=120)


def query(prompt: str, stream: bool = True) -> str:
    """Send a prompt to Ollama and return the response. Streams to stdout by default."""
    messages = _build_messages(prompt)
    tools = _get_tools()

    if not stream:
        resp = _chat_request(messages, stream=False, tools=tools)
        resp.raise_for_status()
        data = resp.json()
        message = data["message"]

        # Handle tool calls
        if message.get("tool_calls"):
            return _handle_tool_calls_sync(messages, message, tools)

        return message.get("content", "")

    # Streaming mode
    full_response, tool_calls = _stream_response(messages, tools)

    if tool_calls:
        return _handle_tool_calls_sync(messages, {
            "role": "assistant",
            "content": "".join(full_response),
            "tool_calls": tool_calls,
        }, tools)

    print()  # newline after streaming
    return "".join(full_response)


_MAX_TOOL_ROUNDS = 5


def _execute_tool_calls(messages: list[dict], tool_calls: list):
    """Execute a list of tool calls, appending results to messages."""
    from skills import execute_tool

    for tc in tool_calls:
        func = tc["function"]
        name = func["name"]
        args = func.get("arguments", {})
        print(f"\n[executing: {name}({args})]", flush=True)
        result = execute_tool(name, args)
        print(f"[result: {result}]", flush=True)
        messages.append({"role": "tool", "content": result})


def _handle_tool_calls_sync(messages: list[dict], assistant_message: dict,
                            tools: list) -> str:
    """Execute tool calls in a loop until the LLM returns pure text."""
    messages.append(assistant_message)
    current_tool_calls = assistant_message["tool_calls"]

    for _round in range(_MAX_TOOL_ROUNDS):
        _execute_tool_calls(messages, current_tool_calls)

        # Re-query — check if LLM wants more tool calls or narrates
        resp = _chat_request(messages, stream=False, tools=tools)
        resp.raise_for_status()
        message = resp.json()["message"]

        if message.get("tool_calls"):
            messages.append(message)
            current_tool_calls = message["tool_calls"]
            continue

        # Pure text — narration
        narration = message.get("content", "")
        print(narration)
        return narration

    # Max rounds reached — return whatever text we have
    print("[max tool rounds reached]")
    return ""


def _stream_response(messages: list[dict], tools: list):
    """Stream a chat response, returning (text_tokens, tool_calls)."""
    full_response = []
    tool_calls = []

    with _chat_request(messages, stream=True, tools=tools) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            msg = chunk.get("message", {})
            token = msg.get("content", "")
            if token:
                print(token, end="", flush=True)
                full_response.append(token)
            if msg.get("tool_calls"):
                tool_calls.extend(msg["tool_calls"])
            if chunk.get("done"):
                break

    return full_response, tool_calls


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BREAK = re.compile(r"(?<=[,;:\u2014])\s+")
_MIN_CLAUSE_LEN = 30  # only split on clause breaks when buffer exceeds this


def stream_sentences(prompt: str):
    """Stream tokens from Ollama, yielding clauses/sentences for TTS.

    Splits on sentence boundaries (.!?) always, and on clause boundaries
    (,;:—) when the buffered text is long enough. This keeps TTS chunks
    small (~5-10 words) for low-latency synthesis.

    Handles tool calls internally: executes tools, re-queries the LLM,
    and streams the narration — so callers don't need to know about tools.
    """
    messages = _build_messages(prompt)
    tools = _get_tools()

    # First pass: stream response, check for tool calls
    full_response, tool_calls = _stream_response(messages, tools)

    if tool_calls:
        # Multi-step tool execution loop
        import events

        events.publish({"type": "state", "state": "acting"})

        assistant_message = {
            "role": "assistant",
            "content": "".join(full_response),
            "tool_calls": tool_calls,
        }
        messages.append(assistant_message)
        current_tool_calls = tool_calls

        for _round in range(_MAX_TOOL_ROUNDS):
            _execute_tool_calls(messages, current_tool_calls)

            # Check if LLM wants more tool calls before narrating
            next_response, next_tool_calls = _stream_response(messages, tools)

            if next_tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": "".join(next_response),
                    "tool_calls": next_tool_calls,
                })
                current_tool_calls = next_tool_calls
                continue

            # Pure text — stream it as TTS sentences
            events.publish({"type": "state", "state": "speaking"})
            combined = "".join(next_response)
            if combined.strip():
                yield from _split_text_to_sentences(combined)
            print()
            return

        # Max rounds — stream whatever the last response was
        events.publish({"type": "state", "state": "speaking"})
        yield from _stream_sentences_from_messages(messages, tools)
        return

    # No tool calls — yield sentences from the already-streamed text
    combined = "".join(full_response)
    if combined.strip():
        # Re-split the already-printed text into sentences for TTS
        yield from _split_text_to_sentences(combined)
    print()  # newline after streaming


def _stream_sentences_from_messages(messages: list[dict], tools: list):
    """Stream a chat response and yield sentence chunks for TTS."""
    buffer = ""

    with _chat_request(messages, stream=True, tools=tools) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            msg = chunk.get("message", {})
            token = msg.get("content", "")
            if token:
                print(token, end="", flush=True)
                buffer += token

            # Split buffer into sentences/clauses
            while True:
                match = _SENTENCE_END.search(buffer)
                if match:
                    sentence = buffer[: match.start() + 1].strip()
                    buffer = buffer[match.end():]
                    if sentence:
                        yield sentence
                    continue

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

    remaining = buffer.strip()
    if remaining:
        yield remaining
    print()


def _split_text_to_sentences(text: str):
    """Split already-complete text into sentence/clause chunks for TTS."""
    buffer = text
    while True:
        match = _SENTENCE_END.search(buffer)
        if match:
            sentence = buffer[: match.start() + 1].strip()
            buffer = buffer[match.end():]
            if sentence:
                yield sentence
            continue

        if len(buffer) >= _MIN_CLAUSE_LEN:
            cmatch = _CLAUSE_BREAK.search(buffer)
            if cmatch:
                clause = buffer[: cmatch.start() + 1].strip()
                buffer = buffer[cmatch.end():]
                if clause:
                    yield clause
                continue
        break

    remaining = buffer.strip()
    if remaining:
        yield remaining
