"""Central configuration for Jarvis."""

import os

# System prompt for LLM chat
SYSTEM_PROMPT = """You are Jarvis, a helpful voice assistant running on a Mac Mini.
Keep responses concise and conversational — they will be spoken aloud.
Use tools when the user asks you to do something actionable.
For simple questions, just answer directly.
When asked to interact with an app's UI, first use ui_read to see what elements are available, then use ui_click or ui_type to interact with them. Always read before clicking.
For Safari tasks, prefer the safari tool over generic UI tools.
For System Settings, use system_settings to jump to the right section, then ui_read/ui_click to navigate within it."""

# Skills settings
SKILLS_ENABLED = True

# STT settings
STT_BACKEND = "local"  # "local" | "api" | "apple"
WHISPER_MODEL = "base"

# LLM settings
LLM_PROVIDER = "ollama"  # "ollama" | "anthropic" | "openai" | "gemini"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# TTS settings
TTS_ENABLED = True
TTS_BACKEND = "kokoro"         # "kokoro" | "chatterbox" | "macos"
TTS_VOICE = "af_heart"         # Kokoro voice (ignored by other backends)
TTS_IDLE_TIMEOUT = 300         # 5 min before unloading model
TTS_SAMPLE_RATE = 24000        # All backends output at this rate

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 2.0  # seconds of silence before stopping recording

# Barge-in settings (interrupt Jarvis by speaking)
BARGE_IN_ENABLED = True
BARGE_IN_THRESHOLD = 1500     # Higher than SILENCE_THRESHOLD to ignore speaker bleed
BARGE_IN_SILENCE_DURATION = 2.0  # seconds of silence before ending barge-in capture (match SILENCE_DURATION)

# Wake word settings
WAKE_WORD_ENABLED = True
WAKE_WORD_MODEL = "hey_jarvis"
WAKE_WORD_THRESHOLD = 0.5

# Conversation mode — stay in dialog after wake word until dismissed or timeout
CONVERSATION_TIMEOUT = 30.0  # seconds of no speech before returning to wake word

# Dismiss phrases (user wants Jarvis to stop and go back to sleep)
DISMISS_PHRASES = [
    "that's enough",
    "nevermind",
    "never mind",
    "go back to sleep",
    "go to sleep",
    "goodbye",
    "good bye",
    "stop",
    "shut up",
    "dismiss",
    "cancel",
]

# ── File Search / Indexer settings ───────────────────────────────────
SEARCH_ENABLED = True
SEARCH_DIRS = ["~/Documents", "~/Desktop", "~/Downloads"]
SEARCH_EXCLUDE_DIRS = [
    ".git", "node_modules", "__pycache__", "venv", ".venv",
    "Library", ".Trash", "dist", "build",
]
SEARCH_EXCLUDE_EXTENSIONS = [
    ".DS_Store", ".app", ".dmg", ".pkg", ".zip", ".tar", ".gz",
    ".mp4", ".mov", ".mp3", ".wav", ".jpg", ".png", ".gif",
    ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot",
]
SEARCH_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SEARCH_EMBEDDING_MODEL = "nomic-embed-text"
SEARCH_EMBEDDING_DIM = 768
SEARCH_CHUNK_SIZE = 2000
SEARCH_CHUNK_OVERLAP = 200
SEARCH_RESCAN_INTERVAL = 300  # 5 minutes
SEARCH_DB_PATH = "~/.jarvis/index.db"
SEARCH_BATCH_SIZE = 32

# ── Web Voice / SSL settings ─────────────────────────────────────────
WEB_VOICE_ENABLED = True
SSL_ENABLED = True
SSL_CERTFILE = "certs/cert.pem"
SSL_KEYFILE = "certs/key.pem"
