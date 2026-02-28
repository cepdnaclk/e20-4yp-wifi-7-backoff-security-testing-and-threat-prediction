interface LiveIndicatorProps {
  active: boolean
  label?: string
  size?: number
}

export default function LiveIndicator({ active, label, size = 8 }: LiveIndicatorProps) {
  return (
    <div className="flex items-center gap-1.5">
      <div
        className={`live-dot ${active ? 'green' : 'grey'}`}
        style={{ width: size, height: size }}
      />
      {label && (
        <span
          className="text-xs font-medium"
          style={{ color: active ? 'var(--color-normal)' : 'var(--color-subtle)' }}
        >
          {label}
        </span>
      )}
    </div>
  )
}
