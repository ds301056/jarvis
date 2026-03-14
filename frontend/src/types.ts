export type JarvisState = 'idle' | 'listening' | 'thinking' | 'speaking'

export interface StateConfig {
  speed: number
  amplitude: number
  color: [number, number, number]
  noiseScale: number
}

export const STATE_CONFIGS: Record<JarvisState, StateConfig> = {
  idle: {
    speed: 0.3,
    amplitude: 0.05,
    color: [0.27, 0.53, 1.0],    // #4488ff
    noiseScale: 1.0,
  },
  listening: {
    speed: 1.5,
    amplitude: 0.12,
    color: [0.27, 1.0, 0.67],    // #44ffaa
    noiseScale: 1.4,
  },
  thinking: {
    speed: 0.8,
    amplitude: 0.08,
    color: [0.67, 0.4, 1.0],     // #aa66ff
    noiseScale: 1.2,
  },
  speaking: {
    speed: 0.6,
    amplitude: 0.15,              // base — RMS overrides this
    color: [0.27, 0.53, 1.0],    // #4488ff
    noiseScale: 1.0,
  },
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  final: boolean
}
