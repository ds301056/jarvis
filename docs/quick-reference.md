# Jarvis Quick Reference

> Concise cheat sheet for running, extending, and troubleshooting Jarvis.

---

## Remote Access (Web Terminal)

Access a full terminal from any browser (no SSH app needed):

```bash
# Start ttyd (from Mac terminal or SSH)
~/cc-remote.sh
```

Open in Safari on your phone:
```
https://100.81.175.94:7681
```

Accept the self-signed certificate warning (Advanced → Continue).

**iPhone tip:** Safari's on-screen keyboard doesn't show a Return key in ttyd. Tap the **≡** (hamburger) menu in the top-left of the ttyd page for a toolbar with Return, Ctrl, Alt, Tab, and arrow keys.

**Stop:** Press `Ctrl+C` in the terminal where `cc-remote.sh` is running, or kill the tmux session:
```bash
tmux kill-session -t cc-remote
```

**Restart:** Just run `~/cc-remote.sh` again.

---

## Starting Jarvis

```bash
# 1. Activate the virtual environment
cd ~/jarvis
source venv/bin/activate

# 2. Start Ollama (if not already running)
ollama serve            # runs in background; or use the macOS app

# 3. Pull / verify the model
ollama list             # should show llama3.1:8b
ollama pull llama3.1:8b # if missing

# 4. Start Jarvis (FastAPI + voice loop)
uvicorn main:app --reload
```

The server starts on **http://localhost:8000**. The voice loop runs automatically as a background thread.

### Frontend (Orb UI)

Open **http://localhost:8000** in a browser to see the 3D orb interface. It connects via WebSocket and shows:
- **Idle** — orb resting
- **Listening** — orb reacting to mic input
- **Thinking** — orb processing
- **Acting** — orb executing a skill (tool call)
- **Speaking** — orb pulsing with TTS output

For frontend development:
```bash
cd ~/jarvis/frontend
npm install
npm run dev        # dev server on http://localhost:5173 (proxies to FastAPI)
npm run build      # build to dist/ (served by FastAPI at /)
```

---

## Voice Commands

| Say this | What happens |
|----------|-------------|
| "Hey Jarvis" | Wake word — activates listening |
| "Open Safari" | Opens the app |
| "Set volume to 50%" | Changes system volume |
| "What time is it?" | Returns current time |
| "Search for Python tutorials" | Google search in Safari |
| "Go to General in Settings" | Opens Settings > General (multi-step: read UI → click) |
| "Call John" | Finds John in Contacts, initiates call |
| "Play some music" | Controls Apple Music |
| "What's on my clipboard?" | Reads clipboard contents |
| "Nevermind" / "Stop" | Dismiss — returns to wake word listening |
| (speak while Jarvis is talking) | Barge-in — interrupts and listens to you |

---

## Skills System

Jarvis uses **skills** — tools the LLM can call to take actions. The LLM decides when to use a skill vs. just talk.

### Current Skills (13)

| Skill | What it does | File |
|-------|-------------|------|
| `open_app` | Launch/switch to a macOS app | `skills/open_app.py` |
| `volume_control` | Set volume, mute/unmute | `skills/volume_control.py` |
| `system_info` | Time, date, uptime, memory | `skills/system_info.py` |
| `clipboard` | Read/write clipboard | `skills/clipboard.py` |
| `web_search` | Open URL or Google search | `skills/web_search.py` |
| `music_control` | Play/pause/skip in Apple Music | `skills/music_control.py` |
| `ui_read` | Read UI elements of frontmost app | `skills/ui_read.py` |
| `ui_click` | Click a button/element by name | `skills/ui_click.py` |
| `ui_type` | Type text or press key combos | `skills/ui_type.py` |
| `safari` | Search, read pages, fill forms, click links | `skills/safari.py` |
| `contacts` | Search contacts, call, FaceTime | `skills/contacts.py` |
| `system_settings` | Navigate to a Settings section | `skills/system_settings.py` |
| `app_store` | Search/install from App Store | `skills/app_store.py` |

