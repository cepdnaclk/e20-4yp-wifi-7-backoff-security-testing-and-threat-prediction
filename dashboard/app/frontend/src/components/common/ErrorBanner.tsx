import { AlertTriangle } from 'lucide-react'

interface ErrorBannerProps {
  message: string
}

export default function ErrorBanner({ message }: ErrorBannerProps) {
  return (
    <div
      className="flex items-center gap-2 px-4 py-3 rounded-neu-sm text-sm"
      style={{
        background: 'var(--color-attack-bg)',
        color: 'var(--color-attack)',
        boxShadow: 'var(--shadow-raised-sm)',
      }}
    >
      <AlertTriangle size={16} />
      <span>{message}</span>
    </div>
  )
}
