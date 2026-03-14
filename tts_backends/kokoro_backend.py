"""Kokoro TTS backend — fast, lightweight neural TTS (82M params)."""

import warnings

import numpy as np

import config

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def load():
    """Load the Kokoro pipeline."""
    from kokoro import KPipeline
    return KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")


def generate(model, text: str) -> np.ndarray:
    """Synthesize text, return float32 numpy array."""
    audio_arrays = []
    for _gs, _ps, audio in model(text, voice=config.TTS_VOICE, speed=1.0):
        audio_arrays.append(audio)

    if not audio_arrays:
        return np.zeros(1, dtype=np.float32)

    return np.concatenate(audio_arrays).astype(np.float32)


def sample_rate() -> int:
    return 24000
