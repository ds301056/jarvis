"""WebSocket voice handler for phone-based voice testing.

Phone mic -> WebSocket -> STT -> LLM -> TTS -> WebSocket -> phone speaker.
"""

import asyncio
import json
import os
import subprocess
import tempfile

from fastapi import WebSocket, WebSocketDisconnect

import config


class WebVoiceHandler:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.audio_buffer = bytearray()

    async def run(self):
        try:
            while True:
                msg = await self.ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if "text" in msg:
                    data = json.loads(msg["text"])
                    await self._handle_text(data)
                elif "bytes" in msg:
                    self.audio_buffer.extend(msg["bytes"])
        except WebSocketDisconnect:
            pass

    async def _handle_text(self, data: dict):
        msg_type = data.get("type")
        if msg_type == "start_recording":
            self.audio_buffer = bytearray()
            await self._send_state("listening")
        elif msg_type == "stop_recording":
            await self._process_audio()

    async def _send_state(self, state: str):
        await self.ws.send_text(json.dumps({"type": "state", "state": state}))

    async def _send_json(self, data: dict):
        await self.ws.send_text(json.dumps(data))

    async def _process_audio(self):
        if not self.audio_buffer:
            await self._send_state("idle")
            return

        # Save WebM to temp file
        webm_tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
        webm_tmp.write(bytes(self.audio_buffer))
        webm_tmp.close()
        self.audio_buffer = bytearray()

        wav_path = webm_tmp.name.replace(".webm", ".wav")

        try:
            # Convert WebM -> WAV via ffmpeg
            result = await asyncio.to_thread(
                subprocess.run,
                ["ffmpeg", "-y", "-i", webm_tmp.name, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
                capture_output=True,
            )
            if result.returncode != 0:
                print(f"[WebVoice] ffmpeg error: {result.stderr.decode()}")
                await self._send_state("idle")
                return

            # STT
            await self._send_state("thinking")
            from stt import transcribe
            text = await asyncio.to_thread(transcribe, wav_path)
            text = text.strip()

            if not text:
                await self._send_state("idle")
                return

            await self._send_json({"type": "transcript", "role": "user", "text": text, "final": True})

            # LLM -> TTS streaming
            from llm import stream_sentences
            from tts import synthesize

            # Bridge sync generator to async via queue
            q: asyncio.Queue = asyncio.Queue()

            def _stream_worker():
                try:
                    for sentence in stream_sentences(text):
                        q.put_nowait(sentence)
                finally:
                    q.put_nowait(None)  # sentinel

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, _stream_worker)

            full_response = []
            await self._send_state("speaking")

            while True:
                sentence = await q.get()
                if sentence is None:
                    break
                full_response.append(sentence)
                await self._send_json({"type": "token", "text": sentence})

                # Synthesize TTS and send PCM binary
                pcm = await asyncio.to_thread(synthesize, sentence)
                await self.ws.send_bytes(pcm)

            await self._send_json({"type": "transcript", "role": "assistant", "text": " ".join(full_response), "final": True})
            await self._send_json({"type": "audio_done"})
            await self._send_state("idle")

        finally:
            # Cleanup temp files
            for f in (webm_tmp.name, wav_path):
                try:
                    os.unlink(f)
                except OSError:
                    pass
