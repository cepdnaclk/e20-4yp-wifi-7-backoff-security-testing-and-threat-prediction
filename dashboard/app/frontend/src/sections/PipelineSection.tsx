import { useApp } from '../context/AppContext'
import SectionTitle from '../components/common/SectionTitle'
import KpiCard from '../components/common/KpiCard'
import LiveIndicator from '../components/common/LiveIndicator'
import PipelineFlowDiagram from '../components/pipeline/PipelineFlowDiagram'
import ActivityFeed from '../components/pipeline/ActivityFeed'
import { Activity, Database, Cpu } from 'lucide-react'
import type { PipelineStages } from '../types/pipeline'
import { PIPELINE_STAGE_META } from '../components/pipeline/stageMeta'

function getCurrentStageKey(stages: PipelineStages | null): keyof PipelineStages | null {
  if (!stages) return null

  const nonDbActive = PIPELINE_STAGE_META
    .filter((meta) => meta.key !== 'db')
    .map((meta) => ({ meta, stage: stages[meta.key] }))
    .filter((item) => item.stage?.state === 'active')
    .sort((a, b) => {
      const aTs = new Date(a.stage?.last_activity_ts || 0).getTime()
      const bTs = new Date(b.stage?.last_activity_ts || 0).getTime()
      return bTs - aTs
    })

  if (nonDbActive.length > 0) return nonDbActive[0].meta.key

  const anyActive = PIPELINE_STAGE_META
    .map((meta) => ({ meta, stage: stages[meta.key] }))
    .filter((item) => item.stage?.state === 'active')
    .sort((a, b) => {
      const aTs = new Date(a.stage?.last_activity_ts || 0).getTime()
      const bTs = new Date(b.stage?.last_activity_ts || 0).getTime()
      return bTs - aTs
    })

  if (anyActive.length > 0) return anyActive[0].meta.key
  return null
}

function getPipelineProgressPercent(stages: PipelineStages | null, currentStageKey: keyof PipelineStages | null): number {
  if (!stages) return 0
  if (!currentStageKey) {
    return (stages.db?.counter ?? 0) > 0 ? 100 : 0
  }
  const idx = PIPELINE_STAGE_META.findIndex((meta) => meta.key === currentStageKey)
  if (idx < 0) return 0
  const currentStage = stages[currentStageKey]
  if (currentStageKey === 'db' && currentStage?.state === 'active') return 100
  const stageFraction = currentStage?.state === 'active' ? 0.6 : 1
  const progress = ((idx + stageFraction) / PIPELINE_STAGE_META.length) * 100
  return Math.max(0, Math.min(100, Math.round(progress)))
}

export default function PipelineSection() {
  const { pipelineStages, events, latestExperimentId, connected, lastUpdateTs } = useApp()

  const gcn = pipelineStages?.gcn
  const db = pipelineStages?.db
  const ns3 = pipelineStages?.ns3
  const currentStageKey = getCurrentStageKey(pipelineStages)
  const currentStageLabel = currentStageKey
    ? PIPELINE_STAGE_META.find((meta) => meta.key === currentStageKey)?.label || 'Unknown'
    : 'Waiting for telemetry'
  const progressPercent = getPipelineProgressPercent(pipelineStages, currentStageKey)
  const currentStageNumber = currentStageKey ? PIPELINE_STAGE_META.findIndex((meta) => meta.key === currentStageKey) + 1 : 0

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
        <div className="mb-4 flex flex-col gap-3">
          <div className="section-title text-base">Data Flow</div>
          <div className="section-subtitle">Real-time pipeline stage status with active stage and progress</div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div className="neu-inset flex items-center justify-between">
              <span className="text-sm" style={{ color: 'var(--color-muted)' }}>
                Current Stage
              </span>
              <span className="text-sm font-semibold">
                {currentStageLabel}
                {currentStageNumber > 0 ? ` (${currentStageNumber}/${PIPELINE_STAGE_META.length})` : ''}
              </span>
            </div>
            <div className="neu-inset">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm" style={{ color: 'var(--color-muted)' }}>Pipeline Progress</span>
                <span className="text-sm font-semibold">{progressPercent}%</span>
              </div>
              <div
                className="w-full h-2 rounded-full"
                style={{ background: 'rgba(113, 128, 150, 0.16)' }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${progressPercent}%`,
                    background: 'linear-gradient(90deg, var(--color-brand), var(--color-normal))',
                  }}
                />
              </div>
            </div>
          </div>
        </div>
        <PipelineFlowDiagram stages={pipelineStages} currentStageKey={currentStageKey} />
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
