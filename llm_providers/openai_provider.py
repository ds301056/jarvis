"""OpenAI LLM provider — GPT models via the OpenAI SDK."""

import json
from typing import Iterator

import config


class LLMError(Exception):
    pass


def _get_client():
    try:
        from openai import OpenAI
    except ImportError:
        raise LLMError("openai package not installed. Run: pip install openai")
    if not config.OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY not set")
    return OpenAI(api_key=config.OPENAI_API_KEY)


def _convert_messages(messages: list[dict]) -> list[dict]:
    """Convert Ollama-format messages to OpenAI format."""
    converted = []
    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "")
        if role == "system":
            converted.append({"role": "system", "content": content})
        elif role == "user":
            converted.append({"role": "user", "content": content})
        elif role == "assistant":
            entry = {"role": "assistant", "content": content or None}
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc["function"].get("id", f"call_{tc['function']['name']}"),
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": json.dumps(tc["function"].get("arguments", {})),
                        },
                    }
                    for tc in tool_calls
                ]
            converted.append(entry)
        elif role == "tool":
            converted.append({
                "role": "tool",
                "tool_call_id": "call_tool",
                "content": content,
            })
    return converted


def convert_tools(ollama_tools: list[dict]) -> list[dict]:
    """Convert Ollama tool format to OpenAI tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "parameters": t["function"].get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for t in ollama_tools
    ]


def chat(messages: list[dict], tools: list | None = None) -> dict:
    """Non-streaming chat."""
    client = _get_client()
    kwargs = {
        "model": config.OPENAI_MODEL,
        "messages": _convert_messages(messages),
    }
    if tools:
        kwargs["tools"] = convert_tools(tools)

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        raise LLMError(f"OpenAI API error: {e}") from e

    choice = response.choices[0].message
    content = choice.content or ""
    tool_calls = []
    if choice.tool_calls:
        for tc in choice.tool_calls:
            tool_calls.append({
                "function": {
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {},
                    "id": tc.id,
                }
            })
    return {"content": content, "tool_calls": tool_calls}


def stream_chat(messages: list[dict], tools: list | None = None) -> Iterator[dict]:
    """Streaming chat with delta tool call accumulation."""
    client = _get_client()
    kwargs = {
        "model": config.OPENAI_MODEL,
        "messages": _convert_messages(messages),
        "stream": True,
    }
    if tools:
        kwargs["tools"] = convert_tools(tools)

    try:
        stream = client.chat.completions.create(**kwargs)
    except Exception as e:
        raise LLMError(f"OpenAI streaming error: {e}") from e

    # Accumulate tool call deltas
    pending_tools: dict[int, dict] = {}

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue

        if delta.content:
            yield {"content": delta.content}

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in pending_tools:
                    pending_tools[idx] = {
                        "function": {
                            "name": "",
                            "arguments": "",
                            "id": tc_delta.id or "",
                        }
                    }
                if tc_delta.function:
                    if tc_delta.function.name:
                        pending_tools[idx]["function"]["name"] += tc_delta.function.name
                    if tc_delta.function.arguments:
                        pending_tools[idx]["function"]["arguments"] += tc_delta.function.arguments

        finish = chunk.choices[0].finish_reason if chunk.choices else None
        if finish == "tool_calls":
            # Emit all accumulated tool calls
            tool_calls = []
            for idx in sorted(pending_tools):
                tc = pending_tools[idx]
                try:
                    tc["function"]["arguments"] = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, TypeError):
                    tc["function"]["arguments"] = {}
                tool_calls.append(tc)
            yield {"tool_calls": tool_calls}
            pending_tools.clear()
        elif finish == "stop":
            yield {"done": True}
