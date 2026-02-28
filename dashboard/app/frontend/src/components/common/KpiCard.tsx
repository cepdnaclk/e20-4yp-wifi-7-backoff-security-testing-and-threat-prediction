import type { ReactNode } from 'react'

interface KpiCardProps {
  label: string
  value: ReactNode
  delta?: string
  deltaType?: 'positive' | 'negative' | 'neutral'
  icon?: ReactNode
  accent?: string
}

export default function KpiCard({ label, value, delta, deltaType = 'neutral', icon, accent }: KpiCardProps) {
  return (
    <div className="kpi-card" style={accent ? { borderTop: `3px solid ${accent}` } : {}}>
      <div className="flex items-start justify-between">
        <div className="kpi-label">{label}</div>
        {icon && (
          <div style={{ color: accent || 'var(--color-brand)', opacity: 0.8 }}>{icon}</div>
        )}
      </div>
      <div className="kpi-value">{value}</div>
      {delta && (
        <div className={`kpi-delta ${deltaType}`}>{delta}</div>
      )}
    </div>
  )
}
