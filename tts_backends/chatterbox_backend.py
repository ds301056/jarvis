"""Chatterbox TTS backend — high-quality diffusion-based TTS (slower)."""

import logging
import os
import warnings

import numpy as np
import torch

# Suppress noisy warnings from transformers/diffusers
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("diffusers").setLevel(logging.ERROR)


def _get_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load():
    """Load Chatterbox model with perth watermarker patch."""
    import perth
    if perth.PerthImplicitWatermarker is None:
        perth.PerthImplicitWatermarker = perth.DummyWatermarker

    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device=_get_device())

    # Suppress tqdm progress bars in chatterbox internals
    from functools import partial
    from tqdm import tqdm
    silent_tqdm = partial(tqdm, disable=True)
    import chatterbox.models.t3.t3 as t3_mod
    import chatterbox.models.s3gen.flow_matching as fm_mod
    t3_mod.tqdm = silent_tqdm
    fm_mod.tqdm = silent_tqdm

    return model


def generate(model, text: str) -> np.ndarray:
    """Synthesize text, return float32 numpy array."""
    wav_tensor = model.generate(text, exaggeration=0.3)

    if isinstance(wav_tensor, torch.Tensor):
        audio = wav_tensor.squeeze().cpu().numpy()
    else:
        audio = np.array(wav_tensor).squeeze()

    return audio.astype(np.float32)


def sample_rate() -> int:
    return 24000
