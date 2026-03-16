"""Anthropic LLM provider — Claude models via the Anthropic SDK."""

from typing import Iterator

import config


class LLMError(Exception):
    pass


def _get_client():
    try:
        import anthropic
    except ImportError:
        raise LLMError("anthropic package not installed. Run: pip install anthropic")
    if not config.ANTHROPIC_API_KEY:
        raise LLMError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _convert_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert Ollama-format messages to Anthropic format.

    Returns (system_prompt, messages_without_system).
    """
    system = ""
    converted = []
    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "")
        if role == "system":
            system = content
        elif role == "user":
            converted.append({"role": "user", "content": content})
        elif role == "assistant":
            blocks = []
            if content:
                blocks.append({"type": "text", "text": content})
            for tc in msg.get("tool_calls", []):
                func = tc["function"]
                blocks.append({
                    "type": "tool_use",
                    "id": func.get("id", f"tool_{func['name']}"),
                    "name": func["name"],
                    "input": func.get("arguments", {}),
                })
            converted.append({"role": "assistant", "content": blocks or content})
        elif role == "tool":
            # Anthropic expects tool results as user messages with tool_result blocks
            converted.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "tool_call", "content": content}],
            })
    return system, converted


def convert_tools(ollama_tools: list[dict]) -> list[dict]:
    """Convert Ollama tool format to Anthropic tool format."""
    tools = []
    for t in ollama_tools:
        func = t["function"]
        tools.append({
            "name": func["name"],
            "description": func.get("description", ""),
            "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
        })
    return tools


def chat(messages: list[dict], tools: list | None = None) -> dict:
    """Non-streaming chat."""
    client = _get_client()
    system, conv = _convert_messages(messages)
    kwargs = {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": 4096,
        "messages": conv,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = convert_tools(tools)

    try:
        response = client.messages.create(**kwargs)
    except Exception as e:
        raise LLMError(f"Anthropic API error: {e}") from e

    content = ""
    tool_calls = []
    for block in response.content:
        if block.type == "text":
            content += block.text
        elif block.type == "tool_use":
            tool_calls.append({
                "function": {
                    "name": block.name,
                    "arguments": block.input,
                    "id": block.id,
                }
            })
    return {"content": content, "tool_calls": tool_calls}


def stream_chat(messages: list[dict], tools: list | None = None) -> Iterator[dict]:
    """Streaming chat."""
    client = _get_client()
    system, conv = _convert_messages(messages)
    kwargs = {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": 4096,
        "messages": conv,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = convert_tools(tools)

    try:
        with client.messages.stream(**kwargs) as stream:
            current_tool = None
            for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        current_tool = {
                            "function": {
                                "name": block.name,
                                "arguments": {},
                                "id": block.id,
                            }
                        }
                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield {"content": delta.text}
                    elif delta.type == "input_json_delta" and current_tool:
                        # Accumulate JSON string — will parse at block_stop
                        prev = current_tool.get("_json_str", "")
                        current_tool["_json_str"] = prev + delta.partial_json
                elif event.type == "content_block_stop":
                    if current_tool:
                        import json
                        json_str = current_tool.pop("_json_str", "{}")
                        try:
                            current_tool["function"]["arguments"] = json.loads(json_str)
                        except json.JSONDecodeError:
                            current_tool["function"]["arguments"] = {}
                        yield {"tool_calls": [current_tool]}
                        current_tool = None
                elif event.type == "message_stop":
                    yield {"done": True}
    except Exception as e:
        raise LLMError(f"Anthropic streaming error: {e}") from e
