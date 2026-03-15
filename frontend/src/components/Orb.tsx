import { useRef, useMemo } from 'react'
import React from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { vertexShader, fragmentShader } from './OrbShaderMaterial'
import { JarvisState, STATE_CONFIGS } from '../types'
import { RmsRef } from '../hooks/useJarvisSocket'

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

function lerpColor(a: [number, number, number], b: [number, number, number], t: number): [number, number, number] {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]
}

interface OrbProps {
  state: JarvisState
  rmsRef: React.MutableRefObject<RmsRef>
  audioSpikes?: boolean  // when true, show dramatic spikes during speaking/listening
}

export default function Orb({ state, rmsRef, audioSpikes = false }: OrbProps) {
  const meshRef = useRef<THREE.Mesh>(null)

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uAmplitude: { value: 0.05 },
      uSpeed: { value: 0.3 },
      uNoiseScale: { value: 1.0 },
      uColor: { value: new THREE.Vector3(0.27, 0.53, 1.0) },
      uSpikeAmount: { value: 0 },
    }),
    []
  )

  // Track current values for lerping
  const current = useRef({
    amplitude: 0.05,
    speed: 0.3,
    noiseScale: 1.0,
    color: [0.27, 0.53, 1.0] as [number, number, number],
    rotationY: 0,
    spikeAmount: 0,
  })

  useFrame((_, delta) => {
    if (!meshRef.current) return

    const rms = rmsRef.current.value
    const config = STATE_CONFIGS[state]
    const lerpFactor = 1 - Math.pow(0.001, delta) // ~smooth over 300ms

    // Target amplitude: for speaking state, blend base with RMS
    let targetAmplitude = config.amplitude
    if (state === 'speaking') {
      targetAmplitude = lerp(0.05, 0.25, rms)
    } else if (state === 'listening') {
      targetAmplitude = lerp(config.amplitude, 0.2, rms)
    }

    current.current.amplitude = lerp(current.current.amplitude, targetAmplitude, lerpFactor)
    current.current.speed = lerp(current.current.speed, config.speed, lerpFactor)
    current.current.noiseScale = lerp(current.current.noiseScale, config.noiseScale, lerpFactor)
    current.current.color = lerpColor(current.current.color, config.color, lerpFactor)

    // Spike amount: ramp up when speaking/listening with audioSpikes on, otherwise 0
    const targetSpike = audioSpikes && (state === 'speaking' || state === 'listening') ? rms : 0
    current.current.spikeAmount = lerp(current.current.spikeAmount, targetSpike, lerpFactor)

    uniforms.uTime.value += delta
    uniforms.uAmplitude.value = current.current.amplitude
    uniforms.uSpeed.value = current.current.speed
    uniforms.uNoiseScale.value = current.current.noiseScale
    uniforms.uColor.value.set(...current.current.color)
    uniforms.uSpikeAmount.value = current.current.spikeAmount

    // Slow rotation during thinking state
    if (state === 'thinking') {
      current.current.rotationY += delta * 0.5
    }
    meshRef.current.rotation.y = current.current.rotationY
  })

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1, 64]} />
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
      />
    </mesh>
  )
}
