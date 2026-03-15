import { useState, useEffect } from 'react'
import { JarvisState } from '../types'

interface DebugOverlayProps {
  state: JarvisState
  rms: number
  rmsSource: 'mic' | 'tts'
  connected: boolean
  messageCount: number
}

export default function DebugOverlay({ state, rms, rmsSource, connected, messageCount }: DebugOverlayProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '`') setVisible(v => !v)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  if (!visible) return null

  const stateColors: Record<JarvisState, string> = {
    idle: '#666',
    listening: '#44ffaa',
    thinking: '#aa66ff',
    speaking: '#4488ff',
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.title}>DEBUG <span style={{ opacity: 0.4, fontSize: '10px' }}>(` to toggle)</span></div>

      <div style={styles.row}>
        <span style={styles.label}>WebSocket</span>
        <span style={{ color: connected ? '#44ff88' : '#ff4444' }}>
          {connected ? 'connected' : 'disconnected'}
        </span>
      </div>

      <div style={styles.row}>
        <span style={styles.label}>State</span>
        <span style={{
          color: stateColors[state],
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '1px',
        }}>
          {state}
        </span>
      </div>

      <div style={styles.row}>
        <span style={styles.label}>RMS ({rmsSource})</span>
        <div style={styles.barContainer}>
          <div style={{
            ...styles.bar,
            width: `${rms * 100}%`,
            background: rmsSource === 'mic' ? '#44ffaa' : '#4488ff',
          }} />
        </div>
        <span style={styles.value}>{rms.toFixed(3)}</span>
      </div>

      <div style={styles.row}>
        <span style={styles.label}>Messages</span>
        <span style={styles.value}>{messageCount}</span>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 16,
    right: 16,
    background: 'rgba(0, 0, 0, 0.85)',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '10px',
    padding: '14px 18px',
    fontFamily: 'SF Mono, Monaco, Consolas, monospace',
    fontSize: '12px',
    color: '#aaa',
    zIndex: 1000,
    minWidth: '240px',
  },
  title: {
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '2px',
    marginBottom: '10px',
    color: '#666',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  label: {
    width: '80px',
    flexShrink: 0,
    color: '#666',
  },
  value: {
    color: '#999',
    minWidth: '40px',
    textAlign: 'right' as const,
  },
  barContainer: {
    flex: 1,
    height: '6px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  bar: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.08s ease-out',
  },
}
