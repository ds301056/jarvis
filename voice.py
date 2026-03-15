"""Main voice loop: speak → transcribe → LLM → TTS response."""

import math
import queue
import struct
import tempfile
import threading
import wave

import pyaudio

import config
import events
from stt import record_audio, transcribe
from llm import query, stream_sentences
from wake_word import wait_for_wake_word


def _is_dismiss(text: str) -> bool:
    """Check if user wants to dismiss Jarvis and return to wake word."""
    lower = text.lower().strip()
    return any(phrase in lower for phrase in config.DISMISS_PHRASES)


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
                events.publish({"type": "state", "state": "listening"})
                break
        else:
            # stop_event was set without barge-in — normal exit
            return
    except OSError:
        return

    # --- Phase 2: record the user's utterance until silence ---
    max_silent_chunks = int(config.BARGE_IN_SILENCE_DURATION * config.SAMPLE_RATE / CHUNK)
    print(f"[recording barge-in utterance... threshold={phase2_threshold}, "
          f"silence_duration={config.BARGE_IN_SILENCE_DURATION}s, "
          f"max_silent_chunks={max_silent_chunks}]", flush=True)
    frames = [data]  # include the chunk that triggered barge-in
    silent_chunks = 0
    _p2_chunk_count = 0

    try:
        while not stop_event.is_set():
            data = mic_stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            samples = struct.unpack(f"<{CHUNK}h", data)
            rms = math.sqrt(sum(s * s for s in samples) / CHUNK)

            _p2_chunk_count += 1
            if rms > phase2_threshold:
                if silent_chunks > 0 and _p2_chunk_count % 4 == 0:
                    print(f"  [phase2] speech resumed (rms={rms:.0f}), reset silence from {silent_chunks}", flush=True)
                silent_chunks = 0
            else:
                silent_chunks += 1

            if _p2_chunk_count % 8 == 0:  # every ~0.5s
                print(f"  [phase2] rms={rms:.0f} silent={silent_chunks}/{max_silent_chunks}", flush=True)

            if silent_chunks >= max_silent_chunks:
                print(f"  [phase2] silence detected ({config.BARGE_IN_SILENCE_DURATION}s), ending capture", flush=True)
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
            _slice_count = 0
            while offset < len(pcm):
                if interrupt_event.is_set():
                    return
                end = min(offset + _PLAYBACK_SLICE, len(pcm))
                chunk = pcm[offset:end]
                stream.write(chunk)
                # Emit TTS RMS every 4th slice (~200ms)
                _slice_count += 1
                if _slice_count % 4 == 0 and events.has_subscribers():
                    samples = struct.unpack(f"<{len(chunk)//2}h", chunk)
                    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
                    events.publish({"type": "rms", "value": min(rms / 8000, 1.0), "source": "tts"})
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
    events.publish({"type": "state", "state": "speaking"})
    interrupted = False
    full_response = []
    try:
        for sentence in stream_sentences(text):
            full_response.append(sentence)
            if events.has_subscribers():
                events.publish({"type": "token", "text": sentence})
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

        # Wait for monitor to finish Phase 2 capture (silence detection).
        # Do NOT set stop_monitor here — let Phase 2 run until it detects
        # silence, otherwise it captures only 2-3 chunks of garbage.
        if monitor_thread is not None:
            monitor_thread.join(timeout=10.0)

        # Give tts/playback a moment to clean up, but don't block long
        tts_thread.join(timeout=0.5)
        playback_thread.join(timeout=0.5)

        if full_response:
            events.publish({"type": "transcript", "role": "assistant", "text": " ".join(full_response), "final": True})
        if captured_audio_path:
            print("[interrupted — processing barge-in audio...]")
            return captured_audio_path[0]
        print("[interrupted — no audio captured, listening for command...]")
        return ""

    # Normal (non-interrupted) path: wait for pipeline to finish,
    # but check for late barge-in so we don't block on a long synthesize().
    while tts_thread.is_alive():
        tts_thread.join(timeout=0.2)
        if interrupt_event.is_set():
            break
    while playback_thread.is_alive():
        playback_thread.join(timeout=0.2)
        if interrupt_event.is_set():
            break
    stop_monitor.set()
    if monitor_thread is not None:
        monitor_thread.join(timeout=2.0)

    if full_response:
        events.publish({"type": "transcript", "role": "assistant", "text": " ".join(full_response), "final": True})

    # Barge-in may have occurred after the LLM stream finished but while
    # TTS/playback were still running.  The producer loop never saw the
    # interrupt so `interrupted` stayed False, but the monitor may have
    # captured audio.  Handle it here instead of silently dropping it.
    if interrupt_event.is_set() and captured_audio_path:
        print("[interrupted (late) — processing barge-in audio...]")
        return captured_audio_path[0]
    if interrupt_event.is_set():
        print("[interrupted (late) — no audio captured, listening again...]")
        return ""

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
    if config.WAKE_WORD_ENABLED:
        print("Wake word enabled — say 'Hey Jarvis' to activate")
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
    events.publish({"type": "state", "state": "idle"})

    try:
        while True:
            try:
                if config.WAKE_WORD_ENABLED:
                    wait_for_wake_word(mic_stream)
                events.publish({"type": "state", "state": "listening"})
                text = transcribe(record_audio(mic_stream=mic_stream, pa_instance=pa))
                if not text:
                    print("(no speech detected, try again)")
                    events.publish({"type": "state", "state": "idle"})
                    continue

                print(f"\nYou: {text}")
                events.publish({"type": "transcript", "role": "user", "text": text, "final": True})

                if _is_dismiss(text):
                    print("[dismissed — returning to wake word]")
                    events.publish({"type": "state", "state": "idle"})
                    continue

                events.publish({"type": "state", "state": "thinking"})
                print("Jarvis: ", end="", flush=True)

                if config.TTS_ENABLED:
                    captured_path = _respond_with_tts(text, mic_stream)
                    # Handle barge-in: let user finish their full thought
                    # before responding (stay in "listening" state)
                    while captured_path is not None:
                        if not captured_path:
                            # Interrupted but no audio captured — go back to listening
                            break
                        print(f"[barge-in captured: {captured_path}]")

                        # Stay in "listening" — let user finish speaking
                        print("[barge-in: continuing to listen for full utterance...]")
                        continuation_path = record_audio(mic_stream=mic_stream, pa_instance=pa, initial_speech=True)

                        # Transcribe both parts and combine
                        barge_text = transcribe(captured_path)
                        continuation_text = transcribe(continuation_path)
                        print(f"[barge-in transcription: '{barge_text}' + continuation: '{continuation_text}']")
                        full_text = f"{barge_text} {continuation_text}".strip() if continuation_text else (barge_text or "")

                        if not full_text:
                            print("(barge-in audio empty, listening again)")
                            break

                        if _is_dismiss(full_text):
                            print("[dismissed via barge-in — returning to wake word]")
                            events.publish({"type": "state", "state": "idle"})
                            break

                        print(f"\nYou: {full_text}")
                        events.publish({"type": "transcript", "role": "user", "text": full_text, "final": True})
                        events.publish({"type": "state", "state": "thinking"})
                        print("Jarvis: ", end="", flush=True)
                        captured_path = _respond_with_tts(full_text, mic_stream)
                    continue
                else:
                    query(text, stream=True)

                events.publish({"type": "state", "state": "idle"})
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
