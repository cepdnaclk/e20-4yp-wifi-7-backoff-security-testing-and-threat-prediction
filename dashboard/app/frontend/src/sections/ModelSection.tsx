import SectionTitle from '../components/common/SectionTitle'
import KpiCard from '../components/common/KpiCard'
import Badge from '../components/common/Badge'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorBanner from '../components/common/ErrorBanner'
import PerformanceBarChart from '../components/charts/PerformanceBarChart'
import ConfusionMatrix from '../components/model/ConfusionMatrix'
import { useActiveModel, useModels, useInferenceStats } from '../hooks/useModels'
import { useAnalysisSummary } from '../hooks/useAnalysis'
import { Brain, Cpu, Layers } from 'lucide-react'

export default function ModelSection() {
  const { data: active, loading: aLoading, error: aError } = useActiveModel()
  const { data: modelList } = useModels()
  const { data: infStats } = useInferenceStats()
  const { data: analysis } = useAnalysisSummary()

  const tr = active?.test_results
  const arch = active?.architecture

  const perfData = tr ? [
    { name: 'F1 Score',   value: tr.f1_score,   color: 'var(--color-brand)' },
    { name: 'Accuracy',   value: tr.accuracy,    color: 'var(--color-normal)' },
    { name: 'Precision',  value: tr.precision,   color: 'var(--color-brand)' },
    { name: 'Recall',     value: tr.recall,      color: 'var(--color-normal)' },
    { name: 'AUC-ROC',    value: tr.auc_roc,     color: '#a78bfa' },
  ] : []

  const cm = tr?.confusion_matrix
  const tn = cm?.[0]?.[0] ?? 0
  const fp = cm?.[0]?.[1] ?? 0
  const fn = cm?.[1]?.[0] ?? 0
  const tp = cm?.[1]?.[1] ?? 0

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle title="Model Intelligence" subtitle="GCN model performance, architecture, and inference stats" />

      {aLoading && <LoadingSpinner message="Loading model data…" />}
      {aError && <ErrorBanner message={aError} />}

      {active && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              label="Active Version"
              value={<span className="text-gradient">{active.version}</span>}
              icon={<Brain size={18} />}
              accent="var(--color-brand)"
            />
            <KpiCard
              label="F1 Score"
              value={tr ? `${(tr.f1_score * 100).toFixed(1)}%` : '—'}
              accent={tr && tr.f1_score > 0.9 ? 'var(--color-normal)' : 'var(--color-warning)'}
            />
            <KpiCard
              label="Avg Inference"
              value={infStats?.avg_ms != null ? `${infStats.avg_ms.toFixed(1)}ms` : '—'}
              icon={<Cpu size={18} />}
              accent="var(--color-brand)"
            />
            <KpiCard
              label="Total Predictions"
              value={infStats?.count?.toLocaleString() ?? '—'}
              icon={<Layers size={18} />}
              accent="var(--color-normal)"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Performance chart */}
            <div className="neu-card">
              <div className="section-title text-base mb-3">Performance Metrics</div>
              {perfData.length > 0 ? (
                <PerformanceBarChart data={perfData} height={200} />
              ) : (
                <div className="text-sm py-8 text-center" style={{ color: 'var(--color-muted)' }}>
                  No test results available
                </div>
              )}
            </div>

            {/* Confusion matrix */}
            <div className="neu-card">
              <div className="section-title text-base mb-3">Confusion Matrix</div>
              {(tp + tn + fp + fn > 0) ? (
                <ConfusionMatrix tp={tp} tn={tn} fp={fp} fn={fn} />
              ) : analysis ? (
                <ConfusionMatrix tp={analysis.tp} tn={analysis.tn} fp={analysis.fp} fn={analysis.fn} />
              ) : (
                <div className="text-sm py-8 text-center" style={{ color: 'var(--color-muted)' }}>
                  No prediction data
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Architecture */}
            {arch && (
              <div className="neu-card">
                <div className="section-title text-base mb-3">Architecture</div>
                <div className="flex flex-col gap-2">
                  {Object.entries(arch).map(([k, v]) => (
                    <div key={k} className="neu-inset flex justify-between items-center">
                      <span className="text-sm capitalize" style={{ color: 'var(--color-muted)' }}>
                        {k.replace(/_/g, ' ')}
                      </span>
                      <span className="text-sm font-semibold">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inference latency */}
            {infStats && (
              <div className="neu-card">
                <div className="section-title text-base mb-3">Inference Latency</div>
                <div className="flex flex-col gap-2">
                  {[
                    { label: 'Min', value: infStats.min_ms != null ? `${infStats.min_ms.toFixed(2)}ms` : '—' },
                    { label: 'P50 Median', value: infStats.p50_ms != null ? `${infStats.p50_ms.toFixed(2)}ms` : '—' },
                    { label: 'P95', value: infStats.p95_ms != null ? `${infStats.p95_ms.toFixed(2)}ms` : '—' },
                    { label: 'Max', value: infStats.max_ms != null ? `${infStats.max_ms.toFixed(2)}ms` : '—' },
                    { label: 'Avg', value: infStats.avg_ms != null ? `${infStats.avg_ms.toFixed(2)}ms` : '—' },
                  ].map(({ label, value }) => (
                    <div key={label} className="neu-inset flex justify-between items-center">
                      <span className="text-sm" style={{ color: 'var(--color-muted)' }}>{label}</span>
                      <span className="text-sm font-semibold">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Version list */}
          {modelList && modelList.models.length > 0 && (
            <div className="neu-card">
              <div className="section-title text-base mb-3">Model Registry</div>
              <div className="flex flex-col gap-2">
                {modelList.models.map((m) => (
                  <div
                    key={m.version}
                    className="neu-inset flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{m.version}</span>
                      {m.is_current && <Badge variant="brand" label="active" />}
                    </div>
                    {m.test_results && (
                      <span className="text-sm" style={{ color: 'var(--color-muted)' }}>
                        F1: {(m.test_results.f1_score * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
