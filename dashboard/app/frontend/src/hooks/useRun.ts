import { useState, useEffect, useCallback, useRef } from 'react'

export interface LaunchRequest {
  scenario: 'normal' | 'positive' | 'negative' | 'dynamic'
  seed: number
  sim_time: number
  bias: number
  num_ap: number
  num_sta: number
  segment_length: 32 | 64 | 128 | 256
  experiment_id?: string
  gcn_version?: string
  phases?: string   // dynamic scenario only: "t0:b0,t1:b1,..." e.g. "0:0,20:5000,40:-5000"
}

export interface RunStatus {
  active: boolean
  experiment_id: string | null
  stage: string | null
  state: string | null
  progress_pct: number | null
  message: string | null
  started_at: string | null
  updated_at: string | null
}

export interface HistoryEntry {
  experiment_id: string
  scenario: string
  num_ap: number
  num_sta: number
  sim_time: number
  segment_length: number
  gcn_version?: string
  started_at: string
  completed_at: string | null
  outcome: 'success' | 'failed' | 'cancelled' | 'running'
}

const BASE = '/api'

export function useRunStatus(pollInterval = 2000) {
  const [status, setStatus] = useState<RunStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetch_ = useCallback(async () => {
    try {
      const res = await fetch(`${BASE}/run/status`)
      if (!res.ok) throw new Error(await res.text())
      setStatus(await res.json())
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    fetch_()
    timerRef.current = setInterval(fetch_, pollInterval)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [fetch_, pollInterval])

  return { status, error, refresh: fetch_ }
}

export function useRunHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/run/history`)
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setHistory(data.history || [])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return { history, loading, reload: load }
}

export async function launchExperiment(req: LaunchRequest): Promise<{ ok: boolean; experiment_id: string; message: string }> {
  const res = await fetch(`${BASE}/run/launch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.text() }))
    throw new Error(err.detail || 'Launch failed')
  }
  return res.json()
}

export async function cancelRun(): Promise<void> {
  const res = await fetch(`${BASE}/run/cancel`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
}
