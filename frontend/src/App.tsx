import { useState } from 'react'
import * as THREE from 'three'
import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import Orb from './components/Orb'
import Particles from './components/Particles'
import ChatPanel from './components/ChatPanel'
import DebugOverlay from './components/DebugOverlay'
import Layout from './components/Layout'
import { useJarvisSocket } from './hooks/useJarvisSocket'

export default function App() {
  const { state, messages, currentTokens, connected, rmsRef } = useJarvisSocket()
  const [audioSpikes, setAudioSpikes] = useState(true)

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

  return (
    <>
      <Layout orb={orbView} chat={chatView} />
      <DebugOverlay
        state={state}
        rmsRef={rmsRef}
        connected={connected}
        messageCount={messages.length}
      />
    </>
  )
}
