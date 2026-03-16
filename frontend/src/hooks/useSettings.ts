import { useState, useEffect, useCallback } from 'react'

export interface Settings {
  llm_provider: string
  ollama_model: string
  anthropic_api_key: string
  anthropic_model: string
  openai_api_key: string
  openai_model: string
  gemini_api_key: string
  gemini_model: string
  tts_backend: string
  stt_backend: string
}

const EMPTY: Settings = {
  llm_provider: 'ollama',
  ollama_model: '',
  anthropic_api_key: '',
  anthropic_model: '',
  openai_api_key: '',
  openai_model: '',
  gemini_api_key: '',
  gemini_model: '',
  tts_backend: 'kokoro',
  stt_backend: 'local',
}

export function useSettings() {
  const [open, setOpen] = useState(false)
  const [settings, setSettings] = useState<Settings>(EMPTY)
  const [loading, setLoading] = useState(false)

  const toggle = useCallback(() => setOpen(v => !v), [])

  // Hotkey: Cmd+Comma
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === ',') {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggle])

  // Fetch settings when opened
  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => setSettings({ ...EMPTY, ...data }))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [open])

  const save = useCallback(async (updated: Settings) => {
    setLoading(true)
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      })
      setSettings(updated)
    } catch (e) {
      console.error('Settings save failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  return { open, toggle, settings, setSettings, save, loading }
}
