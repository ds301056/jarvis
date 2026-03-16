import { useState, useRef, useCallback } from 'react'

export interface SearchResult {
  file_path: string
  file_name: string
  extension: string
  modified_at: number
  snippet: string
  score: number
}

export function useSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [active, setActive] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([])
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=10`)
      const data = await resp.json()
      setResults(data.results || [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  const handleQuery = useCallback((q: string) => {
    setQuery(q)
    if (!q.trim()) {
      setResults([])
      setActive(false)
      return
    }
    setActive(true)
    // Debounce 300ms
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => doSearch(q), 300)
  }, [doSearch])

  const clearSearch = useCallback(() => {
    setQuery('')
    setResults([])
    setActive(false)
  }, [])

  const openFile = useCallback(async (path: string) => {
    await fetch(`/api/files/open?path=${encodeURIComponent(path)}`)
  }, [])

  return { query, results, loading, active, handleQuery, clearSearch, openFile }
}
