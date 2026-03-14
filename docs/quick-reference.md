# Jarvis Quick Reference

> Concise cheat sheet for building Jarvis. Updated as the project evolves.

---

## Daily Workflow

```bash
# 1. Activate the virtual environment
source ~/jarvis/venv/bin/activate

# 2. Start Ollama (if not already running)
ollama serve            # runs in background; or use the macOS app

# 3. Pull / verify the model
ollama list             # should show llama3.1:8b
ollama pull llama3.1:8b # if missing

# 4. Start the FastAPI server
cd ~/jarvis
uvicorn main:app --reload

# 5. Run voice mode (separate terminal, venv activated)
python -c "from voice import voice_loop; voice_loop()"
```

---

## Git Commands

Remote: `https://github.com/ds301056/jarvis.git` (HTTPS, gh already authed)

```bash
git status
git add <files>
git commit -m "message"
git push origin main
git log --oneline -10
```

---

## Project Structure

```
~/jarvis/
├── config.py            — central settings (backends, models, audio params)
├── main.py              — FastAPI server with status endpoints
├── llm.py               — Ollama query client (streaming + sentence splitting)
├── stt.py               — speech-to-text (record + transcribe via faster-whisper)
├── tts.py               — TTS dispatcher (lazy-loads backend, synthesize/play API)
├── voice.py             — voice loop: record → transcribe → LLM → TTS → play
├── tts_backends/        — pluggable TTS engine modules
│   ├── kokoro_backend.py    — Kokoro 82M (fast, neural, default)
│   ├── chatterbox_backend.py — Chatterbox (high quality, slow)
│   └── macos_backend.py     — macOS `say` (zero deps, instant)
├── docs/                — documentation
└── venv/                — Python 3.11 virtual environment
```

No `requirements.txt` or `pyproject.toml` yet — deps installed directly in venv.

---

## Config Knobs (`config.py`)

| Setting | Default | Notes |
|---------|---------|-------|
| `STT_BACKEND` | `"local"` | `"local"`, `"api"`, `"apple"` (only local implemented) |
| `WHISPER_MODEL` | `"base"` | Whisper model size for faster-whisper |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model name to query |
| `TTS_ENABLED` | `True` | Set `False` for text-only mode |
| `TTS_BACKEND` | `"kokoro"` | `"kokoro"`, `"chatterbox"`, `"macos"` (see TTS section below) |
| `TTS_VOICE` | `"af_heart"` | Kokoro voice name (ignored by other backends) |
| `TTS_IDLE_TIMEOUT` | `300` | Seconds before unloading TTS model from memory |
| `TTS_SAMPLE_RATE` | `24000` | All backends output at this rate |
| `SAMPLE_RATE` | `16000` | Audio input sample rate (Hz) |
| `CHANNELS` | `1` | Mono audio |
| `CHUNK_SIZE` | `1024` | PyAudio buffer size |
| `SILENCE_THRESHOLD` | `500` | RMS amplitude below which = silence |
| `SILENCE_DURATION` | `2.0` | Seconds of silence before stop recording |

---

## TTS Backends

Change the backend by editing `TTS_BACKEND` in `config.py`. No restart needed between voice loop runs.

### Kokoro (default) — `TTS_BACKEND = "kokoro"`

- **Speed**: ~50-200ms per clause on MPS. Fastest neural option.
- **Quality**: Good. Natural-sounding, 82M parameter model.
- **Best for**: Daily use. Low-latency conversational responses.
- **Voices**: Set `TTS_VOICE` in config. Options include `af_heart`, `af_bella`, `af_sarah`, `am_adam`, `am_michael`, `bf_emma`, `bm_george`, etc. Full list: https://huggingface.co/hexgrad/Kokoro-82M
- **Install**: `pip install kokoro` (already installed)
- **Notes**: Model downloads ~350MB on first use. Uses MPS on Apple Silicon.

### Chatterbox — `TTS_BACKEND = "chatterbox"`

- **Speed**: ~2-5s per sentence on MPS. Slow but expressive.
- **Quality**: Highest. Diffusion-based, very natural prosody and emotion.
- **Best for**: Pre-recorded content, demos, or when quality matters more than speed.
- **Install**: `pip install chatterbox-tts` (already installed)
- **Notes**: Requires Python 3.11 (numpy<1.26 constraint). Large model (~3GB on disk). `perth` watermarker patched automatically.

### macOS `say` — `TTS_BACKEND = "macos"`

- **Speed**: ~100-300ms. Nearly instant.
- **Quality**: Decent. System TTS voices (Siri-like). Least natural of the three.
- **Best for**: Zero-dependency fallback, testing, or when you don't want GPU usage.
- **Voices**: Controlled by system settings (System Preferences → Accessibility → Spoken Content). Run `say -v ?` to list all available voices.
- **Install**: None — built into macOS.
- **Notes**: Shells out to `say` command. No GPU needed.

### Switching backends

```python
# In config.py — just change this line:
TTS_BACKEND = "kokoro"       # fast neural (default)
TTS_BACKEND = "chatterbox"   # highest quality
TTS_BACKEND = "macos"        # instant, no deps
```

### Disabling TTS entirely

```python
# In config.py:
TTS_ENABLED = False   # text-only mode, no audio output
```

---

## Useful Checks

```bash
# Verify FastAPI is up
curl http://localhost:8000/

# Check full voice pipeline config
curl http://localhost:8000/voice/status

# Check TTS backend status (model loaded, device, etc.)
curl http://localhost:8000/tts/status

# Check Ollama connectivity + available models
curl http://localhost:8000/llm/status

# Test Ollama directly
curl http://localhost:11434/api/tags

# Verify key imports work
python -c "import faster_whisper, pyaudio, fastapi, requests; print('all good')"

# Test TTS directly (no voice loop)
python -c "from tts import speak; speak('Hello, I am Jarvis.')"
```

---

## Gotchas

- **Python 3.11 required** — chatterbox-tts needs numpy<1.26 which doesn't have Python 3.13/3.14 wheels. The venv uses Python 3.11 via `brew install python@3.11`.
- **No requirements.txt** — if you recreate the venv you'll need to reinstall everything manually. Consider generating one with `pip freeze > requirements.txt`.
- **PyAudio needs PortAudio** — install via `brew install portaudio` before `pip install pyaudio`.
- **Ollama must be running** before starting the server or voice loop, otherwise `/llm/status` returns `"unreachable"`.
- **Silence detection** — the default threshold (500) may need tuning for your mic/environment. If it keeps recording forever or cuts off too early, adjust `SILENCE_THRESHOLD` in `config.py`.
- **STT backends** — only `"local"` (faster-whisper) is implemented. Setting `STT_BACKEND` to `"api"` or `"apple"` raises `NotImplementedError`.
- **Streaming output** — `llm.query()` prints tokens to stdout in real-time by default. Pass `stream=False` for a single returned string.
- **Temp audio files** — `stt.py` writes to temp wav files during transcription; they should be cleaned up automatically but check `/tmp` if disk fills up.
- **TTS model warm-up** — the voice loop pre-loads the TTS model in background while waiting for your first utterance. First synthesis may still be slightly slower if the model hasn't finished loading.
- **Clause splitting** — LLM responses are split on commas/semicolons/colons (when >30 chars) and sentence boundaries for faster TTS chunks. This is tuned for low-latency; adjust `_MIN_CLAUSE_LEN` in `llm.py` if chunks feel too short or too long.