### Creating a New Skill

Drop a single Python file in `skills/`. It gets auto-discovered on startup.

**Template:**

```python
"""skills/my_skill.py — Description of what this skill does."""

from skills.base import Skill


class MySkill(Skill):
    name = "my_skill"                          # unique name the LLM will call
    description = (                            # tells the LLM when to use this
        "One sentence explaining what this skill does "
        "and when the LLM should choose it."
    )
    parameters = {                             # JSON Schema for arguments
        "type": "object",
        "properties": {
            "thing": {
                "type": "string",
                "description": "What this argument is for.",
            },
        },
        "required": ["thing"],
    }

    def execute(self, thing: str) -> str:
        """Do the thing. Return a text result the LLM will narrate."""
        # ... your logic here ...
        return f"Done: {thing}"
```

**Rules:**
- Class must inherit from `Skill`
- Must set `name`, `description`, and `parameters`
- `execute()` receives kwargs matching the parameters schema
- `execute()` must return a string — this gets sent back to the LLM
- Keep descriptions clear — the 8b model relies on them to pick the right tool
- Use `subprocess.run(..., timeout=5)` for shell commands to avoid hangs
- File name doesn't matter (but keep it descriptive)
- Prefix helpers with `_` or put them in `applescript_helpers.py`

**Testing a skill manually:**

```python
from skills import execute_tool
print(execute_tool("my_skill", {"thing": "test"}))
```

### AppleScript Helpers

For UI automation skills, use the shared helpers in `skills/applescript_helpers.py`:

```python
from skills.applescript_helpers import (
    run_applescript,       # run raw AppleScript, return stdout
    get_frontmost_app,     # name of the active app
    get_ui_elements,       # accessibility tree as text (for ui_read)
    click_element_by_name, # click by element name + type
    type_text,             # keystroke via System Events
    press_key,             # key combo (e.g. Cmd+C)
)
```

### Multi-Step Tool Calling

The LLM can chain up to 5 tool calls per request. Example flow:
1. User: "Navigate to General in Settings"
2. LLM calls `system_settings(section="general")` → opens Settings > General
3. LLM calls `ui_read()` → sees available buttons
4. LLM calls `ui_click(element_name="About")` → clicks About
5. LLM narrates: "I've opened the About section in General settings."

### Disabling Skills

```python
# In config.py:
SKILLS_ENABLED = False   # disables all tool calling, LLM is chat-only
```

---

## User Profile (Coming Soon)

Store your personal info for auto-filling forms and applications.

**Location:** `~/.jarvis/user_profile.json`

**Structure:**
```json
{
    "name": "Derek Smith",
    "email": "derek@example.com",
    "phone": "+1-555-123-4567",
    "address": "123 Main St, City, State 12345",
    "work_history": [
        {
            "title": "Software Engineer",
            "company": "Acme Corp",
            "start": "2020",
            "end": "2023",
            "description": "Built things"
        }
    ],
    "education": [
        {
            "degree": "BS Computer Science",
            "school": "State University",
            "year": "2020"
        }
    ],
    "skills": ["Python", "JavaScript", "Machine Learning"]
}
```

**Voice commands (once implemented):**
- "Save my email as derek@example.com"
- "Add to my work history: Software Engineer at Google from 2020 to 2023"
- "Fill out this application" (auto-matches form fields on current Safari page)

---

## Project Structure

