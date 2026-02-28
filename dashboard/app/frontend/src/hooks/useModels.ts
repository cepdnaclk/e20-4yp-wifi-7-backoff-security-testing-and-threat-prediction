import { useApi } from './useApi'
import type { ModelListResponse, ActiveModelDetail, InferenceStats } from '../types/models'

export function useModels() {
  return useApi<ModelListResponse>('/api/models', 30_000)
}

export function useActiveModel() {
  return useApi<ActiveModelDetail>('/api/models/active', 30_000)
}

export function useInferenceStats() {
  return useApi<InferenceStats>('/api/models/inference-stats', 10_000)
}
