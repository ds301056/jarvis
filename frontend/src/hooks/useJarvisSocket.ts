import { useEffect, useReducer, useRef, useCallback } from 'react'
import { JarvisState, ChatMessage } from '../types'

interface JarvisStore {
  state: JarvisState
  rms: number
  rmsSource: 'mic' | 'tts'
  messages: ChatMessage[]
  currentTokens: string
  connected: boolean
}

type Action =
  | { type: 'state'; state: JarvisState }
  | { type: 'rms'; value: number; source: 'mic' | 'tts' }
  | { type: 'transcript'; role: 'user' | 'assistant'; text: string; final: boolean }
  | { type: 'token'; text: string }
  | { type: 'connected' }
  | { type: 'disconnected' }

function reducer(s: JarvisStore, a: Action): JarvisStore {
  switch (a.type) {
    case 'state':
      // When transitioning to speaking, clear accumulated tokens
      if (a.state === 'speaking' && s.state !== 'speaking') {
        return { ...s, state: a.state, currentTokens: '' }
      }
      return { ...s, state: a.state }
    case 'rms':
      return { ...s, rms: a.value, rmsSource: a.source }
    case 'transcript':
      if (a.final) {
        return {
          ...s,
          messages: [...s.messages, { role: a.role, text: a.text, final: true }],
          currentTokens: '',
        }
      }
      return s
    case 'token':
      return { ...s, currentTokens: s.currentTokens + a.text + ' ' }
    case 'connected':
      return { ...s, connected: true }
    case 'disconnected':
      return { ...s, connected: false, state: 'idle', rms: 0 }
    default:
      return s
  }
}

const INITIAL: JarvisStore = {
  state: 'idle',
  rms: 0,
  rmsSource: 'mic',
  messages: [],
  currentTokens: '',
  connected: false,
}

export function useJarvisSocket() {
  const [store, dispatch] = useReducer(reducer, INITIAL)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      dispatch({ type: 'connected' })
      retryRef.current = 0
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        dispatch(msg)
      } catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      dispatch({ type: 'disconnected' })
      // Reconnect with exponential backoff (max 5s)
      const delay = Math.min(1000 * Math.pow(1.5, retryRef.current), 5000)
      retryRef.current++
      setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return store
}
