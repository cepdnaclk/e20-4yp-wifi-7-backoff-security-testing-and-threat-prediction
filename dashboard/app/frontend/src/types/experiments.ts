export interface Experiment {
  experiment_id: string
  inferred_type: 'normal' | 'attack' | 'unknown'
  first_ts: string | null
  last_ts: string | null
  metric_count: number
  segment_count: number
  attack_segment_count: number
  normal_segment_count: number
  attack_rate: number
  avg_confidence: number | null
  model_version: string | null
  pass_fail: 'pass' | 'fail' | 'unknown'
}

export interface ExperimentListResponse {
  experiments: Experiment[]
  total: number
  limit: number
  offset: number
}

export interface ExperimentSummary {
  experiment_id: string
  segment_count: number
  attack_segment_count: number
  normal_segment_count: number
  attack_rate: number
  avg_confidence: number | null
  min_confidence: number | null
  max_confidence: number | null
  avg_inference_time_ms: number | null
  model_version: string | null
  ts_start: string | null
  ts_end: string | null
}

export interface Prediction {
  id: number
  segment_id: string
  segment_number: number
  prediction: 0 | 1
  prediction_label: 'normal' | 'attack'
  confidence: number
  p_normal: number | null
  p_attack: number | null
  window_start_idx: number
  window_end_idx: number
  ts_start: string | null
  ts_end: string | null
  inference_time_ms: number | null
}

export interface MetricPoint {
  ts: string
  value: number
}

export interface MetricSeries {
  experiment_id: string
  metric_name: string
  entity_id: string
  unit: string
  points: MetricPoint[]
}

export interface MetricStat {
  metric_name: string
  unit: string
  avg: number
  min: number
  max: number
  std: number
  trend: 'up' | 'down' | 'flat'
}
