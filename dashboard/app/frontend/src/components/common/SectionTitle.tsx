import type { ReactNode } from 'react'

interface SectionTitleProps {
  title: string
  subtitle?: string
  actions?: ReactNode
}

export default function SectionTitle({ title, subtitle, actions }: SectionTitleProps) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="section-title">{title}</h2>
        {subtitle && <p className="section-subtitle mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
