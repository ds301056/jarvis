import { useState, useEffect, useRef } from 'react'
import { JarvisState } from '../types'

const STATE_SEQUENCE: JarvisState[] = ['idle', 'listening', 'thinking', 'speaking']
const DURATIONS: Record<JarvisState, number> = {
  idle: 3000,
  listening: 2500,
  thinking: 2000,
  speaking: 4000,
}

export function useMockState() {
  const [state, setState] = useState<JarvisState>('idle')
  const [rms, setRms] = useState(0)
  const indexRef = useRef(0)

  // Cycle through states
  useEffect(() => {
    const advance = () => {
      indexRef.current = (indexRef.current + 1) % STATE_SEQUENCE.length
      const next = STATE_SEQUENCE[indexRef.current]
      setState(next)
    }

    const id = setInterval(() => {
      advance()
    }, DURATIONS[state])

    return () => clearInterval(id)
  }, [state])

  // Simulate RMS during speaking/listening
  useEffect(() => {
    if (state !== 'speaking' && state !== 'listening') {
      setRms(0)
      return
    }

    const id = setInterval(() => {
      // Simulate natural speech amplitude with some randomness
      const base = state === 'speaking' ? 0.4 : 0.3
      const variation = Math.random() * 0.4
      setRms(base + variation)
    }, 60)

    return () => clearInterval(id)
  }, [state])

  return { state, rms }
}
