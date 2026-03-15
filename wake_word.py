"""Wake word detection using openwakeword — 'Hey Jarvis' trigger."""

import numpy as np

import config
import events

_model = None


def _get_model():
    global _model
    if _model is None:
        from openwakeword.model import Model
        _model = Model(wakeword_models=[config.WAKE_WORD_MODEL], inference_framework="onnx")
        print(f"[wake word] loaded model: {config.WAKE_WORD_MODEL}")
    return _model


def wait_for_wake_word(mic_stream) -> bool:
    """Block reading from mic_stream until 'Hey Jarvis' is detected.

    Returns True when the wake word is detected.
    """
    model = _get_model()
    model.reset()
    events.publish({"type": "state", "state": "idle"})
    print("\n[wake word] listening for 'Hey Jarvis'...", flush=True)

    while True:
        data = mic_stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
        audio = np.frombuffer(data, dtype=np.int16)
        prediction = model.predict(audio)

        score = prediction.get(config.WAKE_WORD_MODEL, 0)
        if score > config.WAKE_WORD_THRESHOLD:
            print(f"[wake word] detected! (score={score:.3f})", flush=True)
            model.reset()
            return True
