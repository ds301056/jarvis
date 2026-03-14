"""Text-to-speech with pluggable backends and lazy-loaded singleton."""

import threading
import time

import numpy as np
import pyaudio

import config

_model = None
_backend = None
_model_lock = threading.Lock()
_last_used = 0.0
_idle_timer = None


def _get_backend():
    """Return the backend module based on config."""
    if config.TTS_BACKEND == "kokoro":
        from tts_backends import kokoro_backend as backend
    elif config.TTS_BACKEND == "chatterbox":
        from tts_backends import chatterbox_backend as backend
    elif config.TTS_BACKEND == "macos":
        from tts_backends import macos_backend as backend
    else:
        raise ValueError(f"Unknown TTS backend: {config.TTS_BACKEND}")
    return backend


def _schedule_idle_unload():
    """Reset the idle timer that unloads the model after TTS_IDLE_TIMEOUT."""
    global _idle_timer
    if _idle_timer is not None:
        _idle_timer.cancel()
    _idle_timer = threading.Timer(config.TTS_IDLE_TIMEOUT, _unload_model)
    _idle_timer.daemon = True
    _idle_timer.start()


def _unload_model():
    """Unload the TTS model to free memory."""
    global _model, _backend, _idle_timer
    with _model_lock:
        if _model is not None:
            print(f"[TTS] Unloading {config.TTS_BACKEND} model (idle timeout)")
            _model = None
            _backend = None
            _idle_timer = None


def _ensure_model():
    """Load the TTS model if not already loaded."""
    global _model, _backend, _last_used
    with _model_lock:
        if _model is None:
            print(f"[TTS] Loading {config.TTS_BACKEND} backend...")
            _backend = _get_backend()
            _model = _backend.load()
            print(f"[TTS] {config.TTS_BACKEND} ready")
        _last_used = time.time()
        _schedule_idle_unload()
        return _model, _backend


def warm_up():
    """Pre-load the TTS model in background so it's ready for first request."""
    threading.Thread(target=_ensure_model, daemon=True).start()


def synthesize(text: str) -> bytes:
    """Synthesize text to int16 PCM bytes using the configured backend."""
    model, backend = _ensure_model()
    audio = backend.generate(model, text)

    # Normalize to int16 PCM
    if not isinstance(audio, np.ndarray):
        audio = np.array(audio, dtype=np.float32)
    if audio.dtype in (np.float32, np.float64):
        audio = np.clip(audio, -1.0, 1.0)
        audio = (audio * 32767).astype(np.int16)

    return audio.tobytes()


def play_audio(pcm_data: bytes):
    """Play int16 PCM data through PyAudio."""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=config.TTS_SAMPLE_RATE,
        output=True,
    )
    try:
        stream.write(pcm_data)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def speak(text: str):
    """Convenience wrapper: synthesize and play."""
    pcm = synthesize(text)
    play_audio(pcm)


def model_status() -> dict:
    """Return current TTS model status."""
    return {
        "tts_enabled": config.TTS_ENABLED,
        "tts_backend": config.TTS_BACKEND,
        "model_loaded": _model is not None,
        "last_used": _last_used if _last_used > 0 else None,
        "idle_timeout": config.TTS_IDLE_TIMEOUT,
    }
