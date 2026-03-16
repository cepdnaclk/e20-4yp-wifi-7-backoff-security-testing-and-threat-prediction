export type StageState = 'active' | 'idle' | 'error'

export interface StageStatus {
  state: StageState
  counter: number
  label: string
  last_activity_ts: string | null
}

export interface PipelineStages {
  ns3: StageStatus
  exporter: StageStatus
  kafka: StageStatus
  windowizer: StageStatus
  gcn: StageStatus
  db: StageStatus
}

export interface PipelineStatusMessage {
  type: 'pipeline_status'
  ts: string
  stages: PipelineStages
  latest_experiment_id: string | null
}

export interface PipelineEvent {
  type: 'pipeline_event'
  ts: string
  stage: string
  level: 'info' | 'warning' | 'error'
  message: string
  experiment_id: string
  prediction: 0 | 1
  confidence: number
}

export interface ConnectionAck {
  type: 'connection_ack'
  ts: string
  server_version: string
  message: string
}

export type WsMessage = PipelineStatusMessage | PipelineEvent | ConnectionAck
