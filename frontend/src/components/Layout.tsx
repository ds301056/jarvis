import { useState, useEffect, ReactNode } from 'react'

interface LayoutProps {
  orb: ReactNode
  chat: ReactNode
}

export default function Layout({ orb, chat }: LayoutProps) {
  const [compact, setCompact] = useState(false)

  useEffect(() => {
    const check = () => {
      // Switch to compact (orb + chat) when window is shorter than ~800px
      setCompact(window.innerHeight < 800)
    }
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  if (!compact) {
    // Fullscreen: just the orb
    return <div style={{ width: '100%', height: '100%' }}>{orb}</div>
  }

  // Compact: orb top, chat bottom
  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ flex: '0 0 55%', minHeight: 0 }}>{orb}</div>
      <div style={{ flex: '0 0 45%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {chat}
      </div>
    </div>
  )
}
