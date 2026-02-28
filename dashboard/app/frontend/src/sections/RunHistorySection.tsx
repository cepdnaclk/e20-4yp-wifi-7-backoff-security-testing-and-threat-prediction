import { useState } from 'react'
import SectionTitle from '../components/common/SectionTitle'
import Badge from '../components/common/Badge'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorBanner from '../components/common/ErrorBanner'
import AttackRateBarChart from '../components/charts/AttackRateBarChart'
import { useExperiments } from '../hooks/useExperiments'
import { CheckCircle, XCircle } from 'lucide-react'

type SortKey = 'last_ts' | 'attack_rate' | 'segment_count'

export default function RunHistorySection() {
  const { data, loading, error } = useExperiments(100)
  const [sortKey, setSortKey] = useState<SortKey>('last_ts')

  const experiments = [...(data?.experiments ?? [])].sort((a, b) => {
    if (sortKey === 'last_ts') return (b.last_ts || '').localeCompare(a.last_ts || '')
    if (sortKey === 'attack_rate') return b.attack_rate - a.attack_rate
    return b.segment_count - a.segment_count
  })

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle
        title="Run History"
        subtitle={`${data?.total ?? 0} experiments recorded`}
        actions={
          <div className="flex gap-2">
            {(['last_ts', 'attack_rate', 'segment_count'] as SortKey[]).map((k) => (
              <button
                key={k}
                className={`neu-btn text-xs py-1 ${sortKey === k ? 'neu-btn-primary' : ''}`}
                onClick={() => setSortKey(k)}
              >
                {k === 'last_ts' ? 'Date' : k === 'attack_rate' ? 'Attack Rate' : 'Segments'}
              </button>
            ))}
          </div>
        }
      />

      {loading && <LoadingSpinner message="Loading run history…" />}
      {error && <ErrorBanner message={error} />}

      {experiments.length > 0 && (
        <>
          {/* Bar chart overview */}
          <div className="neu-card">
            <div className="section-title text-base mb-3">Attack Rate by Run</div>
            <AttackRateBarChart experiments={experiments.slice(0, 20)} />
          </div>

          {/* Table */}
          <div className="neu-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    {['Experiment', 'Type', 'Segments', 'Attack Rate', 'Confidence', 'Pass/Fail', 'Model'].map((h) => (
                      <th
                        key={h}
                        className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider"
                        style={{ color: 'var(--color-muted)', borderBottom: '1px solid rgba(166,180,200,0.3)' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((e) => (
                    <tr
                      key={e.experiment_id}
                      style={{ borderBottom: '1px solid rgba(166,180,200,0.15)' }}
                    >
                      <td className="py-2 px-3 font-mono text-xs max-w-xs truncate" title={e.experiment_id}>
                        {e.experiment_id}
                      </td>
                      <td className="py-2 px-3">
                        <Badge
                          variant={e.inferred_type === 'normal' ? 'normal' : e.inferred_type === 'attack' ? 'attack' : 'neutral'}
                          label={e.inferred_type}
                        />
                      </td>
                      <td className="py-2 px-3">{e.segment_count}</td>
                      <td className="py-2 px-3 font-semibold" style={{ color: e.attack_rate > 0.5 ? 'var(--color-attack)' : 'var(--color-normal)' }}>
                        {(e.attack_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-3">
                        {e.avg_confidence != null ? `${(e.avg_confidence * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-2 px-3">
                        {e.pass_fail === 'pass' ? (
                          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-normal)' }}>
                            <CheckCircle size={13} /> pass
                          </span>
                        ) : e.pass_fail === 'fail' ? (
                          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-attack)' }}>
                            <XCircle size={13} /> fail
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-2 px-3 font-mono text-xs" style={{ color: 'var(--color-muted)' }}>
                        {e.model_version ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
