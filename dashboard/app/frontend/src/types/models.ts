export interface ModelArchitecture {
  hidden_channels: number
  num_layers: number
  window_size: number
  num_features: number
  dropout: number
}

export interface ModelTestResults {
  accuracy: number
  f1_score: number
  precision: number
  recall: number
  auc_roc: number
  confusion_matrix: [[number, number], [number, number]]
}

export interface ModelInfo {
  version: string
  path: string
  is_current: boolean
  architecture: ModelArchitecture | null
  test_results: ModelTestResults | null
  created_at: string | null
}

export interface InferenceStats {
  count: number
  min_ms: number | null
  p50_ms: number | null
  p95_ms: number | null
  max_ms: number | null
  avg_ms: number | null
}

export interface ActiveModelDetail {
  version: string
  path: string
  architecture: ModelArchitecture | null
  test_results: ModelTestResults | null
}

export interface ModelListResponse {
  models: ModelInfo[]
  active_version: string | null
}