```
~/jarvis/
├── main.py              — FastAPI server (REST + WebSocket + voice loop + chat + settings)
├── voice.py             — voice loop: wake word → record → STT → LLM → TTS
├── llm.py               — LLM client with pluggable providers (streaming, tool calling)
├── settings.py          — Settings persistence (~/.jarvis/settings.json) + config hot-patching
├── stt.py               — speech-to-text (faster-whisper)
├── tts.py               — TTS dispatcher (lazy-loads backend on first use)
├── config.py            — all settings (models, audio, skills, prompts, API keys)
├── events.py            — thread-safe pub/sub for state → WebSocket
├── wake_word.py         — openwakeword "Hey Jarvis" detection
├── skills/              — tool calling skills (auto-discovered)
│   ├── base.py              — Skill base class
│   ├── __init__.py          — registry + auto-discovery
│   ├── applescript_helpers.py — shared AppleScript utilities
│   ├── open_app.py          — launch apps
│   ├── volume_control.py    — system volume
│   ├── system_info.py       — time, date, uptime
│   ├── clipboard.py         — pbcopy/pbpaste
│   ├── web_search.py        — Google search / open URLs
│   ├── music_control.py     — Apple Music control
│   ├── ui_read.py           — read accessibility tree
│   ├── ui_click.py          — click elements by name
│   ├── ui_type.py           — type text / key combos
│   ├── safari.py            — Safari control + JS injection
│   ├── contacts.py          — contact lookup + calling
│   ├── system_settings.py   — navigate System Settings
│   └── app_store.py         — App Store search + install
├── llm_providers/       — pluggable LLM backends
│   ├── ollama_provider.py   — Ollama (local, default)
│   ├── anthropic_provider.py — Anthropic Claude
│   ├── openai_provider.py   — OpenAI GPT
│   └── gemini_provider.py   — Google Gemini
├── tts_backends/        — pluggable TTS engines
│   ├── kokoro_backend.py    — Kokoro 82M (fast, default)
│   ├── chatterbox_backend.py — Chatterbox (high quality, slow)
│   └── macos_backend.py     — macOS `say` (instant, no deps)
├── frontend/            — React + Three.js orb UI
│   ├── src/                 — TypeScript source
│   └── dist/                — built static files (served by FastAPI)
├── docs/                — this documentation
└── venv/                — Python 3.11 virtual environment
```

---

## Config Knobs (`config.py`)

| Setting | Default | Notes |
|---------|---------|-------|
| `SYSTEM_PROMPT` | (see config.py) | Personality + tool usage guidance |
| `SKILLS_ENABLED` | `True` | Toggle all tool calling |
| `LLM_PROVIDER` | `"ollama"` | `"ollama"`, `"anthropic"`, `"openai"`, `"gemini"` |
| `STT_BACKEND` | `"local"` | Only `"local"` implemented |
| `WHISPER_MODEL` | `"base"` | Whisper model size |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API |
| `OLLAMA_MODEL` | `llama3.1:8b` | LLM model (when provider=ollama) |
| `ANTHROPIC_API_KEY` | env var | From `ANTHROPIC_API_KEY` env var |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude model |
| `OPENAI_API_KEY` | env var | From `OPENAI_API_KEY` env var |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| `GEMINI_API_KEY` | env var | From `GEMINI_API_KEY` env var |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model |
| `TTS_ENABLED` | `True` | `False` for text-only |
| `TTS_BACKEND` | `"kokoro"` | `"kokoro"`, `"chatterbox"`, `"macos"` |
| `TTS_VOICE` | `"af_heart"` | Kokoro voice name |
| `TTS_IDLE_TIMEOUT` | `300` | Seconds before unloading TTS model |
| `WAKE_WORD_ENABLED` | `True` | Wake word gate |
| `BARGE_IN_ENABLED` | `True` | Interrupt by speaking |
| `SILENCE_THRESHOLD` | `500` | RMS below this = silence |
| `SILENCE_DURATION` | `2.0` | Seconds of silence to stop recording |

Settings can also be changed at runtime via the **Settings Overlay** (Cmd+Comma or gear icon). Saved to `~/.jarvis/settings.json`.

---

## LLM Providers

Jarvis supports multiple LLM backends. Switch via settings overlay (Cmd+Comma) or config.

