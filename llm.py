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


_ACTION_KEYWORDS = re.compile(
    r'\b(open|launch|start|run|close|quit|'
    r'search|find|look\s+up|google|'
    r'play|pause|stop|skip|next|previous|'
    r'volume|mute|unmute|louder|quieter|'
    r'click|tap|press|type|scroll|select|'
    r'call|dial|text|message|send|'
    r'set|change|turn\s+on|turn\s+off|enable|disable|toggle|'
    r'copy|paste|clipboard|'
    r'read|show|what\'s\s+on\s+screen|'
    r'navigate|go\s+to|visit|browse|'
    r'download|install|update|'
    r'brightness|dark\s+mode|night\s+shift|'
    r'timer|alarm|remind|'
    r'file|folder|document)\b', re.IGNORECASE
)


def _needs_tools(prompt: str) -> bool:
    """Check if a prompt likely needs tool access based on action keywords."""
    if not config.SKILLS_ENABLED:
        return False
    return bool(_ACTION_KEYWORDS.search(prompt))


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
    tools = _get_tools() if _needs_tools(prompt) else []

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


def _stream_response_detecting_tools(messages: list[dict], tools: list,
                                     tool_calls_out: list):
    """Stream a chat response, yielding sentences in real-time for TTS.

    If tool_calls are detected, appends them to tool_calls_out and returns
    without yielding any sentences. Otherwise, yields sentence/clause chunks
    as they form during streaming.
    """
    buffer = ""
    pending_text = []  # text tokens collected before we know if tools are coming

    with _chat_request(messages, stream=True, tools=tools) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            msg = chunk.get("message", {})
            token = msg.get("content", "")

            if msg.get("tool_calls"):
                # Tool call detected — collect all tool calls and bail out
                tool_calls_out.extend(msg["tool_calls"])
                # Print any buffered text but don't yield sentences
                if token:
                    print(token, end="", flush=True)
                # Drain remaining chunks for more tool calls
                for line2 in resp.iter_lines():
                    if not line2:
                        continue
                    chunk2 = json.loads(line2)
                    msg2 = chunk2.get("message", {})
                    t2 = msg2.get("content", "")
                    if t2:
                        print(t2, end="", flush=True)
                    if msg2.get("tool_calls"):
                        tool_calls_out.extend(msg2["tool_calls"])
                    if chunk2.get("done"):
                        break
                # Append assistant message with tool calls to messages
                full_text = "".join(pending_text) + token
                messages.append({
                    "role": "assistant",
                    "content": full_text,
                    "tool_calls": tool_calls_out[:],
                })
                return

            if token:
                print(token, end="", flush=True)
                pending_text.append(token)
                buffer += token

            # Split buffer into sentences/clauses and yield
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

    # Yield any remaining text in the buffer
    remaining = buffer.strip()
    if remaining:
        yield remaining

    # Append assistant message to messages for conversation continuity
    full_text = "".join(pending_text)
    if full_text:
        messages.append({"role": "assistant", "content": full_text})
    print()


def stream_sentences(prompt: str):
    """Stream tokens from Ollama, yielding clauses/sentences for TTS.

    Splits on sentence boundaries (.!?) always, and on clause boundaries
    (,;:—) when the buffered text is long enough. This keeps TTS chunks
    small (~5-10 words) for low-latency synthesis.

    Handles tool calls internally: executes tools, re-queries the LLM,
    and streams the narration — so callers don't need to know about tools.
    """
    messages = _build_messages(prompt)
    tools = _get_tools() if _needs_tools(prompt) else []

    # Stream response, yielding sentences in real-time
    tool_calls = []
    yield from _stream_response_detecting_tools(messages, tools, tool_calls)

    if not tool_calls:
        return  # text path done — sentences already yielded in real-time

    # Tool path: execute tools, then stream narration
    import events
    events.publish({"type": "state", "state": "acting"})

    for _round in range(_MAX_TOOL_ROUNDS):
        _execute_tool_calls(messages, tool_calls)
        tool_calls = []
        yield from _stream_response_detecting_tools(messages, tools, tool_calls)
        if not tool_calls:
            events.publish({"type": "state", "state": "speaking"})
            return

    # Max rounds — stream whatever we can
    events.publish({"type": "state", "state": "speaking"})
    yield from _stream_sentences_from_messages(messages, tools)


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
