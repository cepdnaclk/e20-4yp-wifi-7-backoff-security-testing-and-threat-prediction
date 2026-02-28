import { useState } from 'react'
import SectionTitle from '../components/common/SectionTitle'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorBanner from '../components/common/ErrorBanner'
import MetricLineChart from '../components/charts/MetricLineChart'
import { useExperiments, useMetricsSummary, useMetricSeries } from '../hooks/useExperiments'
import { useApp } from '../context/AppContext'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

const ALL_METRICS = [
  'backoff_slots', 'throughput_mbps', 'packet_loss_rate', 'delay_ms',
  'channel_busy_ratio', 'retry_count', 'link1_usage', 'link2_usage',
  'mcs_index', 'rssi_dbm', 'snr_db', 'queue_depth', 'jitter_ms',
]

const METRIC_COLORS: Record<string, string> = {
  backoff_slots:     'var(--color-brand)',
  throughput_mbps:   'var(--color-normal)',
  packet_loss_rate:  'var(--color-attack)',
  delay_ms:          '#f97316',
  channel_busy_ratio:'#a78bfa',
  retry_count:       '#f59e0b',
  link1_usage:       '#06b6d4',
  link2_usage:       '#0ea5e9',
  mcs_index:         '#8b5cf6',
  rssi_dbm:          '#10b981',
  snr_db:            '#14b8a6',
  queue_depth:       '#f43f5e',
  jitter_ms:         '#fb923c',
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'up')   return <TrendingUp size={14} color="var(--color-normal)" />
  if (trend === 'down') return <TrendingDown size={14} color="var(--color-attack)" />
  return <Minus size={14} color="var(--color-subtle)" />
}

export default function NetworkHealthSection() {
  const { latestExperimentId } = useApp()
  const { data: expList } = useExperiments(50)
  const [selectedExp, setSelectedExp] = useState<string | null>(null)
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null)

  const activeId = selectedExp || latestExperimentId
  const { data: metricsSummary, loading, error } = useMetricsSummary(activeId)
  const { data: expandedSeries } = useMetricSeries(
    expandedMetric ? activeId : null,
    expandedMetric || '',
  )

  const experiments = expList?.experiments || []

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle
        title="Network Health"
        subtitle="All 13 telemetry metrics with trends and time-series drill-down"
      />

      {/* Experiment picker */}
      <div className="neu-card">
        <div className="section-title text-sm mb-3">Experiment</div>
        <div className="flex flex-wrap gap-2">
          {experiments.slice(0, 12).map((e) => (
            <button
              key={e.experiment_id}
              className={`neu-btn text-xs py-1 ${activeId === e.experiment_id ? 'neu-btn-primary' : ''}`}
              onClick={() => setSelectedExp(e.experiment_id)}
            >
              {e.experiment_id.split('-').slice(-3).join('-')}
            </button>
          ))}
        </div>
      </div>

      {loading && <LoadingSpinner message="Loading metrics…" />}
      {error && <ErrorBanner message={error} />}

      {/* Metrics grid */}
      {metricsSummary && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {metricsSummary.metrics.map((m) => {
            const isExpanded = expandedMetric === m.metric_name
            return (
              <div
                key={m.metric_name}
                className="neu-card cursor-pointer"
                style={{
                  border: isExpanded ? '2px solid var(--color-brand)' : '2px solid transparent',
                  transition: 'border 0.2s ease',
                }}
                onClick={() =>
                  setExpandedMetric(isExpanded ? null : m.metric_name)
                }
              >
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div
                      className="text-xs font-semibold uppercase tracking-wider"
                      style={{ color: METRIC_COLORS[m.metric_name] || 'var(--color-brand)' }}
                    >
                      {m.metric_name.replace(/_/g, ' ')}
                    </div>
                    {m.unit && (
                      <div className="text-xs" style={{ color: 'var(--color-subtle)' }}>{m.unit}</div>
                    )}
                  </div>
                  <TrendIcon trend={m.trend} />
                </div>

                <div className="text-2xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>
                  {m.avg.toFixed(3)}
                </div>

                <div className="grid grid-cols-3 gap-1 text-xs">
                  {[
                    { label: 'min', value: m.min.toFixed(3) },
                    { label: 'max', value: m.max.toFixed(3) },
                    { label: 'σ',   value: m.std.toFixed(3) },
                  ].map(({ label, value }) => (
                    <div
                      key={label}
                      className="neu-inset text-center py-1"
                    >
                      <div style={{ color: 'var(--color-subtle)' }}>{label}</div>
                      <div className="font-semibold">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Expanded metric time-series */}
      {expandedMetric && expandedSeries && (
        <div className="neu-card">
          <div className="section-title text-base mb-3">
            {expandedMetric.replace(/_/g, ' ')} — Time Series
            {expandedSeries.unit ? ` (${expandedSeries.unit})` : ''}
          </div>
          <MetricLineChart
            data={expandedSeries.points}
            unit={expandedSeries.unit ? ` ${expandedSeries.unit}` : ''}
            color={METRIC_COLORS[expandedMetric] || 'var(--color-brand)'}
            name={expandedMetric.replace(/_/g, ' ')}
            height={220}
          />
        </div>
      )}
    </div>
  )
}
