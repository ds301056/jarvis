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
├── config.py   — central settings (backends, models, audio params)
├── main.py     — FastAPI server with status endpoints
├── llm.py      — Ollama query client (streaming support)
├── stt.py      — speech-to-text (record + transcribe via faster-whisper)
├── voice.py    — voice loop: record → transcribe → LLM → print
└── venv/       — Python 3.14 virtual environment (45 packages)
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
| `SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `CHANNELS` | `1` | Mono audio |
| `CHUNK` | `1024` | PyAudio buffer size |
| `SILENCE_THRESHOLD` | `500` | RMS amplitude below which = silence |
| `SILENCE_DURATION` | `2.0` | Seconds of silence before stop recording |

---

## Useful Checks

```bash
# Verify FastAPI is up
curl http://localhost:8000/

# Check voice config
curl http://localhost:8000/voice/status

# Check Ollama connectivity + available models
curl http://localhost:8000/llm/status

# Test Ollama directly
curl http://localhost:11434/api/tags

# Verify key imports work
python -c "import faster_whisper, pyaudio, fastapi, requests; print('all good')"
```

---

## Gotchas

- **No requirements.txt** — if you recreate the venv you'll need to reinstall everything manually. Consider generating one with `pip freeze > requirements.txt`.
- **PyAudio needs PortAudio** — install via `brew install portaudio` before `pip install pyaudio`.
- **Ollama must be running** before starting the server or voice loop, otherwise `/llm/status` returns `"unreachable"`.
- **Silence detection** — the default threshold (500) may need tuning for your mic/environment. If it keeps recording forever or cuts off too early, adjust `SILENCE_THRESHOLD` in `config.py`.
- **STT backends** — only `"local"` (faster-whisper) is implemented. Setting `STT_BACKEND` to `"api"` or `"apple"` raises `NotImplementedError`.
- **Streaming output** — `llm.query()` prints tokens to stdout in real-time by default. Pass `stream=False` for a single returned string.
- **Temp audio files** — `stt.py` writes to temp wav files during transcription; they should be cleaned up automatically but check `/tmp` if disk fills up.
