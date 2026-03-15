# Building Jarvis: A Local-First Voice Assistant on 16GB

A fully local voice assistant — LLM, speech-to-text, text-to-speech, wake word detection, and a browser-based UI — running entirely on a Mac Mini M4 with 16GB of unified RAM. No cloud APIs, no subscriptions, no data leaving the machine. The constraint that should have made this impossible is what made the architecture interesting.

---

## The Constraint That Shaped Everything

The Mac Mini M4 has 16GB of unified memory shared between CPU and GPU. That's the entire budget for:

| Component | Memory Cost |
|-----------|------------|
| macOS + Python runtime | ~3 GB |
| Ollama (Llama 3.1 8B) | ~5 GB |
| TTS model (Kokoro, when loaded) | ~4.5 GB |
| Whisper STT (int8 base) | ~0.5 GB |
| **Headroom** | **~2 GB** |

There is no room for waste. A 70B parameter model would consume all 16GB on its own. A TTS model that stays resident permanently eats into LLM context window. Every architectural decision below traces back to this memory ceiling.

---

## Build Timeline

### Day 1 — Foundation & Remote Access

The first day was a dependency chain — each step gated the next:

1. **Xcode CLI tools** — required by Homebrew
2. **Homebrew** — package manager for everything else
3. **Python 3.11** — runtime for the assistant
4. **Node.js** — for the frontend build toolchain
5. **Claude Code** — AI-assisted development from day one
6. **VS Code** — remote editing via SSH

Then the LLM:

- **Ollama + Llama 3.1 8B** — chosen specifically because the 8B parameter model fits in ~5GB. The next size up (70B) would consume the entire system. Quantized 8B is the largest model that leaves room for everything else.

Remote access came next, since Jarvis runs headless:

- **Tailscale** for private mesh VPN — free tier, no port forwarding, WireGuard-encrypted
- **SSH + Termius + tmux** for persistent phone-to-Mac terminal sessions
- **ttyd** for browser-based terminal access (no app install needed on iPhone)

### Phase 1 — FastAPI Scaffold

**FastAPI** was chosen for one reason: it handles both REST and WebSocket in a single async framework. REST endpoints serve config and status. WebSocket streams real-time voice pipeline state to the browser UI.

Concerns were separated early: `main.py` owns the FastAPI app, `voice.py` owns the voice loop thread, `events.py` bridges them.

### Phase 2 — Voice Input Pipeline

**faster-whisper with int8 quantization** — the base model is ~140MB, fitting easily within the memory budget. Int8 compute type halves memory usage with negligible quality loss for voice command transcription.

The STT system was built pluggable from the start:

```python
# stt.py — backend selection
if config.STT_BACKEND == "local":
    return transcribe_local(audio_path)
elif config.STT_BACKEND == "api":
    raise NotImplementedError("API backend not yet implemented")
elif config.STT_BACKEND == "apple":
    raise NotImplementedError("Apple backend not yet implemented")
```

Three backends — `local`, `api`, `apple` — selectable via one config line. The local backend works today; cloud and Apple Speech can be swapped in without touching the voice loop.

Voice activity detection uses **RMS amplitude** with a configurable silence threshold (default 500) and a 2-second silence cutoff. Simple, no ML overhead.

A practical problem: **AirPods Bluetooth mic activation delay**. When AirPods switch from A2DP (music) to HFP (microphone) profile, there's a 1–3 second warm-up where the mic returns silence. The solution: a persistent mic stream opened once at startup, with an RMS-based warm-up loop that waits for the first non-silent frame before accepting input.

### Phase 3 — Voice Output & Frontend

#### Pluggable TTS with Three Backends

```python
# tts.py — dynamic backend import
if config.TTS_BACKEND == "kokoro":
    from tts_backends import kokoro_backend as backend
elif config.TTS_BACKEND == "chatterbox":
    from tts_backends import chatterbox_backend as backend
elif config.TTS_BACKEND == "macos":
    from tts_backends import macos_backend as backend
```

- **Kokoro 82M** — fast, natural-sounding, default choice (~4.5GB loaded)
- **Chatterbox** — higher quality, slower synthesis
- **macOS `say`** — zero-dependency fallback, no model to load

Switching backends is a one-line config change: `TTS_BACKEND = "macos"`.

#### Lazy Loading + Idle Unload — The Key Memory Optimization

The TTS model cannot stay loaded 24/7. At 4.5GB, it would leave no headroom for the LLM. The solution is a **lazy-loaded singleton with idle timeout**:

```python
# tts.py — the model loads on first request, unloads after 5 min idle
_model = None
_idle_timer = None

def _ensure_model():
    global _model, _backend, _last_used
    with _model_lock:
        if _model is None:
            _backend = _get_backend()
            _model = _backend.load()
        _last_used = time.time()
        _schedule_idle_unload()
        return _model, _backend

def _unload_model():
    global _model, _backend, _idle_timer
    with _model_lock:
        if _model is not None:
            _model = None
            _backend = None
```

First TTS request loads the model. A daemon timer resets on every synthesis call. After 5 minutes of silence, the model unloads and frees 4.5GB back to the system. Next request reloads transparently. The user never notices.

#### Sentence-Level Streaming

Waiting for the full LLM response before speaking creates 5–10 seconds of dead air. Instead, the pipeline streams at the sentence level:

