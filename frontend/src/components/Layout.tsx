import { useState, useEffect, ReactNode } from 'react'

interface LayoutProps {
  orb: ReactNode
  chat: ReactNode
  searchBar: ReactNode
  searchResults: ReactNode
  searchActive: boolean
}

export default function Layout({ orb, chat, searchBar, searchResults, searchActive }: LayoutProps) {
  const [compact, setCompact] = useState(false)

  useEffect(() => {
    const check = () => {
      setCompact(window.innerHeight < 800)
    }
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  if (!compact) {
    // Fullscreen: orb with search overlay at bottom
    return (
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        {orb}
        <div style={styles.searchOverlay}>
          {searchBar}
          {searchActive && (
            <div style={styles.searchResultsWrap}>
              {searchResults}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Compact: orb top, search bar + (results or chat) bottom
  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: '0 0 55%', minHeight: 0 }}>{orb}</div>
      <div style={{ flex: '0 0 45%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {searchBar}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {searchActive ? searchResults : chat}
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  searchOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    background: 'rgba(10, 10, 21, 0.92)',
    borderTop: '1px solid rgba(255,255,255,0.08)',
    display: 'flex',
    flexDirection: 'column',
  },
  searchResultsWrap: {
    maxHeight: '40vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
}
