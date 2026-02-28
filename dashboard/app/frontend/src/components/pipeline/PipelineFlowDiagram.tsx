import type { PipelineStages } from '../../types/pipeline'

interface Stage {
  key: keyof PipelineStages
  label: string
  icon: string
}

const STAGES: Stage[] = [
  { key: 'ns3',        label: 'NS-3 Sim',    icon: '📡' },
  { key: 'exporter',   label: 'Exporter',    icon: '📤' },
  { key: 'kafka',      label: 'Redpanda',    icon: '🔀' },
  { key: 'windowizer', label: 'Windowizer',  icon: '🪟' },
  { key: 'gcn',        label: 'GCN Detect',  icon: '🧠' },
  { key: 'db',         label: 'TimescaleDB', icon: '🗄️' },
]

const STATE_COLOR: Record<string, string> = {
  active: 'var(--color-normal)',
  idle:   'var(--color-muted)',
  error:  'var(--color-attack)',
}

const STATE_BG: Record<string, string> = {
  active: 'var(--color-normal-bg)',
  idle:   'rgba(113,128,150,0.08)',
  error:  'var(--color-attack-bg)',
}

interface PipelineFlowDiagramProps {
  stages: PipelineStages | null
}

export default function PipelineFlowDiagram({ stages }: PipelineFlowDiagramProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {STAGES.map((s, i) => {
        const stage = stages?.[s.key]
        const state = stage?.state || 'idle'
        const isActive = state === 'active'

        return (
          <div key={s.key} className="flex items-center gap-2">
            {/* Stage node */}
            <div
              className="flex flex-col items-center gap-1 px-3 py-2.5 rounded-neu-sm"
              style={{
                minWidth: 88,
                background: STATE_BG[state],
                boxShadow: isActive
                  ? `0 0 0 2px ${STATE_COLOR[state]}33, var(--shadow-raised-sm)`
                  : 'var(--shadow-raised-sm)',
                border: `1px solid ${STATE_COLOR[state]}44`,
                transition: 'all 0.3s ease',
              }}
            >
              <div className="text-lg leading-none">{s.icon}</div>
              <div className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
                {s.label}
              </div>
              <div className="flex items-center gap-1">
                <div
                  className={`live-dot ${state === 'active' ? 'green' : state === 'error' ? 'red' : 'grey'}`}
                  style={{ width: 6, height: 6 }}
                />
                <span className="text-xs" style={{ color: STATE_COLOR[state] }}>
                  {stage ? `${stage.counter} ${stage.label}` : 'idle'}
                </span>
              </div>
            </div>

            {/* Connector */}
            {i < STAGES.length - 1 && (
              <svg width="28" height="16" viewBox="0 0 28 16">
                <defs>
                  <marker id={`arrow-${i}`} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                    <path d="M0,0 L6,3 L0,6 Z" fill={isActive ? 'var(--color-brand)' : 'var(--color-subtle)'} />
                  </marker>
                </defs>
                <line
                  x1="2" y1="8" x2="22" y2="8"
                  stroke={isActive ? 'var(--color-brand)' : 'var(--color-subtle)'}
                  strokeWidth={isActive ? 2 : 1.5}
                  strokeDasharray={isActive ? '4 3' : undefined}
                  markerEnd={`url(#arrow-${i})`}
                  className={isActive ? 'flow-active' : undefined}
                />
              </svg>
            )}
          </div>
        )
      })}
    </div>
  )
}
