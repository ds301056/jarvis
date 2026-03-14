"""Main voice loop: speak → transcribe → LLM → TTS response."""

import queue
import threading

import config
from stt import transcribe
from llm import query, stream_sentences


def _tts_worker(sentence_q: queue.Queue, audio_q: queue.Queue):
    """Pull sentences from queue, synthesize to PCM, push to audio queue."""
    from tts import synthesize

    while True:
        sentence = sentence_q.get()
        if sentence is None:  # poison pill
            audio_q.put(None)
            break
        try:
            pcm = synthesize(sentence)
            audio_q.put(pcm)
        except Exception as e:
            print(f"\n[TTS synth error] {e}")


def _playback_worker(audio_q: queue.Queue):
    """Pull PCM data from queue, play through a single PyAudio stream."""
    import pyaudio

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=config.TTS_SAMPLE_RATE,
        output=True,
    )
    try:
        while True:
            pcm = audio_q.get()
            if pcm is None:  # poison pill
                break
            stream.write(pcm)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def _respond_with_tts(text: str):
    """Stream LLM response with sentence-level TTS pipeline."""
    sentence_q = queue.Queue(maxsize=4)
    audio_q = queue.Queue(maxsize=2)

    tts_thread = threading.Thread(target=_tts_worker, args=(sentence_q, audio_q), daemon=True)
    playback_thread = threading.Thread(target=_playback_worker, args=(audio_q,), daemon=True)
    tts_thread.start()
    playback_thread.start()

    # Producer: stream sentences from LLM into the pipeline
    try:
        for sentence in stream_sentences(text):
            sentence_q.put(sentence)
    finally:
        sentence_q.put(None)  # signal end to TTS worker

    # Wait for pipeline to drain
    tts_thread.join()
    playback_thread.join()


def voice_loop():
    """Run the continuous voice interaction loop."""
    print("Jarvis Voice Mode — say something (Ctrl+C to quit)")
    if config.TTS_ENABLED:
        print("TTS enabled — responses will be spoken aloud")
        print("Loading TTS model in background...")
        from tts import warm_up
        warm_up()
    print("-" * 50)

    while True:
        try:
            text = transcribe()
            if not text:
                print("(no speech detected, try again)")
                continue

            print(f"\nYou: {text}")
            print("Jarvis: ", end="", flush=True)

            if config.TTS_ENABLED:
                _respond_with_tts(text)
            else:
                query(text, stream=True)

            print()

        except KeyboardInterrupt:
            print("\nExiting voice mode.")
            break


if __name__ == "__main__":
    voice_loop()
