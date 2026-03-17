import { useState, useRef, useCallback, useEffect } from 'react'
import { JarvisState, ChatMessage } from '../types'

export interface VoiceClientState {
  isRecording: boolean
  state: JarvisState
  transcript: string
  messages: ChatMessage[]
  currentTokens: string
  startRecording: () => void
  stopRecording: () => void
  toggleRecording: () => void
  connected: boolean
}

export function useVoiceClient(): VoiceClientState {
  const [isRecording, setIsRecording] = useState(false)
  const [state, setState] = useState<JarvisState>('idle')
  const [transcript, setTranscript] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentTokens, setCurrentTokens] = useState('')
  const [connected, setConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const nextPlayTimeRef = useRef(0)
  const retryRef = useRef(0)

  const SAMPLE_RATE = 24000

  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new AudioContext({ sampleRate: SAMPLE_RATE })
    }
    // iOS Safari requires resume from user gesture
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    return audioCtxRef.current
  }, [])

  const playPcmChunk = useCallback((pcmBytes: ArrayBuffer) => {
    const ctx = getAudioContext()
    const int16 = new Int16Array(pcmBytes)
    const float32 = new Float32Array(int16.length)
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768
    }

    const buffer = ctx.createBuffer(1, float32.length, SAMPLE_RATE)
    buffer.getChannelData(0).set(float32)

    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)

    const now = ctx.currentTime
    const startTime = Math.max(now, nextPlayTimeRef.current)
    source.start(startTime)
    nextPlayTimeRef.current = startTime + buffer.duration
  }, [getAudioContext])

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/voice`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      retryRef.current = 0
    }

    ws.onmessage = (e) => {
      if (e.data instanceof Blob) {
        // Binary PCM audio from TTS
        e.data.arrayBuffer().then(playPcmChunk)
        return
      }
      try {
        const msg = JSON.parse(e.data)
        switch (msg.type) {
          case 'state':
            setState(msg.state)
            if (msg.state === 'speaking') {
              setCurrentTokens('')
            }
            if (msg.state === 'idle') {
              nextPlayTimeRef.current = 0
            }
            break
          case 'transcript':
            if (msg.final) {
              setMessages(prev => [...prev, { role: msg.role, text: msg.text, final: true }])
              setCurrentTokens('')
              if (msg.role === 'user') {
                setTranscript(msg.text)
              }
            }
            break
          case 'token':
            setCurrentTokens(prev => prev + msg.text + ' ')
            break
          case 'audio_done':
            break
        }
      } catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      setConnected(false)
      const delay = Math.min(1000 * Math.pow(1.5, retryRef.current), 5000)
      retryRef.current++
      setTimeout(connect, delay)
    }

    ws.onerror = () => ws.close()
  }, [playPcmChunk])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
      audioCtxRef.current?.close()
    }
  }, [connect])

  const startRecording = useCallback(async () => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    // Resume AudioContext from user gesture (iOS requirement)
    getAudioContext()

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Pick MIME type: prefer webm/opus, fallback to mp4 (Safari)
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/mp4')
          ? 'audio/mp4'
          : ''

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      recorderRef.current = recorder

      ws.send(JSON.stringify({ type: 'start_recording' }))

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          e.data.arrayBuffer().then(buf => ws.send(buf))
        }
      }

      recorder.start(250) // Send chunks every 250ms
      setIsRecording(true)
    } catch (err) {
      console.error('Failed to start recording:', err)
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError') {
          alert('Microphone access was denied. Please allow microphone permissions in your browser settings.')
        } else if (err.name === 'NotFoundError') {
          alert('No microphone found. Please connect a microphone and try again.')
        } else if (err.name === 'NotSupportedError' || err.name === 'SecurityError') {
          alert('Microphone access requires HTTPS. Please access Jarvis via https://.')
        } else {
          alert(`Microphone error: ${err.message}`)
        }
      }
    }
  }, [getAudioContext])

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
    recorderRef.current = null

    // Stop mic tracks
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null

    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'stop_recording' }))
    }
    setIsRecording(false)
  }, [])

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }, [isRecording, startRecording, stopRecording])

  return {
    isRecording,
    state,
    transcript,
    messages,
    currentTokens,
    startRecording,
    stopRecording,
    toggleRecording,
    connected,
  }
}
