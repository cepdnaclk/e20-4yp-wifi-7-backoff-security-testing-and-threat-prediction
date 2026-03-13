import { useState, useEffect } from 'react'
import { AppProvider } from './context/AppContext'
import TopBar from './components/layout/TopBar'
import Sidebar from './components/layout/Sidebar'
import PipelineSection from './sections/PipelineSection'
import RunSection from './sections/RunSection'
import ExperimentSection from './sections/ExperimentSection'
import ModelSection from './sections/ModelSection'
import RunHistorySection from './sections/RunHistorySection'
import AttackSection from './sections/AttackSection'
import NetworkHealthSection from './sections/NetworkHealthSection'

export type SectionId =
  | 'pipeline'
  | 'run'
  | 'experiment'
  | 'model'
  | 'history'
  | 'attack'
  | 'network'

const SECTIONS: Record<SectionId, React.FC> = {
  pipeline: PipelineSection,
  run: RunSection,
  experiment: ExperimentSection,
  model: ModelSection,
  history: RunHistorySection,
  attack: AttackSection,
  network: NetworkHealthSection,
}

export default function App() {
  const [activeSection, setActiveSection] = useState<SectionId>('pipeline')

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.section && detail.section in SECTIONS) {
        setActiveSection(detail.section as SectionId)
      }
    }
    window.addEventListener('navigate', handler)
    return () => window.removeEventListener('navigate', handler)
  }, [])

  const Section = SECTIONS[activeSection]

  return (
    <AppProvider>
      <div className="flex h-full overflow-hidden" style={{ background: 'var(--color-bg)' }}>
        <Sidebar active={activeSection} onSelect={setActiveSection} />
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-6">
            <Section />
          </main>
        </div>
      </div>
    </AppProvider>
  )
}
