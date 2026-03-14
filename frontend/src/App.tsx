import { Canvas } from '@react-three/fiber'
import Orb from './components/Orb'
import { useMockState } from './hooks/useMockState'

export default function App() {
  const { state, rms } = useMockState()

  return (
    <>
      <Canvas
        camera={{ position: [0, 0, 3], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.1} />
        <Orb state={state} rms={rms} />
      </Canvas>
      <div className="state-label">{state}</div>
    </>
  )
}
