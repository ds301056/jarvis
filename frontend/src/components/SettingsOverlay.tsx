import { useState, useEffect } from 'react'
import { Settings } from '../hooks/useSettings'

interface SettingsOverlayProps {
  open: boolean
  onClose: () => void
  settings: Settings
  onSettingsChange: (s: Settings) => void
  onSave: (s: Settings) => void
  loading: boolean
}

type Tab = 'llm' | 'voice' | 'about'

export default function SettingsOverlay({
  open, onClose, settings, onSettingsChange, onSave, loading,
}: SettingsOverlayProps) {
  const [tab, setTab] = useState<Tab>('llm')
  const [models, setModels] = useState<string[]>([])

  // Fetch models when provider changes
  useEffect(() => {
    if (!open) return
    fetch(`/api/llm/models?provider=${settings.llm_provider}`)
      .then(r => r.json())
      .then(data => setModels(data.models || []))
      .catch(() => setModels([]))
  }, [open, settings.llm_provider])

  if (!open) return null

  const update = (key: keyof Settings, value: string) => {
    onSettingsChange({ ...settings, [key]: value })
  }

  const modelKey = `${settings.llm_provider}_model` as keyof Settings
  const currentModel = settings.llm_provider === 'ollama'
    ? settings.ollama_model
    : settings[modelKey] || ''

  return (
    <div style={styles.backdrop} onClick={onClose}>
      <div style={styles.panel} onClick={e => e.stopPropagation()}>
        <div style={styles.header}>
          <h2 style={styles.title}>Settings</h2>
          <button onClick={onClose} style={styles.closeBtn}>&times;</button>
        </div>

        {/* Tabs */}
        <div style={styles.tabs}>
          {(['llm', 'voice', 'about'] as Tab[]).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                ...styles.tab,
                ...(tab === t ? styles.tabActive : {}),
              }}
            >
              {t === 'llm' ? 'LLM' : t === 'voice' ? 'Voice' : 'About'}
            </button>
          ))}
        </div>

        <div style={styles.body}>
          {tab === 'llm' && (
            <>
              <label style={styles.label}>Provider</label>
              <select
                value={settings.llm_provider}
                onChange={e => update('llm_provider', e.target.value)}
                style={styles.select}
              >
                <option value="ollama">Ollama (Local)</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="openai">OpenAI (GPT)</option>
                <option value="gemini">Google (Gemini)</option>
              </select>

              {settings.llm_provider !== 'ollama' && (
                <>
                  <label style={styles.label}>API Key</label>
                  <input
                    type="password"
                    value={settings[`${settings.llm_provider}_api_key` as keyof Settings] || ''}
                    onChange={e => update(`${settings.llm_provider}_api_key` as keyof Settings, e.target.value)}
                    placeholder="Enter API key..."
                    style={styles.input}
                  />
                </>
              )}

              <label style={styles.label}>Model</label>
              {models.length > 0 ? (
                <select
                  value={currentModel}
                  onChange={e => update(modelKey, e.target.value)}
                  style={styles.select}
                >
                  {models.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              ) : (
                <input
                  value={currentModel}
                  onChange={e => update(modelKey, e.target.value)}
                  placeholder="Model name..."
                  style={styles.input}
                />
              )}
            </>
          )}

          {tab === 'voice' && (
            <>
              <label style={styles.label}>TTS Backend</label>
              <select
                value={settings.tts_backend}
                onChange={e => update('tts_backend', e.target.value)}
                style={styles.select}
              >
                <option value="kokoro">Kokoro (Fast)</option>
                <option value="chatterbox">Chatterbox (Quality)</option>
                <option value="macos">macOS (System)</option>
              </select>

              <label style={styles.label}>STT Backend</label>
              <select
                value={settings.stt_backend}
                onChange={e => update('stt_backend', e.target.value)}
                style={styles.select}
              >
                <option value="local">Local Whisper</option>
              </select>
            </>
          )}

          {tab === 'about' && (
            <div style={{ color: '#aaa', lineHeight: 1.8 }}>
              <p><strong style={{ color: '#ddd' }}>Jarvis</strong> — Voice assistant for macOS</p>
              <p>Built with Ollama, FastAPI, React, and Three.js</p>
              <p style={{ marginTop: 16, fontSize: 12, opacity: 0.5 }}>
                Press <kbd style={styles.kbd}>Cmd+,</kbd> to toggle settings
              </p>
            </div>
          )}
        </div>

        <div style={styles.footer}>
          <button onClick={onClose} style={styles.cancelBtn}>Cancel</button>
          <button
            onClick={() => onSave(settings)}
            disabled={loading}
            style={styles.saveBtn}
          >
            {loading ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.7)',
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  panel: {
    width: '100%',
    maxWidth: 560,
    maxHeight: '80vh',
    background: 'rgba(22, 22, 38, 0.98)',
    borderRadius: 16,
    border: '1px solid rgba(255,255,255,0.1)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 24px 12px',
  },
  title: {
    margin: 0,
    fontSize: 18,
    fontWeight: 600,
    color: '#e0e0e0',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#888',
    fontSize: 24,
    cursor: 'pointer',
    padding: '0 4px',
    lineHeight: 1,
  },
  tabs: {
    display: 'flex',
    gap: 4,
    padding: '0 24px',
    borderBottom: '1px solid rgba(255,255,255,0.08)',
  },
  tab: {
    background: 'none',
    border: 'none',
    color: '#888',
    fontSize: 13,
    fontWeight: 500,
    padding: '10px 16px',
    cursor: 'pointer',
    borderBottom: '2px solid transparent',
    transition: 'color 0.2s, border-color 0.2s',
  },
  tabActive: {
    color: '#4488ff',
    borderBottomColor: '#4488ff',
  },
  body: {
    flex: 1,
    padding: '20px 24px',
    overflowY: 'auto' as const,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: '#999',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  select: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8,
    color: '#ddd',
    fontSize: 14,
    padding: '10px 12px',
    outline: 'none',
  },
  input: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8,
    color: '#ddd',
    fontSize: 14,
    padding: '10px 12px',
    outline: 'none',
  },
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
    padding: '16px 24px',
    borderTop: '1px solid rgba(255,255,255,0.08)',
  },
  cancelBtn: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8,
    color: '#aaa',
    fontSize: 13,
    padding: '8px 20px',
    cursor: 'pointer',
  },
  saveBtn: {
    background: 'rgba(68, 136, 255, 0.8)',
    border: 'none',
    borderRadius: 8,
    color: 'white',
    fontSize: 13,
    fontWeight: 600,
    padding: '8px 24px',
    cursor: 'pointer',
  },
  kbd: {
    background: 'rgba(255,255,255,0.1)',
    borderRadius: 4,
    padding: '2px 6px',
    fontSize: 11,
  },
}
