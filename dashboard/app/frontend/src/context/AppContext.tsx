import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from 'react'
import type { PipelineStages, PipelineEvent, WsMessage } from '../types/pipeline'

const WS_URL =
  import.meta.env.VITE_WS_URL ||
  (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/pipeline'

const MAX_EVENTS = 50
const RECONNECT_DELAY = 3000

export interface AppState {
  connected: boolean
  pipelineStages: PipelineStages | null
  latestExperimentId: string | null
  events: PipelineEvent[]
  lastUpdateTs: string | null
  selectedExperimentId: string | null
  setSelectedExperimentId: (id: string | null) => void
}

const AppContext = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false)
  const [pipelineStages, setPipelineStages] = useState<PipelineStages | null>(null)
  const [latestExperimentId, setLatestExperimentId] = useState<string | null>(null)
  const [events, setEvents] = useState<PipelineEvent[]>([])
  const [lastUpdateTs, setLastUpdateTs] = useState<string | null>(null)
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (mountedRef.current) setConnected(true)
    }

    ws.onmessage = (ev) => {
      if (!mountedRef.current) return
      try {
        const msg: WsMessage = JSON.parse(ev.data)
        if (msg.type === 'pipeline_status') {
          setPipelineStages(msg.stages)
          setLatestExperimentId(msg.latest_experiment_id)
          setLastUpdateTs(msg.ts)
        } else if (msg.type === 'pipeline_event') {
          setEvents((prev) => [msg, ...prev].slice(0, MAX_EVENTS))
        }
      } catch {
        // ignore malformed frames
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return (
    <AppContext.Provider
      value={{
        connected,
        pipelineStages,
        latestExperimentId,
        events,
        lastUpdateTs,
        selectedExperimentId,
        setSelectedExperimentId,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp(): AppState {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside AppProvider')
  return ctx
}
