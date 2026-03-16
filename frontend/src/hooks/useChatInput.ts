import { useState, useCallback } from 'react'

export function useChatInput() {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    setSending(true)
    setInput('')
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed }),
      })
    } catch (e) {
      console.error('Chat send failed:', e)
    } finally {
      setSending(false)
    }
  }, [sending])

  return { input, setInput, send, sending }
}
