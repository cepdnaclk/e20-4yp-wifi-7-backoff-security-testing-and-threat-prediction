import { Wifi, Circle } from 'lucide-react'
import { useApp } from '../../context/AppContext'

function timeAgo(ts: string | null): string {
  if (!ts) return 'never'
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (diff < 5) return 'just now'
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export default function TopBar() {
  const { connected, lastUpdateTs } = useApp()

  return (
    <header
      className="flex items-center justify-between px-6 py-3 shrink-0"
      style={{
        background: 'var(--color-bg)',
        boxShadow: '0 2px 8px rgba(166,180,200,0.4)',
        zIndex: 10,
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="flex items-center justify-center rounded-neu-sm"
          style={{
            width: 36,
            height: 36,
            background: 'linear-gradient(135deg, var(--color-brand), #a78bfa)',
            boxShadow: 'var(--shadow-brand)',
          }}
        >
          <Wifi size={18} color="white" />
        </div>
        <div>
          <div className="font-bold text-sm" style={{ color: 'var(--color-text)', letterSpacing: '-0.01em' }}>
            NDT Wi-Fi 7 MLO
          </div>
          <div className="text-xs" style={{ color: 'var(--color-muted)' }}>
            Digital Twin Security Dashboard
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-xs" style={{ color: 'var(--color-muted)' }}>
          Updated {timeAgo(lastUpdateTs)}
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`live-dot ${connected ? 'green' : 'grey'}`} />
          <span className="text-xs font-medium" style={{ color: connected ? 'var(--color-normal)' : 'var(--color-subtle)' }}>
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>
    </header>
  )
}
