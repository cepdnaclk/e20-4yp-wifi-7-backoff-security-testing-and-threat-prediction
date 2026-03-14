import { useState } from 'react'
import SectionTitle from '../components/common/SectionTitle'
import KpiCard from '../components/common/KpiCard'
import Badge from '../components/common/Badge'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorBanner from '../components/common/ErrorBanner'
import PerformanceBarChart from '../components/charts/PerformanceBarChart'
import ConfusionMatrix from '../components/model/ConfusionMatrix'
import { useActiveModel, useModels, useInferenceStats, useModelDetail, deployModel } from '../hooks/useModels'
import { useAnalysisSummary } from '../hooks/useAnalysis'
import { Brain, Cpu, Layers, GitCompare } from 'lucide-react'

function MetricRow({ label, a, b }: { label: string; a?: number | null; b?: number | null }) {
  const fmt = (v?: number | null) => v != null ? `${(v * 100).toFixed(2)}%` : '—'
  const diff = a != null && b != null ? ((b - a) * 100) : null
  return (
    <div className="neu-inset flex items-center justify-between py-1.5 px-3 gap-4">
      <span className="text-xs" style={{ color: 'var(--color-muted)' }}>{label}</span>
      <span className="text-sm font-semibold w-20 text-right">{fmt(a)}</span>
      <span className="text-sm font-semibold w-20 text-right">{fmt(b)}</span>
      {diff != null && (
        <span className="text-xs w-16 text-right" style={{ color: diff > 0 ? 'var(--color-normal)' : diff < 0 ? 'var(--color-attack)' : 'var(--color-muted)' }}>
          {diff > 0 ? '+' : ''}{diff.toFixed(2)}pp
        </span>
      )}
    </div>
  )
}

