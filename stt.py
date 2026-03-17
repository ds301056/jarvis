"""Speech-to-text module with pluggable backends."""

import wave
import tempfile
import struct

import pyaudio

import config
import events


def record_audio(mic_stream=None, pa_instance=None, initial_speech=False,
                 max_wait: float | None = None) -> str | None:
    """Record audio from the microphone until silence is detected. Returns path to temp wav file.

    If mic_stream and pa_instance are provided, uses the existing stream
    (caller owns it — we won't close it). Otherwise creates a new one.

    If initial_speech is True, the silence timer starts immediately (user was
    already speaking, e.g. after barge-in).

    If max_wait is set, returns None if no speech is detected within that many seconds.
    """
    owns_stream = mic_stream is None
    if owns_stream:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=config.CHANNELS,
            rate=config.SAMPLE_RATE,
            input=True,
            frames_per_buffer=config.CHUNK_SIZE,
        )
        # Wait for mic to become active (AirPods Bluetooth profile switch)
        print("🎤 Waiting for mic...", end="", flush=True)
        while True:
            data = stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
            samples = struct.unpack(f"<{len(data)//2}h", data)
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
            if rms > 1:
                break
    else:
        stream = mic_stream

    print("\r🎤 Listening... (speak now, silence to stop)")

    frames = []
    silent_chunks = 0
    max_silent_chunks = int(config.SILENCE_DURATION * config.SAMPLE_RATE / config.CHUNK_SIZE)
    has_speech = initial_speech
    _chunk_count = 0

    try:
        while True:
            data = stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)

            # Calculate RMS amplitude
            samples = struct.unpack(f"<{len(data)//2}h", data)
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5

            # Show RMS every ~0.25s (every 4 chunks at 1024/16000)
            _chunk_count += 1
            if _chunk_count % 4 == 0:
                label = "SPEECH" if rms > config.SILENCE_THRESHOLD else "silent"
                bar = "#" * min(int(rms / 50), 40)
                print(f"\r  RMS: {rms:6.0f} [{label}] {bar:<40s}", end="", flush=True)
                if events.has_subscribers():
                    events.publish({"type": "rms", "value": min(rms / 8000, 1.0), "source": "mic"})

            # Conversation timeout: no speech started within max_wait
            if not has_speech and max_wait is not None:
                wait_elapsed = _chunk_count * config.CHUNK_SIZE / config.SAMPLE_RATE
                if wait_elapsed >= max_wait:
                    print("\n[no speech — conversation timeout]")
                    return None

            if rms > config.SILENCE_THRESHOLD:
                silent_chunks = 0
                has_speech = True
            else:
                silent_chunks += 1

            if has_speech and silent_chunks >= max_silent_chunks:
                print()  # newline after RMS display
                break
    finally:
        if owns_stream:
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
