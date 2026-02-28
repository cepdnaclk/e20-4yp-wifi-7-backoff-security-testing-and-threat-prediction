type BadgeVariant = 'normal' | 'attack' | 'warning' | 'brand' | 'neutral'

interface BadgeProps {
  label: string
  variant?: BadgeVariant
  dot?: boolean
}

const VARIANT_CLASS: Record<BadgeVariant, string> = {
  normal:  'pill-normal',
  attack:  'pill-attack',
  warning: 'pill-warning',
  brand:   'pill-brand',
  neutral: 'pill-neutral',
}

export default function Badge({ label, variant = 'neutral', dot = false }: BadgeProps) {
  return (
    <span className={`neu-pill ${VARIANT_CLASS[variant]}`}>
      {dot && <span className={`live-dot ${variant === 'normal' ? 'green' : variant === 'attack' ? 'red' : 'blue'}`} style={{ width: 6, height: 6 }} />}
      {label}
    </span>
  )
}
