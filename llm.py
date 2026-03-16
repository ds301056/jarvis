"""LLM client with streaming support, tool calling, and pluggable providers."""

import re

import config

# Lazy-load skills to avoid circular imports
_tools_cache = None
_tools_provider = None  # track which provider the cache was built for


def _get_provider():
    """Return the provider module for the current LLM_PROVIDER setting."""
    provider = config.LLM_PROVIDER
    if provider == "ollama":
        from llm_providers import ollama_provider as mod
    elif provider == "anthropic":
        from llm_providers import anthropic_provider as mod
    elif provider == "openai":
        from llm_providers import openai_provider as mod
    elif provider == "gemini":
        from llm_providers import gemini_provider as mod
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return mod


def _get_tools():
    """Get tool definitions in the current provider's format (cached, invalidated on provider change)."""
    global _tools_cache, _tools_provider
    current = config.LLM_PROVIDER
    if _tools_cache is None or _tools_provider != current:
        if config.SKILLS_ENABLED:
            from skills import get_ollama_tools
            ollama_tools = get_ollama_tools()
            provider = _get_provider()
            _tools_cache = provider.convert_tools(ollama_tools)
            _tools_provider = current
        else:
            _tools_cache = []
            _tools_provider = current
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
    """Build the messages list for chat."""
    messages = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return messages


def query(prompt: str, stream: bool = True) -> str:
    """Send a prompt and return the response. Streams to stdout by default."""
    provider = _get_provider()
    messages = _build_messages(prompt)
    tools = _get_tools() if _needs_tools(prompt) else []

    if not stream:
        result = provider.chat(messages, tools=tools or None)
        if result.get("tool_calls"):
            return _handle_tool_calls_sync(messages, {
                "role": "assistant",
                "content": result["content"],
                "tool_calls": result["tool_calls"],
            }, tools)
        return result.get("content", "")

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
    provider = _get_provider()
    messages.append(assistant_message)
    current_tool_calls = assistant_message["tool_calls"]

    for _round in range(_MAX_TOOL_ROUNDS):
        _execute_tool_calls(messages, current_tool_calls)

        result = provider.chat(messages, tools=tools or None)

        if result.get("tool_calls"):
            messages.append({
                "role": "assistant",
                "content": result["content"],
                "tool_calls": result["tool_calls"],
            })
            current_tool_calls = result["tool_calls"]
            continue

        narration = result.get("content", "")
        print(narration)
        return narration

    print("[max tool rounds reached]")
    return ""


def _stream_response(messages: list[dict], tools: list):
    """Stream a chat response, returning (text_tokens, tool_calls)."""
    provider = _get_provider()
    full_response = []
    tool_calls = []

    for chunk in provider.stream_chat(messages, tools=tools or None):
        if "content" in chunk:
            token = chunk["content"]
            print(token, end="", flush=True)
            full_response.append(token)
        if "tool_calls" in chunk:
            tool_calls.extend(chunk["tool_calls"])
        if chunk.get("done"):
            break

    return full_response, tool_calls


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BREAK = re.compile(r"(?<=[,;:\u2014])\s+")
_MIN_CLAUSE_LEN = 30  # only split on clause breaks when buffer exceeds this


def _split_buffer(buffer: str):
    """Try to split a sentence or clause from the front of buffer.

    Returns (chunk, remaining_buffer) or (None, buffer) if no split found.
    """
    match = _SENTENCE_END.search(buffer)
    if match:
        sentence = buffer[: match.start() + 1].strip()
        remaining = buffer[match.end():]
        if sentence:
            return sentence, remaining

    if len(buffer) >= _MIN_CLAUSE_LEN:
        cmatch = _CLAUSE_BREAK.search(buffer)
        if cmatch:
            clause = buffer[: cmatch.start() + 1].strip()
            remaining = buffer[cmatch.end():]
            if clause:
                return clause, remaining

    return None, buffer


def _stream_response_detecting_tools(messages: list[dict], tools: list,
                                     tool_calls_out: list):
    """Stream a chat response, yielding sentences in real-time for TTS.

    If tool_calls are detected, appends them to tool_calls_out and returns
    without yielding any sentences. Otherwise, yields sentence/clause chunks
    as they form during streaming.
    """
    provider = _get_provider()
    buffer = ""
    pending_text = []
    got_tool = False

    for chunk in provider.stream_chat(messages, tools=tools or None):
        if "tool_calls" in chunk:
            tool_calls_out.extend(chunk["tool_calls"])
            got_tool = True
            continue

        token = chunk.get("content", "")
        if token:
            print(token, end="", flush=True)
            if got_tool:
                # Already in tool mode — just print, don't yield
                continue
            pending_text.append(token)
            buffer += token

        if not got_tool:
            # Split buffer into sentences/clauses and yield
            while True:
                piece, buffer = _split_buffer(buffer)
                if piece is None:
                    break
                yield piece

        if chunk.get("done"):
            break

    if got_tool:
        # Append assistant message with tool calls
        full_text = "".join(pending_text)
        messages.append({
            "role": "assistant",
            "content": full_text,
            "tool_calls": tool_calls_out[:],
        })
        return

    # Yield any remaining text in the buffer
    remaining = buffer.strip()
    if remaining:
        yield remaining

    # Append assistant message for conversation continuity
    full_text = "".join(pending_text)
    if full_text:
        messages.append({"role": "assistant", "content": full_text})
    print()


def stream_sentences(prompt: str):
    """Stream tokens from the LLM, yielding clauses/sentences for TTS.

    Splits on sentence boundaries (.!?) always, and on clause boundaries
    (,;:—) when the buffered text is long enough. This keeps TTS chunks
    small (~5-10 words) for low-latency synthesis.

    Handles tool calls internally: executes tools, re-queries the LLM,
    and streams the narration — so callers don't need to know about tools.
    """
    messages = _build_messages(prompt)
    tools = _get_tools() if _needs_tools(prompt) else []

    tool_calls = []
    yield from _stream_response_detecting_tools(messages, tools, tool_calls)

    if not tool_calls:
        return

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

    events.publish({"type": "state", "state": "speaking"})
    yield from _stream_sentences_from_messages(messages, tools)


def _stream_sentences_from_messages(messages: list[dict], tools: list):
    """Stream a chat response and yield sentence chunks for TTS."""
    provider = _get_provider()
    buffer = ""

    for chunk in provider.stream_chat(messages, tools=tools or None):
        token = chunk.get("content", "")
        if token:
            print(token, end="", flush=True)
            buffer += token

        while True:
            piece, buffer = _split_buffer(buffer)
            if piece is None:
                break
            yield piece

        if chunk.get("done"):
            break

    remaining = buffer.strip()
    if remaining:
        yield remaining
    print()
