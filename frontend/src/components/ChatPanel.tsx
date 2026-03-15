import { useEffect, useRef } from 'react'
import { ChatMessage } from '../types'

interface ChatPanelProps {
  messages: ChatMessage[]
  currentTokens: string
}

export default function ChatPanel({ messages, currentTokens }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentTokens])

  return (
    <div style={styles.container}>
      <div style={styles.scrollArea}>
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              ...styles.bubble,
              ...(msg.role === 'user' ? styles.userBubble : styles.assistantBubble),
            }}
          >
            <div style={styles.role}>{msg.role === 'user' ? 'You' : 'Jarvis'}</div>
            <div>{msg.text}</div>
          </div>
        ))}
        {currentTokens && (
          <div style={{ ...styles.bubble, ...styles.assistantBubble }}>
            <div style={styles.role}>Jarvis</div>
            <div>{currentTokens}<span style={styles.cursor}>|</span></div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    borderTop: '1px solid rgba(255,255,255,0.06)',
  },
  scrollArea: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  bubble: {
    maxWidth: '80%',
    padding: '10px 14px',
    borderRadius: '12px',
    fontSize: '14px',
    lineHeight: '1.5',
    wordWrap: 'break-word' as const,
  },
  userBubble: {
    alignSelf: 'flex-end',
    background: 'rgba(68, 136, 255, 0.15)',
    color: '#c8d8ff',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    background: 'rgba(255, 255, 255, 0.06)',
    color: '#d0d0d0',
  },
  role: {
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '1px',
    marginBottom: '4px',
    opacity: 0.5,
  },
  cursor: {
    opacity: 0.5,
    animation: 'blink 1s step-end infinite',
  },
}
