import { useEffect, useReducer, useRef, useCallback } from 'react'
import React from 'react'
import { JarvisState, ChatMessage } from '../types'

interface JarvisStore {
  state: JarvisState
  messages: ChatMessage[]
  currentTokens: string
  connected: boolean
}

type Action =
  | { type: 'state'; state: JarvisState }
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
      return { ...s, connected: false, state: 'idle' }
    default:
      return s
  }
}

const INITIAL: JarvisStore = {
  state: 'idle',
  messages: [],
  currentTokens: '',
  connected: false,
}

export interface RmsRef {
  value: number
  source: 'mic' | 'tts'
}

export function useJarvisSocket() {
  const [store, dispatch] = useReducer(reducer, INITIAL)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const rmsRef = useRef<RmsRef>({ value: 0, source: 'mic' })

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
        // RMS updates go straight to ref — no React re-render
        if (msg.type === 'rms') {
          rmsRef.current = { value: msg.value, source: msg.source }
          return
        }
        dispatch(msg)
      } catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      dispatch({ type: 'disconnected' })
      rmsRef.current = { value: 0, source: 'mic' }
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

  return { ...store, rmsRef }
}
