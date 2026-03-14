"""Central configuration for Jarvis."""

# STT settings
STT_BACKEND = "local"  # "local" | "api" | "apple"
WHISPER_MODEL = "base"

# LLM settings
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 2.0  # seconds of silence before stopping recording
