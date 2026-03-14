"""Main voice loop: speak → transcribe → LLM → TTS response."""

import math
import queue
import struct
import tempfile
import threading
import wave

import pyaudio

import config
from stt import record_audio, transcribe
from llm import query, stream_sentences


def _mic_monitor(mic_stream, interrupt_event: threading.Event,
                 stop_event: threading.Event, captured_audio_path: list):
    """Monitor mic during TTS playback; set interrupt_event if user speaks loudly.

    Phase 1: detect barge-in (loud speech above BARGE_IN_THRESHOLD).
    Phase 2: after barge-in, keep recording on the SAME stream until silence,
             save to wav, and store path in captured_audio_path.

    Does NOT close mic_stream (caller owns it).
    """
    CHUNK = config.CHUNK_SIZE
    phase2_threshold = config.BARGE_IN_THRESHOLD // 2  # 750

    # --- Phase 1: detect barge-in ---
    try:
        while not stop_event.is_set():
            data = mic_stream.read(CHUNK, exception_on_overflow=False)
            samples = struct.unpack(f"<{CHUNK}h", data)
            rms = math.sqrt(sum(s * s for s in samples) / CHUNK)
            if rms > config.BARGE_IN_THRESHOLD:
                print(f"\n[barge-in detected, rms={rms:.0f}]", flush=True)
                interrupt_event.set()
                break
        else:
            # stop_event was set without barge-in — normal exit
            return
    except OSError:
        return

    # --- Phase 2: record the user's utterance until silence ---
    print("[recording barge-in utterance...]", flush=True)
    frames = [data]  # include the chunk that triggered barge-in
    silent_chunks = 0
    max_silent_chunks = int(1.0 * config.SAMPLE_RATE / CHUNK)  # 1s silence
    has_speech = True  # we already have speech from the trigger chunk

    try:
        while not stop_event.is_set():
            data = mic_stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            samples = struct.unpack(f"<{CHUNK}h", data)
            rms = math.sqrt(sum(s * s for s in samples) / CHUNK)

            if rms > phase2_threshold:
                silent_chunks = 0
            else:
                silent_chunks += 1

            if silent_chunks >= max_silent_chunks:
                break
    except OSError:
        pass

    # Save captured audio to wav
    if frames:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(config.CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(config.SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        captured_audio_path.append(tmp.name)
        print(f"[captured {len(frames)} chunks of barge-in audio]", flush=True)


# 50ms of audio at 24kHz int16 mono = 2400 bytes
_PLAYBACK_SLICE = int(config.TTS_SAMPLE_RATE * 0.05) * 2


def _playback_worker(audio_q: queue.Queue, interrupt_event: threading.Event):
    """Pull PCM data from queue, play in small slices checking for interrupt."""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=config.TTS_SAMPLE_RATE,
        output=True,
    )
    try:
        while True:
            try:
                pcm = audio_q.get(timeout=0.1)
            except queue.Empty:
                if interrupt_event.is_set():
                    return
                continue
            if pcm is None:
                break
            offset = 0
            while offset < len(pcm):
                if interrupt_event.is_set():
                    return
                end = min(offset + _PLAYBACK_SLICE, len(pcm))
                stream.write(pcm[offset:end])
                offset = end
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def _tts_worker(sentence_q: queue.Queue, audio_q: queue.Queue,
                interrupt_event: threading.Event):
    """Pull sentences from queue, synthesize to PCM, push to audio queue."""
    from tts import synthesize

    while True:
        if interrupt_event.is_set():
            audio_q.put(None)
            break
        try:
            sentence = sentence_q.get(timeout=0.1)
        except queue.Empty:
            continue
        if sentence is None:
            audio_q.put(None)
            break
        if interrupt_event.is_set():
            audio_q.put(None)
            break
        try:
            pcm = synthesize(sentence)
            while not interrupt_event.is_set():
                try:
                    audio_q.put(pcm, timeout=0.1)
                    break
                except queue.Full:
                    continue
            else:
                audio_q.put(None)
                break
        except Exception as e:
            print(f"\n[TTS synth error] {e}")


def _drain_queue(q: queue.Queue):
    while True:
        try:
            q.get_nowait()
        except queue.Empty:
            break


def _respond_with_tts(text: str, mic_stream) -> str | None:
    """Stream LLM response with sentence-level TTS pipeline.

    Returns path to captured barge-in audio if interrupted, None otherwise.
    """
    sentence_q = queue.Queue(maxsize=4)
    audio_q = queue.Queue(maxsize=2)
    interrupt_event = threading.Event()
    stop_monitor = threading.Event()
    captured_audio_path = []  # mutable container for monitor thread to fill

    tts_thread = threading.Thread(
        target=_tts_worker, args=(sentence_q, audio_q, interrupt_event), daemon=True)
    playback_thread = threading.Thread(
        target=_playback_worker, args=(audio_q, interrupt_event), daemon=True)
    tts_thread.start()
    playback_thread.start()

    # Start mic monitor — uses the persistent mic stream (no new PyAudio needed)
    monitor_thread = None
    if config.BARGE_IN_ENABLED:
        monitor_thread = threading.Thread(
            target=_mic_monitor,
            args=(mic_stream, interrupt_event, stop_monitor, captured_audio_path),
            daemon=True)
        monitor_thread.start()

    # Producer: stream sentences from LLM into the pipeline
    interrupted = False
    try:
        for sentence in stream_sentences(text):
            if interrupt_event.is_set():
                interrupted = True
                break
            while not interrupt_event.is_set():
                try:
                    sentence_q.put(sentence, timeout=0.1)
                    break
                except queue.Full:
                    continue
            if interrupt_event.is_set():
                interrupted = True
                break
    finally:
        # Use put_nowait — if queue is full (tts stuck in synthesize), drain first
        _drain_queue(sentence_q)
        sentence_q.put(None)

    if interrupted:
        # Fast path: don't wait for tts/playback (they're daemon threads and will
        # finish or die on their own). Go straight to getting captured audio.
        _drain_queue(sentence_q)
        _drain_queue(audio_q)

        # Wait for monitor to finish Phase 2 capture (needs the mic stream,
        # so we MUST wait before returning to avoid concurrent mic reads)
        stop_monitor.set()
        if monitor_thread is not None:
            monitor_thread.join(timeout=5.0)

        # Give tts/playback a moment to clean up, but don't block long
        tts_thread.join(timeout=0.5)
        playback_thread.join(timeout=0.5)

        if captured_audio_path:
            print("[interrupted — processing barge-in audio...]")
            return captured_audio_path[0]
        print("[interrupted — no audio captured, listening for command...]")
        return ""

    # Normal (non-interrupted) path: wait for pipeline to finish
    tts_thread.join()
    playback_thread.join()
    stop_monitor.set()
    if monitor_thread is not None:
        monitor_thread.join(timeout=2.0)

    return None


def voice_loop():
    """Run the continuous voice interaction loop."""
    print("Jarvis Voice Mode — say something (Ctrl+C to quit)")
    if config.TTS_ENABLED:
        print("TTS enabled — responses will be spoken aloud")
        if config.BARGE_IN_ENABLED:
            print("Barge-in enabled — speak to interrupt Jarvis")
        print("Loading TTS model in background...")
        from tts import warm_up
        warm_up()
    print("-" * 50)

    # Create persistent mic stream (one-time HFP switch for AirPods)
    pa = pyaudio.PyAudio()
    mic_stream = pa.open(
        format=pyaudio.paInt16,
        channels=config.CHANNELS,
        rate=config.SAMPLE_RATE,
        input=True,
        frames_per_buffer=config.CHUNK_SIZE,
    )

    # One-time mic warm-up
    print("🎤 Waiting for mic...", end="", flush=True)
    while True:
        data = mic_stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
        samples = struct.unpack(f"<{len(data)//2}h", data)
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        if rms > 1:
            break
    print("\r🎤 Mic active — ready!                ")

    try:
        while True:
            try:
                text = transcribe(record_audio(mic_stream=mic_stream, pa_instance=pa))
                if not text:
                    print("(no speech detected, try again)")
                    continue

                print(f"\nYou: {text}")
                print("Jarvis: ", end="", flush=True)

                if config.TTS_ENABLED:
                    captured_path = _respond_with_tts(text, mic_stream)
                    if captured_path is not None:
                        if captured_path:
                            # Barge-in with captured audio — transcribe directly
                            barge_text = transcribe(captured_path)
                            if barge_text:
                                print(f"\nYou: {barge_text}")
                                print("Jarvis: ", end="", flush=True)
                                captured_path = _respond_with_tts(barge_text, mic_stream)
                                # If interrupted again during barge-in response,
                                # loop will handle it on next iteration
                                if captured_path is not None and captured_path:
                                    # Chain: re-enter loop with this new capture
                                    # For simplicity, just continue to next iteration
                                    pass
                            else:
                                print("(barge-in audio empty, listening again)")
                        # Empty string = interrupted but no capture, just re-listen
                        continue
                else:
                    query(text, stream=True)

                print()

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"\n[error] {e}")
                continue
    except KeyboardInterrupt:
        print("\nExiting voice mode.")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        pa.terminate()


if __name__ == "__main__":
    voice_loop()
