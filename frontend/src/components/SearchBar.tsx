import React from 'react'

interface SearchBarProps {
  query: string
  onQueryChange: (q: string) => void
  onClear: () => void
  loading: boolean
}

export default function SearchBar({ query, onQueryChange, onClear, loading }: SearchBarProps) {
  return (
    <div style={styles.container}>
      <div style={styles.inputWrap}>
        <span style={styles.icon}>{loading ? '\u23F3' : '\uD83D\uDD0D'}</span>
        <input
          type="text"
          value={query}
          onChange={e => onQueryChange(e.target.value)}
          placeholder="Search files..."
          style={styles.input}
        />
        {query && (
          <button onClick={onClear} style={styles.clearBtn}>&times;</button>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '8px 12px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  inputWrap: {
    display: 'flex',
    alignItems: 'center',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '8px',
    padding: '0 10px',
  },
  icon: {
    fontSize: '14px',
    marginRight: '8px',
    opacity: 0.5,
  },
  input: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#d0d0d0',
    fontSize: '14px',
    padding: '8px 0',
    fontFamily: 'inherit',
  },
  clearBtn: {
    background: 'none',
    border: 'none',
    color: 'rgba(255,255,255,0.4)',
    fontSize: '18px',
    cursor: 'pointer',
    padding: '0 4px',
    lineHeight: 1,
  },
}
