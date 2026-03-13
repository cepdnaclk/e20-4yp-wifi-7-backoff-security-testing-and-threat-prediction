import {
  Activity,
  Play,
  FlaskConical,
  Brain,
  History,
  ShieldAlert,
  Signal,
} from 'lucide-react'
import type { SectionId } from '../../App'

interface NavItem {
  id: SectionId
  label: string
  icon: React.ElementType
}

const NAV_ITEMS: NavItem[] = [
  { id: 'pipeline',   label: 'Pipeline Monitor',  icon: Activity },
  { id: 'run',        label: 'Run Experiment',     icon: Play },
  { id: 'experiment', label: 'Experiment View',    icon: FlaskConical },
  { id: 'model',      label: 'Model Intelligence', icon: Brain },
  { id: 'history',    label: 'Run History',      icon: History },
  { id: 'attack',     label: 'Attack Analysis',  icon: ShieldAlert },
  { id: 'network',    label: 'Network Health',   icon: Signal },
]

interface SidebarProps {
  active: SectionId
  onSelect: (id: SectionId) => void
}

export default function Sidebar({ active, onSelect }: SidebarProps) {
  return (
    <aside
      className="flex flex-col shrink-0 p-4 gap-1"
      style={{
        width: 220,
        background: 'var(--color-bg)',
        boxShadow: '2px 0 8px rgba(166,180,200,0.3)',
        zIndex: 9,
      }}
    >
      <div className="mb-4 mt-1 px-2">
        <div className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--color-subtle)' }}>
          Navigation
        </div>
      </div>

      {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          className={`nav-item w-full text-left ${active === id ? 'active' : ''}`}
          onClick={() => onSelect(id)}
        >
          <Icon size={16} />
          <span>{label}</span>
        </button>
      ))}
    </aside>
  )
}
