import { useApp } from '../context/AppContext'
import SectionTitle from '../components/common/SectionTitle'
import KpiCard from '../components/common/KpiCard'
import LiveIndicator from '../components/common/LiveIndicator'
import PipelineFlowDiagram from '../components/pipeline/PipelineFlowDiagram'
import ActivityFeed from '../components/pipeline/ActivityFeed'
import { Activity, Database, Cpu } from 'lucide-react'

export default function PipelineSection() {
  const { pipelineStages, events, latestExperimentId, connected, lastUpdateTs } = useApp()

  const gcn = pipelineStages?.gcn
  const db = pipelineStages?.db
  const ns3 = pipelineStages?.ns3

  function timeAgo(ts: string | null): string {
    if (!ts) return '—'
    const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
    if (diff < 5) return 'just now'
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return `${Math.floor(diff / 3600)}h ago`
  }

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle
        title="Pipeline Monitor"
        subtitle="Live NS-3 → GCN detection pipeline status"
        actions={<LiveIndicator active={connected} label={connected ? 'Live' : 'Disconnected'} />}
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          label="Total Metrics"
          value={ns3 ? ns3.counter.toLocaleString() : '—'}
          icon={<Activity size={18} />}
          accent="var(--color-brand)"
        />
        <KpiCard
          label="Total Predictions"
          value={db ? db.counter.toLocaleString() : '—'}
          icon={<Cpu size={18} />}
          accent="var(--color-normal)"
        />
        <KpiCard
          label="Last Update"
          value={timeAgo(lastUpdateTs)}
          accent="var(--color-warning)"
        />
        <KpiCard
          label="Active Experiment"
          value={
            latestExperimentId
              ? <span className="text-sm font-semibold truncate block" title={latestExperimentId}>
                  {latestExperimentId.split('-').slice(-2).join('-')}
                </span>
              : '—'
          }
          icon={<Database size={18} />}
          accent="var(--color-brand)"
        />
      </div>

      {/* Flow diagram */}
      <div className="neu-card">
        <div className="mb-4">
          <div className="section-title text-base">Data Flow</div>
          <div className="section-subtitle">Real-time pipeline stage status</div>
        </div>
        <PipelineFlowDiagram stages={pipelineStages} />
      </div>

      {/* GCN stats + Activity feed */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="neu-card">
          <div className="section-title text-base mb-3">GCN Detector</div>
          <div className="flex flex-col gap-3">
            {[
              { label: 'Segments processed', value: gcn?.counter ?? '—' },
              { label: 'Stage state', value: gcn?.state ?? '—' },
              { label: 'Last prediction', value: gcn?.last_activity_ts ? timeAgo(gcn.last_activity_ts) : '—' },
            ].map(({ label, value }) => (
              <div key={label} className="neu-inset flex justify-between items-center">
                <span className="text-sm" style={{ color: 'var(--color-muted)' }}>{label}</span>
                <span className="text-sm font-semibold">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="neu-card">
          <div className="section-title text-base mb-3">Live Activity Feed</div>
          <ActivityFeed events={events} />
        </div>
      </div>
    </div>
  )
}
