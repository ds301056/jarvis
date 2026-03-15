import { useState } from 'react'
import { Canvas } from '@react-three/fiber'
import Orb from './components/Orb'
import ChatPanel from './components/ChatPanel'
import DebugOverlay from './components/DebugOverlay'
import Layout from './components/Layout'
import { useJarvisSocket } from './hooks/useJarvisSocket'

export default function App() {
  const { state, rms, rmsSource, messages, currentTokens, connected } = useJarvisSocket()
  const [audioSpikes, setAudioSpikes] = useState(true)

  const orbView = (
    <>
      <Canvas
        camera={{ position: [0, 0, 3], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        style={{ width: '100%', height: '100%' }}
      >
        <ambientLight intensity={0.1} />
        <Orb state={state} rms={rms} audioSpikes={audioSpikes} />
      </Canvas>
      <div className="state-label">{state}{!connected && ' (disconnected)'}</div>
      <button
        onClick={() => setAudioSpikes(v => !v)}
        style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          background: audioSpikes ? 'rgba(68, 136, 255, 0.25)' : 'rgba(255,255,255,0.06)',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: '8px',
          color: audioSpikes ? '#88bbff' : '#666',
          padding: '8px 14px',
          fontSize: '12px',
          cursor: 'pointer',
          fontFamily: 'inherit',
          letterSpacing: '0.5px',
          transition: 'all 0.2s',
        }}
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
        rms={rms}
        rmsSource={rmsSource}
        connected={connected}
        messageCount={messages.length}
      />
    </>
  )
}
