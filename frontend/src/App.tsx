import { Canvas } from '@react-three/fiber'
import Orb from './components/Orb'
import ChatPanel from './components/ChatPanel'
import DebugOverlay from './components/DebugOverlay'
import Layout from './components/Layout'
import { useJarvisSocket } from './hooks/useJarvisSocket'

export default function App() {
  const { state, rms, rmsSource, messages, currentTokens, connected } = useJarvisSocket()

  const orbView = (
    <>
      <Canvas
        camera={{ position: [0, 0, 3], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        style={{ width: '100%', height: '100%' }}
      >
        <ambientLight intensity={0.1} />
        <Orb state={state} rms={rms} />
      </Canvas>
      <div className="state-label">{state}{!connected && ' (disconnected)'}</div>
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