1. LLM streams tokens → `stream_sentences()` buffers until sentence boundary
2. Each complete sentence goes into a `sentence_q` (max 4)
3. A TTS worker thread pulls sentences, synthesizes to PCM, pushes to `audio_q` (max 2)
4. A playback worker thread pulls PCM and writes to the speaker in 50ms slices

Three threads, two bounded queues, natural backpressure. The user hears the first sentence in ~1 second.

#### Barge-In: Two-Phase Interrupt

Natural conversation requires interruption. Barge-in detection runs on a separate mic monitor thread during TTS playback:

- **Phase 1** — Detect the user speaking over Jarvis (RMS above `BARGE_IN_THRESHOLD` of 1500, set high to ignore speaker bleed)
- **Phase 2** — Once detected, keep recording on the same mic stream until silence, capturing the full utterance

The interrupt event stops TTS playback within 50ms (one audio slice). The captured audio gets transcribed and processed as the next user input. The conversation continues without the user having to repeat themselves.

#### Frontend: React + Three.js Orb

A browser-based UI built with React and Three.js:

- Audio-reactive orb visualization with custom shaders — RMS values from the voice pipeline drive vertex displacement via the event bus
- Real-time state display (idle → listening → thinking → speaking)
- Live transcript streaming over WebSocket

#### Thread-Safe Event Bus

The voice pipeline runs in threads. FastAPI runs in an async event loop. The event bus bridges them:

```python
# events.py — thread-to-async bridge
def publish(event: dict):
    if not _subscribers or _loop is None:
        return
    for q in _subscribers:
        _loop.call_soon_threadsafe(q.put_nowait, event)
```

`call_soon_threadsafe` is the critical detail — it safely schedules the event onto the asyncio loop from any thread. WebSocket clients subscribe via async queues. The voice thread publishes RMS values, state transitions, and transcripts without ever touching async code directly.

### Phase 4 — Wake Word, Dismiss & Skills

#### Wake Word

**openwakeword** for offline "Hey Jarvis" detection — free, runs ONNX inference, minimal memory footprint. Configurable threshold (default 0.5) balances false positives vs. missed activations.

#### Keyword Dismiss

No LLM call needed to stop Jarvis. A simple string match against a configurable phrase list:

```python
DISMISS_PHRASES = ["nevermind", "stop", "shut up", "go to sleep", "cancel", ...]
```

Instant response, zero compute cost.

#### Auto-Discovered Skill System

Drop a Python file in `skills/`, it's available to the LLM:

```
skills/
├── open_app.py
├── volume_control.py
├── safari.py
├── contacts.py
├── music_control.py
├── ui_read.py
├── ui_click.py
├── ui_type.py
├── app_store.py
├── clipboard.py
├── file_search.py
├── system_info.py
├── system_settings.py
├── web_search.py
└── applescript_helpers.py
```

15 skill files. No registration, no boilerplate. The skill loader discovers them at startup and exposes them as tools to the LLM. Multi-step tool calling lets the LLM chain up to 5 tool calls per request — e.g., `ui_read` to see what's on screen, then `ui_click` to interact with it.

---

## Architecture Deep Dive: The Pluggable Pattern

Every major component follows the same pattern:

1. **Config selects the backend** — a string in `config.py`
2. **Dynamic import** — `if/elif` dispatches to the right module
3. **Unified interface** — every backend exposes the same functions (`load()`, `generate()`, etc.)

This isn't over-engineering. On 16GB, you *will* need to swap models. A smaller Whisper model releases memory for a larger LLM. A lighter TTS backend lets you run a beefier STT model. As better quantized models appear, upgrading should be a config change, not a rewrite.

**Example:** Switching TTS from Kokoro (4.5GB, high quality) to macOS `say` (0GB, decent quality) to free memory:

```python
# config.py — one line
TTS_BACKEND = "macos"
```

Everything else — lazy loading, idle unload, sentence streaming — continues to work unchanged.

---

## Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Llama 3.1 8B, not 70B | Largest model that fits in ~5GB on a 16GB system |
| Lazy-loaded TTS singleton | 4.5GB model can't stay resident 24/7 alongside the LLM |
| 5-min idle unload timer | Balances responsiveness (no reload mid-conversation) with memory recovery |
| Sentence-level TTS streaming | Sub-second first-audio latency instead of 5–10s wait |
| int8 Whisper quantization | Halves memory footprint with negligible transcription quality loss |
| Persistent mic stream | One-time AirPods Bluetooth profile switch instead of per-request 3s delay |
| Thread-safe event bus | Voice runs in threads, WebSocket in async — `call_soon_threadsafe` bridges them |
| RMS-based voice activity | Simple amplitude check, no ML model overhead for silence detection |
| Two-phase barge-in | Phase 1 detects interrupt, Phase 2 captures full utterance — no lost words |
| Auto-discovered skills | New capability = new Python file, zero registration boilerplate |
| Pluggable backends everywhere | 16GB means models will be swapped — architecture makes it a config change |
| Tailscale mesh VPN | Secure remote access without exposing ports or managing certificates |

---

## What's Next

- **RAG memory** — vector search over local documents (embedding model already configured: `nomic-embed-text`, indexer scaffolded)
- **Home Assistant integration** — voice-controlled smart home via local API
- **Claude API routing** — offload complex reasoning tasks to cloud when local 8B isn't sufficient
- **Model upgrades** — as smaller, higher-quality quantized models release, the pluggable architecture means dropping them in is trivial
