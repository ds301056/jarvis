import { useRef, KeyboardEvent } from 'react'
import { JarvisState } from '../types'

interface ChatInputProps {
  input: string
  onInputChange: (value: string) => void
  onSend: (text: string) => void
  sending: boolean
  // Inline mic button
  isRecording: boolean
  voiceState: JarvisState
  onMicToggle: () => void
}

export default function ChatInput({
  input, onInputChange, onSend, sending,
  isRecording, voiceState, onMicToggle,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend(input)
    }
  }

  const isProcessing = !isRecording && (voiceState === 'thinking' || voiceState === 'speaking')

  return (
    <div style={styles.wrapper}>
      <div style={styles.container}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => {
            onInputChange(e.target.value)
            // Auto-resize
            const el = e.target
            el.style.height = 'auto'
            el.style.height = Math.min(el.scrollHeight, 120) + 'px'
          }}
          onKeyDown={handleKeyDown}
          placeholder="Message Jarvis..."
          rows={1}
          style={styles.textarea}
        />
        <div style={styles.buttons}>
          {/* Mic button */}
          <button
            onClick={onMicToggle}
            disabled={isProcessing}
            style={{
              ...styles.iconBtn,
              background: isRecording
                ? 'rgba(255, 60, 60, 0.85)'
                : 'transparent',
              animation: isRecording ? 'mic-pulse 1.5s ease-in-out infinite' : 'none',
            }}
            title={isRecording ? 'Stop recording' : 'Start recording'}
          >
            {isProcessing ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ animation: 'spin 1s linear infinite' }}>
                <circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.4)" strokeWidth="2" fill="none" />
                <path d="M12 2a10 10 0 0 1 10 10" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="rgba(255,255,255,0.6)">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
            )}
          </button>
          {/* Send button */}
          <button
            onClick={() => onSend(input)}
            disabled={!input.trim() || sending}
            style={{
              ...styles.iconBtn,
              opacity: input.trim() && !sending ? 1 : 0.3,
            }}
            title="Send message"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="rgba(255,255,255,0.8)">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    display: 'flex',
    justifyContent: 'center',
    padding: '12px 16px 24px',
    zIndex: 100,
    pointerEvents: 'none',
  },
  container: {
    width: '100%',
    maxWidth: 680,
    display: 'flex',
    alignItems: 'flex-end',
    gap: 8,
    background: 'rgba(20, 20, 35, 0.85)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 24,
    padding: '8px 8px 8px 16px',
    pointerEvents: 'auto',
  },
  textarea: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#e0e0e0',
    fontSize: 14,
    lineHeight: '1.5',
    resize: 'none' as const,
    maxHeight: 120,
    fontFamily: 'inherit',
    padding: '4px 0',
  },
  buttons: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    flexShrink: 0,
  },
  iconBtn: {
    width: 32,
    height: 32,
    borderRadius: '50%',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s',
  },
}
