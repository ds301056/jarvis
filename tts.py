"""Text-to-speech module using Chatterbox TTS with lazy-loaded singleton."""

import logging
import os
import threading
import time
import warnings

import numpy as np
import pyaudio
import torch

import config

# Suppress noisy warnings from transformers/diffusers/torch
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("diffusers").setLevel(logging.ERROR)

_model = None
_model_lock = threading.Lock()
_last_used = 0.0
_idle_timer = None


def _get_device() -> str:
    """Return best available torch device."""
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


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
    global _model, _idle_timer
    with _model_lock:
        if _model is not None:
            print("[TTS] Unloading model (idle timeout)")
            _model = None
            _idle_timer = None


def _ensure_model():
    """Load the TTS model if not already loaded."""
    global _model, _last_used
    with _model_lock:
        if _model is None:
            print("[TTS] Loading model...")
            # Patch perth watermarker stub (public release has None placeholder)
            import perth
            if perth.PerthImplicitWatermarker is None:
                perth.PerthImplicitWatermarker = perth.DummyWatermarker
            from chatterbox.tts import ChatterboxTTS
            device = _get_device()
            _model = ChatterboxTTS.from_pretrained(device=device)
            _suppress_tqdm()
            print(f"[TTS] Model loaded on {device}")
        _last_used = time.time()
        _schedule_idle_unload()
        return _model


def warm_up():
    """Pre-load the TTS model in background so it's ready for first request."""
    threading.Thread(target=_ensure_model, daemon=True).start()


def _suppress_tqdm():
    """Patch tqdm in chatterbox modules to be silent."""
    from functools import partial
    from tqdm import tqdm
    silent_tqdm = partial(tqdm, disable=True)
    import chatterbox.models.t3.t3 as t3_mod
    import chatterbox.models.s3gen.flow_matching as fm_mod
    t3_mod.tqdm = silent_tqdm
    fm_mod.tqdm = silent_tqdm


def synthesize(text: str) -> bytes:
    """Synthesize text to int16 PCM bytes."""
    model = _ensure_model()
    wav_tensor = model.generate(text, exaggeration=0.3)

    # Convert to int16 PCM
    if isinstance(wav_tensor, torch.Tensor):
        audio = wav_tensor.squeeze().cpu().numpy()
    else:
        audio = np.array(wav_tensor).squeeze()

    # Normalize to int16 range
    if audio.dtype == np.float32 or audio.dtype == np.float64:
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
        "tts_model": config.TTS_MODEL,
        "model_loaded": _model is not None,
        "device": _get_device(),
        "last_used": _last_used if _last_used > 0 else None,
        "idle_timeout": config.TTS_IDLE_TIMEOUT,
    }
