import type { PipelineEvent } from '../../types/pipeline'

interface ActivityFeedProps {
  events: PipelineEvent[]
}

function formatTs(ts: string): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const LEVEL_COLOR: Record<string, string> = {
  info:    'var(--color-brand)',
  warning: 'var(--color-attack)',
  error:   'var(--color-attack)',
}

const LEVEL_BG: Record<string, string> = {
  info:    'rgba(99,146,250,0.08)',
  warning: 'var(--color-attack-bg)',
  error:   'var(--color-attack-bg)',
}

export default function ActivityFeed({ events }: ActivityFeedProps) {
  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm" style={{ color: 'var(--color-muted)' }}>
        Waiting for predictions…
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto pr-1">
      {events.map((ev) => (
        <div
          key={`${ev.ts}-${ev.message}`}
          className="flex items-start gap-2 px-3 py-2 rounded-neu-sm text-xs"
          style={{
            background: LEVEL_BG[ev.level] || 'rgba(99,146,250,0.06)',
            borderLeft: `3px solid ${LEVEL_COLOR[ev.level] || 'var(--color-brand)'}`,
          }}
        >
          <span className="shrink-0 font-mono" style={{ color: 'var(--color-muted)' }}>
            {formatTs(ev.ts)}
          </span>
          <span
            className="font-semibold shrink-0"
            style={{ color: LEVEL_COLOR[ev.level], textTransform: 'uppercase', letterSpacing: '0.04em' }}
          >
            {ev.stage}
          </span>
          <span style={{ color: 'var(--color-text)', wordBreak: 'break-all' }}>
            {ev.message}
          </span>
        </div>
      ))}
    </div>
  )
}
