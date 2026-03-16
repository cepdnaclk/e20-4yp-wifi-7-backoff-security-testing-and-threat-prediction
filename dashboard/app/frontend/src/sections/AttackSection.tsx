import SectionTitle from '../components/common/SectionTitle'
import KpiCard from '../components/common/KpiCard'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorBanner from '../components/common/ErrorBanner'
import ConfidenceHistogram from '../components/charts/ConfidenceHistogram'
import AttackTypeDonut from '../components/charts/AttackTypeDonut'
import { useAnalysisSummary, useConfidenceHistogram, useAttackByType } from '../hooks/useAnalysis'
import { ShieldAlert, Target, CheckCircle, AlertTriangle } from 'lucide-react'

function pct(n: number | null | undefined, d: number | null | undefined): string {
  if (n == null || d == null || d === 0) return '—'
  return `${((n / d) * 100).toFixed(1)}%`
}

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v == null) return '—'
  return `${(v * 100).toFixed(decimals)}%`
}

export default function AttackSection() {
  const { data: summary, loading, error } = useAnalysisSummary()
  const { data: histogram } = useConfidenceHistogram(10)
  const { data: byType } = useAttackByType()

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle
        title="Attack Analysis"
        subtitle="Cross-experiment detection performance and confidence distribution"
      />

      {loading && <LoadingSpinner message="Loading analysis…" />}
      {error && <ErrorBanner message={error} />}

      {summary && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              label="Detection Rate (Recall)"
              value={fmt(summary.recall)}
              icon={<ShieldAlert size={18} />}
              accent="var(--color-attack)"
            />
            <KpiCard
              label="Precision"
              value={fmt(summary.precision)}
              icon={<Target size={18} />}
              accent="var(--color-brand)"
            />
            <KpiCard
              label="F1 Score"
              value={fmt(summary.f1)}
              icon={<CheckCircle size={18} />}
              accent={summary.f1 != null && summary.f1 > 0.9 ? 'var(--color-normal)' : 'var(--color-warning)'}
            />
            <KpiCard
              label="False Positive Rate"
              value={fmt(summary.fpr)}
              icon={<AlertTriangle size={18} />}
              accent={summary.fpr != null && summary.fpr < 0.05 ? 'var(--color-normal)' : 'var(--color-attack)'}
            />
          </div>

          {/* TP/TN/FP/FN breakdown */}
          <div className="neu-card">
            <div className="section-title text-base mb-4">Detection Breakdown</div>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {[
                { label: 'True Positives', value: summary.tp, color: 'var(--color-normal)', bg: 'var(--color-normal-bg)', desc: 'Correctly detected attacks' },
                { label: 'True Negatives', value: summary.tn, color: 'var(--color-normal)', bg: 'var(--color-normal-bg)', desc: 'Correctly identified normals' },
                { label: 'False Positives', value: summary.fp, color: 'var(--color-attack)', bg: 'var(--color-attack-bg)', desc: 'Normal flagged as attack' },
                { label: 'False Negatives', value: summary.fn, color: 'var(--color-warning)', bg: 'var(--color-warning-bg)', desc: 'Attack missed' },
              ].map(({ label, value, color, bg, desc }) => (
                <div
                  key={label}
                  className="flex flex-col gap-1 p-3 rounded-neu-sm"
                  style={{ background: bg, boxShadow: 'var(--shadow-raised-sm)' }}
                >
                  <div className="text-xs font-semibold uppercase tracking-wider" style={{ color }}>
                    {label}
                  </div>
                  <div className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
                    {value}
                  </div>
                  <div className="text-xs" style={{ color: 'var(--color-muted)' }}>{desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Confidence histogram */}
            {histogram && (
              <div className="neu-card">
                <div className="section-title text-base mb-3">Confidence Distribution</div>
                <ConfidenceHistogram data={histogram} height={220} />
              </div>
            )}

            {/* Attack by type donut */}
            {byType && byType.groups.length > 0 && (
              <div className="neu-card">
                <div className="section-title text-base mb-3">Segments by Experiment Type</div>
                <AttackTypeDonut data={byType.groups} height={220} />
                <div className="flex flex-col gap-1.5 mt-3">
                  {byType.groups.map((g) => (
                    <div key={g.exp_type} className="neu-inset flex justify-between items-center text-sm">
                      <span style={{ color: 'var(--color-muted)' }}>{g.exp_type}</span>
                      <span className="font-semibold">
                        {pct(g.attack_segments, g.total_segments)} detection
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Accuracy summary */}
          <div className="neu-card">
            <div className="section-title text-base mb-3">Accuracy Summary</div>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {[
                { label: 'Total Segments', value: summary.total_segments.toLocaleString(), accent: 'var(--color-brand)' },
                { label: 'Overall Accuracy', value: fmt(summary.accuracy), accent: 'var(--color-normal)' },
                { label: 'False Neg. Rate', value: fmt(summary.fnr), accent: 'var(--color-warning)' },
                { label: 'Attack Segments', value: summary.total_attacks.toLocaleString(), accent: 'var(--color-attack)' },
              ].map(({ label, value, accent }) => (
                <div
                  key={label}
                  className="neu-inset flex flex-col gap-1"
                >
                  <span className="text-xs" style={{ color: 'var(--color-muted)' }}>{label}</span>
                  <span className="text-xl font-bold" style={{ color: accent }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
