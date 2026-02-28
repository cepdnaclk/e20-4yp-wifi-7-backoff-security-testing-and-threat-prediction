import { useApi } from './useApi'
import type { ExperimentListResponse, ExperimentSummary, MetricSeries, MetricStat } from '../types/experiments'

export function useExperiments(limit = 50, prefix?: string) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (prefix) params.set('prefix', prefix)
  return useApi<ExperimentListResponse>(`/api/experiments?${params}`, 10_000)
}

export function useExperimentSummary(experimentId: string | null) {
  return useApi<ExperimentSummary>(
    experimentId ? `/api/experiments/${encodeURIComponent(experimentId)}/summary` : null,
    10_000,
  )
}

export function useExperimentPredictions(experimentId: string | null) {
  return useApi<{ predictions: import('../types/experiments').Prediction[] }>(
    experimentId ? `/api/experiments/${encodeURIComponent(experimentId)}/predictions` : null,
  )
}

export function useMetricSeries(experimentId: string | null, metric: string, entity?: string) {
  const params = new URLSearchParams({ metric })
  if (entity) params.set('entity_id', entity)
  return useApi<MetricSeries>(
    experimentId ? `/api/experiments/${encodeURIComponent(experimentId)}/metrics?${params}` : null,
  )
}

export function useMetricsSummary(experimentId: string | null) {
  return useApi<{ experiment_id: string; metrics: MetricStat[] }>(
    experimentId ? `/api/experiments/${encodeURIComponent(experimentId)}/metrics/summary` : null,
  )
}
