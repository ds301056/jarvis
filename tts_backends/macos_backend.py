"""macOS `say` TTS backend — zero dependencies, built-in system voices."""

import subprocess
import tempfile
import wave

import numpy as np


def load():
    """No model to load for macOS say."""
    return None


def generate(_model, text: str) -> np.ndarray:
    """Synthesize text using macOS say command, return float32 numpy array."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    subprocess.run(
        ["say", "-o", tmp_path, "--data-format", "LEI16@24000", text],
        check=True,
        capture_output=True,
    )

    with wave.open(tmp_path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())

    import os
    os.unlink(tmp_path)

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    return audio


def sample_rate() -> int:
    return 24000
