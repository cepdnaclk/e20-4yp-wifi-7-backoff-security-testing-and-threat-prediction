import { useState, useEffect, useCallback } from 'react'
import { useApi } from './useApi'
import type { ModelListResponse, ActiveModelDetail, InferenceStats } from '../types/models'

export function useModels() {
  return useApi<ModelListResponse>('/api/models', 30_000)
}

export function useActiveModel() {
  return useApi<ActiveModelDetail>('/api/models/active', 30_000)
}

export function useInferenceStats() {
  return useApi<InferenceStats>('/api/models/inference-stats', 10_000)
}

export function useModelDetail(version: string | null) {
  const [data, setData] = useState<ActiveModelDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    if (!version) { setData(null); return }
    setLoading(true)
    setError(null)
    try {
      const res = await window.fetch(`/api/models/${version}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setData(await res.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [version])

  useEffect(() => { fetch() }, [fetch])

  return { data, loading, error, refetch: fetch }
}

export async function deployModel(version: string): Promise<{ deployed: string; detector_restarted: boolean; message: string }> {
  const res = await window.fetch(`/api/models/${version}/deploy`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Deploy failed')
  }
  return res.json()
}
