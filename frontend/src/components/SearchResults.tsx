import React from 'react'
import { SearchResult } from '../hooks/useSearch'

const FILE_ICONS: Record<string, string> = {
  '.pdf': '\uD83D\uDCC4',
  '.xlsx': '\uD83D\uDCCA',
  '.xls': '\uD83D\uDCCA',
  '.pptx': '\uD83D\uDCCA',
  '.docx': '\uD83D\uDCC3',
  '.py': '\uD83D\uDC0D',
  '.js': '\uD83D\uDFE8',
  '.ts': '\uD83D\uDD35',
  '.md': '\uD83D\uDCDD',
  '.txt': '\uD83D\uDCC4',
  '.json': '\uD83D\uDD27',
  '.csv': '\uD83D\uDCCA',
}

interface SearchResultsProps {
  results: SearchResult[]
  loading: boolean
  query: string
  onOpenFile: (path: string) => void
}

export default function SearchResults({ results, loading, query, onOpenFile }: SearchResultsProps) {
  if (loading) {
    return <div style={styles.status}>Searching...</div>
  }

  if (query && results.length === 0) {
    return <div style={styles.status}>No results for "{query}"</div>
  }

  if (results.length === 0) return null

  return (
    <div style={styles.container}>
      <div style={styles.count}>{results.length} result{results.length !== 1 ? 's' : ''}</div>
      {results.map((r, i) => (
        <div key={i} style={styles.card}>
          <div style={styles.header}>
            <span style={styles.fileIcon}>{FILE_ICONS[r.extension] || '\uD83D\uDCC1'}</span>
            <div style={styles.fileInfo}>
              <div style={styles.fileName}>{r.file_name}</div>
              <div style={styles.filePath}>{truncatePath(r.file_path)}</div>
            </div>
            <button onClick={() => onOpenFile(r.file_path)} style={styles.openBtn}>
              Open
            </button>
          </div>
          <div style={styles.snippet}>{r.snippet}</div>
          <div style={styles.meta}>
            {new Date(r.modified_at * 1000).toLocaleDateString()}
          </div>
        </div>
      ))}
    </div>
  )
}

function truncatePath(path: string, maxLen = 60): string {
  if (path.length <= maxLen) return path
  const parts = path.split('/')
  // Show first dir + ... + last 2 dirs + filename
  if (parts.length > 4) {
    return parts[0] + '/.../' + parts.slice(-3).join('/')
  }
  return '...' + path.slice(-maxLen)
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  status: {
    padding: '20px',
    textAlign: 'center',
    color: 'rgba(255,255,255,0.4)',
    fontSize: '14px',
  },
  count: {
    fontSize: '11px',
    color: 'rgba(255,255,255,0.3)',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    padding: '4px 0',
  },
  card: {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '8px',
    padding: '10px 12px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  fileIcon: {
    fontSize: '20px',
    flexShrink: 0,
  },
  fileInfo: {
    flex: 1,
    minWidth: 0,
  },
  fileName: {
    fontWeight: 600,
    fontSize: '13px',
    color: '#e0e0e0',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  filePath: {
    fontSize: '11px',
    color: 'rgba(255,255,255,0.3)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  openBtn: {
    flexShrink: 0,
    background: 'rgba(68,136,255,0.15)',
    border: '1px solid rgba(68,136,255,0.3)',
    borderRadius: '6px',
    color: '#88bbff',
    fontSize: '12px',
    padding: '4px 10px',
    cursor: 'pointer',
  },
  snippet: {
    fontSize: '12px',
    lineHeight: '1.5',
    color: 'rgba(255,255,255,0.5)',
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  meta: {
    fontSize: '10px',
    color: 'rgba(255,255,255,0.2)',
    marginTop: '4px',
  },
}
