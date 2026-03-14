"""Speech-to-text module with pluggable backends."""

import wave
import tempfile
import struct

import pyaudio

import config


def record_audio() -> str:
    """Record audio from the microphone until silence is detected. Returns path to temp wav file."""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=config.CHANNELS,
        rate=config.SAMPLE_RATE,
        input=True,
        frames_per_buffer=config.CHUNK_SIZE,
    )

    print("🎤 Listening... (speak now, silence to stop)")
    frames = []
    silent_chunks = 0
    max_silent_chunks = int(config.SILENCE_DURATION * config.SAMPLE_RATE / config.CHUNK_SIZE)
    has_speech = False

    try:
        while True:
            data = stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)

            # Calculate RMS amplitude
            samples = struct.unpack(f"<{len(data)//2}h", data)
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5

            if rms > config.SILENCE_THRESHOLD:
                silent_chunks = 0
                has_speech = True
            else:
                silent_chunks += 1

            if has_speech and silent_chunks >= max_silent_chunks:
                break
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    # Write to temp wav file
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(config.CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    return tmp.name


def transcribe_local(audio_path: str) -> str:
    """Transcribe using local faster-whisper model."""
    from faster_whisper import WhisperModel

    model = WhisperModel(config.WHISPER_MODEL, compute_type="int8")
    segments, _ = model.transcribe(audio_path)
    return " ".join(seg.text for seg in segments).strip()


def transcribe(audio_path: str | None = None) -> str:
    """Record (if no path given) and transcribe audio using the configured backend."""
    if audio_path is None:
        audio_path = record_audio()

    if config.STT_BACKEND == "local":
        return transcribe_local(audio_path)
    elif config.STT_BACKEND == "api":
        raise NotImplementedError("API backend not yet implemented")
    elif config.STT_BACKEND == "apple":
        raise NotImplementedError("Apple backend not yet implemented")
    else:
        raise ValueError(f"Unknown STT backend: {config.STT_BACKEND}")
