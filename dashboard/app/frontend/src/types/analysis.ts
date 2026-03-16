export interface AnalysisSummary {
  total_segments: number
  total_attacks: number
  total_normals: number
  tp: number
  tn: number
  fp: number
  fn: number
  precision: number | null
  recall: number | null
  fpr: number | null
  fnr: number | null
  f1: number | null
  accuracy: number | null
}

export interface HistogramBin {
  bin_start: number
  bin_end: number
  count: number
}

export interface ConfidenceHistogram {
  normal: HistogramBin[]
  attack: HistogramBin[]
}

export interface AttackTypeGroup {
  exp_type: string
  total_segments: number
  attack_segments: number
  detection_rate: number
}
