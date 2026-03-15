import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const PARTICLE_COUNT = 200

export default function Particles() {
  const pointsRef = useRef<THREE.Points>(null)
  const timeRef = useRef(0)

  const { positions, speeds } = useMemo(() => {
    const positions = new Float32Array(PARTICLE_COUNT * 3)
    const speeds = new Float32Array(PARTICLE_COUNT)
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Spread particles in a sphere around the orb
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 1.8 + Math.random() * 4
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = r * Math.cos(phi)
      speeds[i] = 0.02 + Math.random() * 0.04
    }
    return { positions, speeds }
  }, [])

  useFrame((_, delta) => {
    if (!pointsRef.current) return
    timeRef.current += delta
    const geo = pointsRef.current.geometry
    const pos = geo.attributes.position as THREE.BufferAttribute
    const arr = pos.array as Float32Array

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Slow orbital drift
      const x = arr[i * 3]
      const z = arr[i * 3 + 2]
      const speed = speeds[i] * delta
      arr[i * 3] = x * Math.cos(speed) - z * Math.sin(speed)
      arr[i * 3 + 2] = x * Math.sin(speed) + z * Math.cos(speed)
      // Gentle vertical bob (using frame-consistent accumulated time)
      arr[i * 3 + 1] += Math.sin(timeRef.current + i) * 0.001
    }
    pos.needsUpdate = true
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={PARTICLE_COUNT}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.015}
        color="#4466aa"
        transparent
        opacity={0.35}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  )
}
