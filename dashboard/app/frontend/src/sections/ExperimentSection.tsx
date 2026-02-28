import { useState } from 'react'
import { useApp } from '../context/AppContext'
import SectionTitle from '../components/common/SectionTitle'
import KpiCard from '../components/common/KpiCard'
import Badge from '../components/common/Badge'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorBanner from '../components/common/ErrorBanner'
import MetricLineChart from '../components/charts/MetricLineChart'
import { useExperiments, useExperimentSummary, useExperimentPredictions, useMetricSeries } from '../hooks/useExperiments'
import type { Experiment } from '../types/experiments'

const METRIC_OPTIONS = [
  'backoff_slots', 'throughput_mbps', 'packet_loss_rate',
  'delay_ms', 'channel_busy_ratio',
]

export default function ExperimentSection() {
  const { selectedExperimentId, setSelectedExperimentId, latestExperimentId } = useApp()
  const [selectedMetric, setSelectedMetric] = useState('backoff_slots')

  const activeId = selectedExperimentId || latestExperimentId
  const { data: expList, loading: expLoading, error: expError } = useExperiments(50)
  const { data: summary } = useExperimentSummary(activeId)
  const { data: preds } = useExperimentPredictions(activeId)
  const { data: series } = useMetricSeries(activeId, selectedMetric)

  const experiments: Experiment[] = expList?.experiments || []

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle title="Experiment View" subtitle="Per-experiment metrics, predictions, and analysis" />

      {/* Experiment selector */}
      <div className="neu-card">
        <div className="section-title text-sm mb-3">Select Experiment</div>
        {expLoading && <LoadingSpinner message="Loading experiments…" />}
        {expError && <ErrorBanner message={expError} />}
        <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
          {experiments.map((e) => (
            <button
              key={e.experiment_id}
              className={`neu-btn text-xs ${activeId === e.experiment_id ? 'neu-btn-primary' : ''}`}
              onClick={() => setSelectedExperimentId(e.experiment_id)}
            >
              {e.experiment_id.split('-').slice(-3).join('-')}
              <Badge
                variant={e.inferred_type === 'normal' ? 'normal' : e.inferred_type === 'attack' ? 'attack' : 'neutral'}
                label={e.inferred_type}
              />
            </button>
          ))}
        </div>
      </div>

      {activeId && summary && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              label="Segments"
              value={summary.segment_count}
              accent="var(--color-brand)"
            />
            <KpiCard
              label="Attack Rate"
              value={`${(summary.attack_rate * 100).toFixed(1)}%`}
              accent={summary.attack_rate > 0.5 ? 'var(--color-attack)' : 'var(--color-normal)'}
            />
            <KpiCard
              label="Avg Confidence"
              value={summary.avg_confidence != null ? `${(summary.avg_confidence * 100).toFixed(1)}%` : '—'}
              accent="var(--color-brand)"
            />
            <KpiCard
              label="Avg Inference"
              value={summary.avg_inference_time_ms != null ? `${summary.avg_inference_time_ms.toFixed(1)}ms` : '—'}
              accent="var(--color-normal)"
            />
          </div>

          {/* Metric chart */}
          <div className="neu-card">
            <div className="flex items-center justify-between mb-4">
              <div className="section-title text-base">Metric Evolution</div>
              <div className="flex gap-2 flex-wrap">
                {METRIC_OPTIONS.map((m) => (
                  <button
                    key={m}
                    className={`neu-btn text-xs py-1 ${selectedMetric === m ? 'neu-btn-primary' : ''}`}
                    onClick={() => setSelectedMetric(m)}
                  >
                    {m.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>
            {series ? (
              <MetricLineChart
                data={series.points}
                unit={series.unit ? ` ${series.unit}` : ''}
                name={selectedMetric.replace(/_/g, ' ')}
                height={200}
              />
            ) : (
              <LoadingSpinner />
            )}
          </div>

          {/* Predictions table */}
          {preds && preds.predictions.length > 0 && (
            <div className="neu-card overflow-hidden">
              <div className="section-title text-base mb-3">Segment Predictions</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      {['#', 'Prediction', 'Confidence', 'Window', 'Inference (ms)'].map((h) => (
                        <th key={h} className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-muted)', borderBottom: '1px solid rgba(166,180,200,0.3)' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preds.predictions.slice(0, 50).map((p) => (
                      <tr
                        key={p.id}
                        style={{
                          borderBottom: '1px solid rgba(166,180,200,0.15)',
                          background: p.prediction === 1 ? 'rgba(232,93,106,0.04)' : undefined,
                        }}
                      >
                        <td className="py-2 px-3 font-mono text-xs" style={{ color: 'var(--color-muted)' }}>{p.segment_number}</td>
                        <td className="py-2 px-3">
                          <Badge variant={p.prediction === 1 ? 'attack' : 'normal'} label={p.prediction_label} />
                        </td>
                        <td className="py-2 px-3 font-semibold">{(p.confidence * 100).toFixed(1)}%</td>
                        <td className="py-2 px-3 font-mono text-xs" style={{ color: 'var(--color-muted)' }}>
                          {p.window_start_idx}–{p.window_end_idx}
                        </td>
                        <td className="py-2 px-3 text-xs">{p.inference_time_ms?.toFixed(2) ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
