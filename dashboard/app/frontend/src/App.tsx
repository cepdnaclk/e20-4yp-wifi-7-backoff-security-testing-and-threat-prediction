import { useState } from 'react'
import { AppProvider } from './context/AppContext'
import TopBar from './components/layout/TopBar'
import Sidebar from './components/layout/Sidebar'
import PipelineSection from './sections/PipelineSection'
import ExperimentSection from './sections/ExperimentSection'
import ModelSection from './sections/ModelSection'
import RunHistorySection from './sections/RunHistorySection'
import AttackSection from './sections/AttackSection'
import NetworkHealthSection from './sections/NetworkHealthSection'

export type SectionId =
  | 'pipeline'
  | 'experiment'
  | 'model'
  | 'history'
  | 'attack'
  | 'network'

const SECTIONS: Record<SectionId, React.FC> = {
  pipeline: PipelineSection,
  experiment: ExperimentSection,
  model: ModelSection,
  history: RunHistorySection,
  attack: AttackSection,
  network: NetworkHealthSection,
}

export default function App() {
  const [activeSection, setActiveSection] = useState<SectionId>('pipeline')
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
