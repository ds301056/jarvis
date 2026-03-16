import { useState } from 'react'
import * as THREE from 'three'
import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import Orb from './components/Orb'
import Particles from './components/Particles'
import ChatPanel from './components/ChatPanel'
import ChatInput from './components/ChatInput'
import SearchBar from './components/SearchBar'
import SearchResults from './components/SearchResults'
import DebugOverlay from './components/DebugOverlay'
import SettingsOverlay from './components/SettingsOverlay'
import Layout from './components/Layout'
import { useJarvisSocket } from './hooks/useJarvisSocket'
import { useVoiceClient } from './hooks/useVoiceClient'
import { useSearch } from './hooks/useSearch'
import { useChatInput } from './hooks/useChatInput'
import { useSettings } from './hooks/useSettings'

export default function App() {
  const { state: localState, messages: localMessages, currentTokens: localTokens, connected, rmsRef } = useJarvisSocket()
  const voice = useVoiceClient()
  const [audioSpikes, setAudioSpikes] = useState(true)
  const { query, results, loading, active, handleQuery, clearSearch, openFile } = useSearch()
  const chatInput = useChatInput()
  const settingsHook = useSettings()

  // Merge: prefer phone voice state when it's active, otherwise use local pipeline
  const isPhoneActive = voice.state !== 'idle' || voice.isRecording
  const state = isPhoneActive ? voice.state : localState
  const messages = isPhoneActive ? voice.messages : localMessages
  const currentTokens = isPhoneActive ? voice.currentTokens : localTokens

  const orbView = (
    <>
      <Canvas
        camera={{ position: [0, 0, 3], fov: 45 }}
        gl={{ antialias: true, alpha: false }}
        scene={{ background: new THREE.Color('#0a0a15') }}
        style={{ width: '100%', height: '100%' }}
      >
        <ambientLight intensity={0.1} />
        <Orb state={state} rmsRef={rmsRef} audioSpikes={audioSpikes} />
        <Particles />
        <EffectComposer multisampling={0}>
          <Bloom
            intensity={0.5}
            luminanceThreshold={0.4}
            luminanceSmoothing={0.9}
            mipmapBlur
          />
        </EffectComposer>
      </Canvas>

      {/* Connection indicator */}
      {!connected && (
        <div className="connecting-overlay">
          <div className="connecting-dot" />
          <span>Connecting...</span>
        </div>
      )}

      <div className="state-label">{state}</div>

      <button
        onClick={() => setAudioSpikes(v => !v)}
        className="spike-toggle"
        data-active={audioSpikes}
      >
        {audioSpikes ? '◆ Spikes ON' : '◇ Spikes OFF'}
      </button>
    </>
  )

  const chatView = <ChatPanel messages={messages} currentTokens={currentTokens} />

  const searchBarView = (
    <SearchBar
      query={query}
      onQueryChange={handleQuery}
      onClear={clearSearch}
      loading={loading}
    />
  )

  const searchResultsView = (
    <SearchResults
      results={results}
      loading={loading}
      query={query}
      onOpenFile={openFile}
    />
  )

  const chatInputView = (
    <ChatInput
      input={chatInput.input}
      onInputChange={chatInput.setInput}
      onSend={chatInput.send}
      sending={chatInput.sending}
      isRecording={voice.isRecording}
      voiceState={voice.state}
      onMicToggle={voice.toggleRecording}
    />
  )

  return (
    <>
      <Layout
        orb={orbView}
        chat={chatView}
        chatInput={chatInputView}
        searchBar={searchBarView}
        searchResults={searchResultsView}
        searchActive={active}
      />
      <DebugOverlay
        state={state}
        rmsRef={rmsRef}
        connected={connected}
        messageCount={messages.length}
      />
      <SettingsOverlay
        open={settingsHook.open}
        onClose={settingsHook.toggle}
        settings={settingsHook.settings}
        onSettingsChange={settingsHook.setSettings}
        onSave={settingsHook.save}
        loading={settingsHook.loading}
      />
      {/* Gear icon to open settings */}
      <button onClick={settingsHook.toggle} style={gearStyle} title="Settings (Cmd+,)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="rgba(255,255,255,0.4)">
          <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.48.48 0 0 0-.48-.41h-3.84a.48.48 0 0 0-.48.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 0 0-.59.22L2.74 8.87a.48.48 0 0 0 .12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.48-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z" />
        </svg>
      </button>
    </>
  )
}

const gearStyle: React.CSSProperties = {
  position: 'fixed',
  top: 16,
  right: 16,
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
  width: 36,
  height: 36,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  zIndex: 50,
  transition: 'background 0.2s',
}
