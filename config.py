"""Central configuration for Jarvis."""

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
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"

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
