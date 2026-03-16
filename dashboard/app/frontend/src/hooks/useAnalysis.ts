import { useApi } from './useApi'
import type { AnalysisSummary, ConfidenceHistogram, AttackTypeGroup } from '../types/analysis'

export function useAnalysisSummary(modelVersion?: string) {
  const params = modelVersion ? `?model_version=${encodeURIComponent(modelVersion)}` : ''
  return useApi<AnalysisSummary>(`/api/analysis/summary${params}`, 10_000)
}

export function useConfidenceHistogram(bins = 10) {
  return useApi<ConfidenceHistogram>(`/api/analysis/confidence-histogram?bins=${bins}`, 15_000)
}

export function useAttackByType() {
  return useApi<{ groups: AttackTypeGroup[] }>('/api/analysis/attack-by-type', 10_000)
}
