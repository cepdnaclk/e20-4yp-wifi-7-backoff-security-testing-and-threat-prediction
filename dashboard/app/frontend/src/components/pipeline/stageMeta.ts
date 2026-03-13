import type { PipelineStages } from '../../types/pipeline'

export interface StageMeta {
  key: keyof PipelineStages
  label: string
  icon: string
}

export const PIPELINE_STAGE_META: StageMeta[] = [
  { key: 'ns3', label: 'NS-3 Sim', icon: '📡' },
  { key: 'exporter', label: 'Exporter', icon: '📤' },
  { key: 'kafka', label: 'Redpanda', icon: '🔀' },
  { key: 'windowizer', label: 'Windowizer', icon: '🪟' },
  { key: 'gcn', label: 'GCN Detect', icon: '🧠' },
  { key: 'db', label: 'TimescaleDB', icon: '🗄️' },
]