| Provider | Model | Local? | Tool Calling | Best for |
|----------|-------|--------|-------------|----------|
| `ollama` (default) | llama3.1:8b | Yes | Yes | Privacy, zero-cost, fast |
| `anthropic` | Claude Sonnet | No | Yes | Complex reasoning, long context |
| `openai` | GPT-4o | No | Yes | Broad knowledge, tool calling |
| `gemini` | Gemini 2.0 Flash | No | Yes | Speed, multimodal |

```bash
# Switch via environment variable
LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... python run.py

# Or set in ~/.jarvis/settings.json (persists across restarts)
# Or use the Settings overlay (Cmd+Comma) in the UI
```

All providers use the same internal message format (Ollama-style). Each provider translates on the fly. Tool calling works across all providers.

---

## TTS Backends

| Backend | Speed | Quality | Best for |
|---------|-------|---------|----------|
| `kokoro` (default) | ~50-200ms | Good | Daily use |
| `chatterbox` | ~2-5s | Highest | Demos, pre-recorded |
| `macos` | ~100ms | Decent | Zero-dep fallback |

```python
# Switch in config.py:
TTS_BACKEND = "kokoro"       # fast neural (default)
TTS_BACKEND = "chatterbox"   # highest quality
TTS_BACKEND = "macos"        # instant, no deps
```

---

## API Endpoints

| Endpoint | Method | What |
|----------|--------|------|
| `/` | GET | Frontend (orb UI) |
| `/api/status` | GET | Server status |
| `/api/chat` | POST | Text input (sends `{text}`, streams response via WebSocket) |
| `/api/settings` | GET | Current settings (API keys masked) |
| `/api/settings` | POST | Save settings + hot-patch config |
| `/api/llm/models` | GET | Available models for a provider (`?provider=ollama`) |
| `/api/voice/status` | GET | Voice pipeline config |
| `/api/tts/status` | GET | TTS model status |
| `/api/llm/status` | GET | Ollama connectivity |
| `/api/search` | GET | Hybrid file search (`?q=query&limit=10`) |
| `/ws` | WebSocket | Real-time state + RMS streaming |

```bash
# Quick health checks
curl http://localhost:8000/api/status
curl http://localhost:8000/api/voice/status
curl http://localhost:8000/api/llm/status

# Text chat (response streams via WebSocket)
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"text": "hello"}'
```

---

## Git

Remote: `https://github.com/ds301056/jarvis.git`

```bash
git status
git add <files>
git commit -m "message"
git push origin main
git log --oneline -10
```

---

## Permissions & Prerequisites

### Required
- **Python 3.11** — chatterbox-tts needs numpy<1.26
- **Ollama** — must be running before starting Jarvis
- **PortAudio** — `brew install portaudio` (for PyAudio)

### For UI Automation Skills
- **Accessibility permission** — System Settings > Privacy & Security > Accessibility. Grant access to Terminal (or whatever runs Jarvis). Required for `ui_read`, `ui_click`, `ui_type`.
- **Safari > Develop menu** — Enable "Allow JavaScript from Apple Events" in Safari's Develop menu (for `safari` skill's JS injection). Enable Develop menu in Safari Settings > Advanced.

### Optional
- **`mas` CLI** — `brew install mas` for App Store search/install from command line

---

## Gotchas

- **Python 3.11 required** — chatterbox needs numpy<1.26. The venv uses `brew install python@3.11`.
- **No requirements.txt** — deps installed directly in venv. Generate one with `pip freeze > requirements.txt`.
- **PyAudio needs PortAudio** — `brew install portaudio` before `pip install pyaudio`.
- **Ollama must be running** before starting Jarvis.
- **Silence threshold** — default 500 may need tuning for your mic. Adjust `SILENCE_THRESHOLD` in config.
- **Tool count limit** — llama3.1:8b works well with ~15 tools max. Quality degrades with more. Consolidate skills if adding many.
- **UI element reading can be slow** — complex apps may take 5-10s for `ui_read`. Depth is capped at 2 levels.
- **TTS model warm-up** — first synthesis may be slower while the model loads in background.
- **Temp audio files** — STT writes to `/tmp`. Check if disk fills up.
