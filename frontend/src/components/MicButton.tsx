import { JarvisState } from '../types'

interface MicButtonProps {
  isRecording: boolean
  state: JarvisState
  onToggle: () => void
}

export default function MicButton({ isRecording, state, onToggle }: MicButtonProps) {
  const isProcessing = !isRecording && (state === 'thinking' || state === 'speaking')

  return (
    <button
      onClick={onToggle}
      disabled={isProcessing}
      style={{
        position: 'fixed',
        bottom: 32,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 64,
        height: 64,
        borderRadius: '50%',
        border: 'none',
        cursor: isProcessing ? 'default' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        background: isRecording
          ? 'rgba(255, 60, 60, 0.85)'
          : isProcessing
            ? 'rgba(100, 100, 120, 0.5)'
            : 'rgba(68, 136, 255, 0.7)',
        boxShadow: isRecording
          ? '0 0 20px rgba(255, 60, 60, 0.5)'
          : '0 0 12px rgba(68, 136, 255, 0.3)',
        transition: 'background 0.2s, box-shadow 0.2s',
        animation: isRecording ? 'mic-pulse 1.5s ease-in-out infinite' : 'none',
      }}
    >
      {isProcessing ? (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style={{ animation: 'spin 1s linear infinite' }}>
          <circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.4)" strokeWidth="2" fill="none" />
          <path d="M12 2a10 10 0 0 1 10 10" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" />
        </svg>
      ) : (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
        </svg>
      )}
    </button>
  )
}
