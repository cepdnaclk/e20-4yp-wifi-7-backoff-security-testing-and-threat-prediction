import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json() as Promise<T>
}

interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useApi<T>(path: string | null, refreshMs?: number): ApiState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const fetchData = useCallback(async () => {
    if (!path) return
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}${path}`, { signal: ctrl.signal })
      if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`)
      const json = await res.json()
      if (!ctrl.signal.aborted) setData(json)
    } catch (e) {
      if (!ctrl.signal.aborted) setError(e instanceof Error ? e.message : String(e))
    } finally {
      if (!ctrl.signal.aborted) setLoading(false)
    }
  }, [path])

  useEffect(() => {
    fetchData()
    if (refreshMs) {
      const t = setInterval(fetchData, refreshMs)
      return () => clearInterval(t)
    }
    return () => abortRef.current?.abort()
  }, [fetchData, refreshMs])

  return { data, loading, error, refetch: fetchData }
}
