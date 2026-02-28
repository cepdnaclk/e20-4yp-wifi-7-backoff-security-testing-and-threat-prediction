interface ConfusionMatrixProps {
  tp: number
  tn: number
  fp: number
  fn: number
}

export default function ConfusionMatrix({ tp, tn, fp, fn }: ConfusionMatrixProps) {
  const total = tp + tn + fp + fn || 1

  function Cell({ value, label, color }: { value: number; label: string; color: string }) {
    return (
      <div
        className="flex flex-col items-center justify-center rounded-neu-sm p-3"
        style={{
          background: color,
          boxShadow: 'var(--shadow-raised-sm)',
          minWidth: 80,
          minHeight: 70,
        }}
      >
        <div className="font-bold text-xl" style={{ color: 'var(--color-text)' }}>{value}</div>
        <div className="text-xs font-medium mt-0.5" style={{ color: 'var(--color-muted)' }}>{label}</div>
        <div className="text-xs" style={{ color: 'var(--color-subtle)' }}>
          {((value / total) * 100).toFixed(1)}%
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="grid grid-cols-2 gap-2 mb-1">
        <div className="text-center text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>Pred: Normal</div>
        <div className="text-center text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>Pred: Attack</div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Cell value={tn} label="TN" color="var(--color-normal-bg)" />
        <Cell value={fp} label="FP" color="var(--color-attack-bg)" />
        <Cell value={fn} label="FN" color="var(--color-warning-bg)" />
        <Cell value={tp} label="TP" color="var(--color-normal-bg)" />
      </div>
      <div className="grid grid-cols-2 gap-2 mt-1">
        <div className="text-center text-xs" style={{ color: 'var(--color-muted)' }}>Actual: Normal</div>
        <div className="text-center text-xs" style={{ color: 'var(--color-muted)' }}>Actual: Attack</div>
      </div>
    </div>
  )
}
