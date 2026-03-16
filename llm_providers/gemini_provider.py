"""Google Gemini LLM provider via the Google GenAI SDK."""

import json
from typing import Iterator

import config


class LLMError(Exception):
    pass


def _get_client():
    try:
        from google import genai
    except ImportError:
        raise LLMError("google-genai package not installed. Run: pip install google-genai")
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY not set")
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _convert_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert Ollama-format messages to Gemini format.

    Returns (system_instruction, contents).
    """
    system = ""
    contents = []
    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "")
        if role == "system":
            system = content
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            parts = []
            if content:
                parts.append({"text": content})
            for tc in msg.get("tool_calls", []):
                func = tc["function"]
                parts.append({
                    "function_call": {
                        "name": func["name"],
                        "args": func.get("arguments", {}),
                    }
                })
            contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            contents.append({
                "role": "user",
                "parts": [{"function_response": {"name": "tool", "response": {"result": content}}}],
            })
    return system, contents


def convert_tools(ollama_tools: list[dict]) -> list[dict]:
    """Convert Ollama tool format to Gemini function declarations."""
    declarations = []
    for t in ollama_tools:
        func = t["function"]
        declarations.append({
            "name": func["name"],
            "description": func.get("description", ""),
            "parameters": func.get("parameters", {"type": "object", "properties": {}}),
        })
    return declarations


def chat(messages: list[dict], tools: list | None = None) -> dict:
    """Non-streaming chat."""
    from google.genai import types

    client = _get_client()
    system, contents = _convert_messages(messages)
    kwargs = {"model": config.GEMINI_MODEL, "contents": contents}
    config_kwargs = {}
    if system:
        config_kwargs["system_instruction"] = system
    if tools:
        kwargs["tools"] = [types.Tool(function_declarations=convert_tools(tools))]
    if config_kwargs:
        kwargs["config"] = types.GenerateContentConfig(**config_kwargs)

    try:
        response = client.models.generate_content(**kwargs)
    except Exception as e:
        raise LLMError(f"Gemini API error: {e}") from e

    content = ""
    tool_calls = []
    for part in response.candidates[0].content.parts:
        if part.text:
            content += part.text
        if part.function_call:
            fc = part.function_call
            tool_calls.append({
                "function": {
                    "name": fc.name,
                    "arguments": dict(fc.args) if fc.args else {},
                }
            })
    return {"content": content, "tool_calls": tool_calls}


def stream_chat(messages: list[dict], tools: list | None = None) -> Iterator[dict]:
    """Streaming chat."""
    from google.genai import types

    client = _get_client()
    system, contents = _convert_messages(messages)
    kwargs = {"model": config.GEMINI_MODEL, "contents": contents}
    config_kwargs = {}
    if system:
        config_kwargs["system_instruction"] = system
    if tools:
        kwargs["tools"] = [types.Tool(function_declarations=convert_tools(tools))]
    if config_kwargs:
        kwargs["config"] = types.GenerateContentConfig(**config_kwargs)

    try:
        for chunk in client.models.generate_content_stream(**kwargs):
            for part in chunk.candidates[0].content.parts:
                if part.text:
                    yield {"content": part.text}
                if part.function_call:
                    fc = part.function_call
                    yield {"tool_calls": [{
                        "function": {
                            "name": fc.name,
                            "arguments": dict(fc.args) if fc.args else {},
                        }
                    }]}
        yield {"done": True}
    except Exception as e:
        raise LLMError(f"Gemini streaming error: {e}") from e
