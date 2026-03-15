"""Thread-safe pub/sub event bus for streaming voice pipeline state to WebSocket clients."""

import asyncio
import json
from typing import Any

_subscribers: list[asyncio.Queue] = []
_loop: asyncio.AbstractEventLoop | None = None


def set_loop(loop: asyncio.AbstractEventLoop):
    """Store the asyncio event loop reference (call from FastAPI startup)."""
    global _loop
    _loop = loop


def has_subscribers() -> bool:
    return len(_subscribers) > 0


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue):
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


def publish(event: dict):
    """Publish an event from any thread. Safe to call from voice pipeline threads."""
    if not _subscribers or _loop is None:
        return
    for q in _subscribers:
        try:
            _loop.call_soon_threadsafe(q.put_nowait, event)
        except (asyncio.QueueFull, RuntimeError):
            pass  # drop if consumer is slow or loop is closed
