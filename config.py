"""Central configuration for Jarvis."""

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
