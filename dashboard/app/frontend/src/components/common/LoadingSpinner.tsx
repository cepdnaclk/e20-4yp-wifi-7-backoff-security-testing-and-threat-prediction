interface LoadingSpinnerProps {
  size?: number
  message?: string
}

export default function LoadingSpinner({ size = 32, message }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        style={{ animation: 'spin 1s linear infinite' }}
      >
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <circle
          cx="16" cy="16" r="13"
          stroke="var(--color-brand)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="50 32"
        />
      </svg>
      {message && (
        <span className="text-sm" style={{ color: 'var(--color-muted)' }}>{message}</span>
      )}
    </div>
  )
}