export default function ModelSection() {
  const { data: active, loading: aLoading, error: aError } = useActiveModel()
  const { data: modelList, refetch: refetchList } = useModels() as any
  const { data: infStats } = useInferenceStats()
  const { data: analysis } = useAnalysisSummary()

  // Which version is selected for the main view
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null)
  // Compare mode
  const [compareMode, setCompareMode] = useState(false)
  const [compareVersion, setCompareVersion] = useState<string | null>(null)
  // Deploy state
  const [deploying, setDeploying] = useState<string | null>(null)
  const [deployMsg, setDeployMsg] = useState<string | null>(null)

  const versions = modelList?.models ?? []
  const activeVersion = modelList?.active_version ?? active?.version ?? ''

  // Resolve which version to show in the main panel
  const viewVersion = selectedVersion ?? activeVersion
  const { data: viewDetail, loading: viewLoading } = useModelDetail(viewVersion !== activeVersion ? viewVersion : null)
  const displayModel = viewVersion === activeVersion ? active : viewDetail

  // Compare model detail
  const { data: compareDetail } = useModelDetail(compareMode ? compareVersion : null)

  const tr = displayModel?.test_results
  const arch = displayModel?.architecture
  const cm = tr?.confusion_matrix
  const tn = cm?.[0]?.[0] ?? 0; const fp = cm?.[0]?.[1] ?? 0
  const fn = cm?.[1]?.[0] ?? 0; const tp = cm?.[1]?.[1] ?? 0

  const perfData = tr ? [
    { name: 'F1',        value: tr.f1,        color: 'var(--color-brand)' },
    { name: 'Accuracy',  value: tr.accuracy,  color: 'var(--color-normal)' },
    { name: 'Precision', value: tr.precision, color: 'var(--color-brand)' },
    { name: 'Recall',    value: tr.recall,    color: 'var(--color-normal)' },
    { name: 'AUC-ROC',  value: tr.auc,       color: '#a78bfa' },
  ] : []

  const handleDeploy = async (version: string) => {
    setDeploying(version)
    setDeployMsg(null)
    try {
      const res = await deployModel(version)
      setDeployMsg(res.message)
      refetchList?.()
    } catch (e) {
      setDeployMsg(`Error: ${e}`)
    } finally {
      setDeploying(null)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle title="Model Intelligence" subtitle="GCN model performance, architecture, and inference stats" />

      {aLoading && <LoadingSpinner message="Loading model data…" />}
      {aError && <ErrorBanner message={aError} />}

      {/* Model registry — clickable version list */}
      {versions.length > 0 && (
        <div className="neu-card">
          <div className="flex items-center justify-between mb-3">
            <div className="section-title text-sm">Model Registry</div>
            <button
              className={`neu-btn text-xs py-1 px-3 flex items-center gap-1.5 ${compareMode ? 'neu-btn-primary' : ''}`}
              onClick={() => { setCompareMode(m => !m); setCompareVersion(null) }}
            >
              <GitCompare size={13} />
              {compareMode ? 'Compare ON' : 'Compare'}
            </button>
          </div>

          <div className="flex flex-col gap-2">
            {versions.map((m: any) => {
              const isSelected = viewVersion === m.version
              const isCompare = compareVersion === m.version
              return (
                <div
                  key={m.version}
                  className="neu-inset flex items-center gap-3 py-2 px-3 cursor-pointer"
                  style={{ borderLeft: isSelected ? '2px solid var(--color-brand)' : isCompare ? '2px solid #06b6d4' : '2px solid transparent' }}
                  onClick={() => {
                    if (compareMode && viewVersion !== m.version) {
                      setCompareVersion(v => v === m.version ? null : m.version)
                    } else {
                      setSelectedVersion(m.version)
                    }
                  }}
                >
                  <div className="flex items-center gap-2 flex-1">
                    <span className="font-semibold text-sm">{m.version}</span>
                    {m.is_active && <Badge variant="brand" label="active" />}
                    {isSelected && !m.is_active && <Badge variant="neutral" label="viewing" />}
                    {isCompare && <Badge variant="neutral" label="compare" />}
                  </div>
                  {m.test_results && (
                    <span className="text-xs font-semibold" style={{ color: 'var(--color-normal)' }}>
                      F1: {(m.test_results.f1 * 100).toFixed(1)}%
                    </span>
                  )}
                  {!m.is_active && (
                    <button
                      className="neu-btn text-xs py-0.5 px-2 ml-2"
                      disabled={deploying === m.version}
                      onClick={(e) => { e.stopPropagation(); handleDeploy(m.version) }}
                    >
                      {deploying === m.version ? 'Deploying…' : 'Deploy'}
                    </button>
                  )}
                </div>
              )
            })}
          </div>

          {deployMsg && (
            <div className="mt-3 text-xs p-2 neu-inset" style={{ color: deployMsg.startsWith('Error') ? 'var(--color-attack)' : 'var(--color-normal)' }}>
              {deployMsg}
            </div>
          )}
        </div>
      )}

      {/* Compare panel */}
      {compareMode && compareVersion && compareDetail && displayModel && (
        <div className="neu-card">
          <div className="section-title text-base mb-4 flex items-center gap-2">
            <GitCompare size={16} />
            Comparing {viewVersion} vs {compareVersion}
          </div>
          <div className="flex gap-3 mb-3 text-xs">
            <span style={{ color: 'var(--color-brand)' }}>■ {viewVersion}</span>
            <span style={{ color: '#06b6d4' }}>■ {compareVersion}</span>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between py-1 px-3 text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>
              <span>METRIC</span>
              <span className="w-20 text-right">{viewVersion}</span>
              <span className="w-20 text-right">{compareVersion}</span>
              <span className="w-16 text-right">DIFF</span>
            </div>
            <MetricRow label="F1 Score"   a={displayModel.test_results?.f1}        b={compareDetail.test_results?.f1} />
            <MetricRow label="Accuracy"   a={displayModel.test_results?.accuracy}   b={compareDetail.test_results?.accuracy} />
            <MetricRow label="Precision"  a={displayModel.test_results?.precision}  b={compareDetail.test_results?.precision} />
            <MetricRow label="Recall"     a={displayModel.test_results?.recall}     b={compareDetail.test_results?.recall} />
            <MetricRow label="ROC-AUC"    a={displayModel.test_results?.auc}        b={compareDetail.test_results?.auc} />
          </div>
        </div>
      )}

      {/* Main detail panel */}
      {displayModel && !viewLoading && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              label="Viewing"
              value={<span className="text-gradient">{viewVersion}</span>}
              icon={<Brain size={18} />}
              accent={viewVersion === activeVersion ? 'var(--color-brand)' : '#06b6d4'}
            />
            <KpiCard
              label="F1 Score"
              value={tr ? `${(tr.f1 * 100).toFixed(1)}%` : '—'}
              accent={tr && tr.f1 > 0.9 ? 'var(--color-normal)' : 'var(--color-warning)'}
            />
            <KpiCard
              label="Avg Inference"
              value={infStats?.avg_ms != null && viewVersion === activeVersion ? `${infStats.avg_ms.toFixed(1)}ms` : '—'}
              icon={<Cpu size={18} />}
              accent="var(--color-brand)"
            />
            <KpiCard
              label="Total Predictions"
              value={infStats?.count != null && viewVersion === activeVersion ? infStats.count.toLocaleString() : '—'}
              icon={<Layers size={18} />}
              accent="var(--color-normal)"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="neu-card">
              <div className="section-title text-base mb-3">Performance Metrics</div>
              {perfData.length > 0 ? (
                <PerformanceBarChart data={perfData} height={200} />
              ) : (
                <div className="text-sm py-8 text-center" style={{ color: 'var(--color-muted)' }}>No test results</div>
              )}
            </div>

            <div className="neu-card">
              <div className="section-title text-base mb-3">Confusion Matrix</div>
              {(tp + tn + fp + fn > 0) ? (
                <ConfusionMatrix tp={tp} tn={tn} fp={fp} fn={fn} />
              ) : analysis ? (
                <ConfusionMatrix tp={analysis.tp} tn={analysis.tn} fp={analysis.fp} fn={analysis.fn} />
              ) : (
                <div className="text-sm py-8 text-center" style={{ color: 'var(--color-muted)' }}>No prediction data</div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {arch && (
              <div className="neu-card">
                <div className="section-title text-base mb-3">Architecture</div>
                <div className="flex flex-col gap-2">
                  {Object.entries(arch).map(([k, v]) => (
                    <div key={k} className="neu-inset flex justify-between items-center">
                      <span className="text-sm capitalize" style={{ color: 'var(--color-muted)' }}>{k.replace(/_/g, ' ')}</span>
                      <span className="text-sm font-semibold">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {infStats && viewVersion === activeVersion && (
              <div className="neu-card">
                <div className="section-title text-base mb-3">Inference Latency</div>
                <div className="flex flex-col gap-2">
                  {[
                    { label: 'Min',       value: infStats.min_ms },
                    { label: 'P50 Median',value: infStats.p50_ms },
                    { label: 'P95',       value: infStats.p95_ms },
                    { label: 'Max',       value: infStats.max_ms },
                    { label: 'Avg',       value: infStats.avg_ms },
                  ].map(({ label, value }) => (
                    <div key={label} className="neu-inset flex justify-between items-center">
                      <span className="text-sm" style={{ color: 'var(--color-muted)' }}>{label}</span>
                      <span className="text-sm font-semibold">{value != null ? `${value.toFixed(2)}ms` : '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
      {viewLoading && <LoadingSpinner message={`Loading ${viewVersion}…`} />}
    </div>
  )
}
