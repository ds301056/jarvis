import { useState } from 'react'
import * as THREE from 'three'
import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import Orb from './components/Orb'
import Particles from './components/Particles'
import ChatPanel from './components/ChatPanel'
import SearchBar from './components/SearchBar'
import SearchResults from './components/SearchResults'
import DebugOverlay from './components/DebugOverlay'
import Layout from './components/Layout'
import { useJarvisSocket } from './hooks/useJarvisSocket'
import { useVoiceClient } from './hooks/useVoiceClient'
import { useSearch } from './hooks/useSearch'
import MicButton from './components/MicButton'

export default function App() {
  const { state: localState, messages: localMessages, currentTokens: localTokens, connected, rmsRef } = useJarvisSocket()
  const voice = useVoiceClient()
  const [audioSpikes, setAudioSpikes] = useState(true)
  const { query, results, loading, active, handleQuery, clearSearch, openFile } = useSearch()

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

  return (
    <>
      <Layout
        orb={orbView}
        chat={chatView}
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
      <MicButton
        isRecording={voice.isRecording}
        state={voice.state}
        onToggle={voice.toggleRecording}
      />
    </>
  )
}
