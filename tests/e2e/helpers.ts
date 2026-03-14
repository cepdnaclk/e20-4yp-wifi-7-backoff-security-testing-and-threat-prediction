/**
 * Shared helpers for NDT dashboard E2E tests.
 */
import { Page, expect } from '@playwright/test'

export const BASE = 'http://localhost:8888'

export type Scenario = 'normal' | 'positive' | 'negative'
export type GcnVersion = 'v1.0.0' | 'v2.0.0' | 'v2.1.0' | 'v3.0.0'

export interface RunConfig {
  scenario: Scenario
  seed: number
  simTime: number      // seconds (use 30 for quick tests)
  bias?: number
  numAp?: number
  numSta?: number
  segmentLength?: 32 | 64 | 128 | 256
  gcnVersion: GcnVersion
}

/** Navigate to Run Experiment section */
export async function goToRun(page: Page) {
  await page.goto(BASE)
  await page.getByRole('button', { name: 'Run Experiment' }).click()
  await expect(page.getByRole('heading', { name: 'Run Experiment' })).toBeVisible()
}

/** Navigate to Experiment View section */
export async function goToExperimentView(page: Page) {
  await page.goto(BASE)
  await page.getByRole('button', { name: 'Experiment View' }).click()
  await expect(page.getByRole('heading', { name: 'Experiment View' })).toBeVisible()
}

/** Navigate to Model Intelligence section */
export async function goToModelIntelligence(page: Page) {
  await page.goto(BASE)
  await page.getByRole('button', { name: 'Model Intelligence' }).click()
  await expect(page.getByRole('heading', { name: 'Model Intelligence' })).toBeVisible()
}

/**
 * Fill in the Run Experiment form and click Launch.
 * Returns the experiment ID that was used.
 */
export async function launchExperiment(page: Page, cfg: RunConfig): Promise<string> {
  await goToRun(page)

  // Wait for form to be visible (not during active run)
  await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

  // Select scenario
  const scenarioLabel = cfg.scenario === 'normal' ? 'Normal' : cfg.scenario === 'positive' ? 'Attack (+)' : 'Attack (−)'
  await page.getByRole('button', { name: new RegExp(scenarioLabel) }).click()

  // Set seed
  const seedInput = page.locator('input[type="number"]').filter({ hasText: '' }).nth(0)
  // Use label-aware approach
  await page.locator('label:has-text("SEED") + input, label:has-text("SEED") ~ input').first().fill(String(cfg.seed))
  // Use nth spinbutton approach based on snapshot: seed is first spinbutton
  const spinbuttons = page.getByRole('spinbutton')
  await spinbuttons.nth(0).fill(String(cfg.seed))
  await spinbuttons.nth(1).fill(String(cfg.simTime))

  if (cfg.bias != null && cfg.scenario !== 'normal') {
    await spinbuttons.nth(2).fill(String(cfg.bias))
  }
  if (cfg.numAp != null) {
    await spinbuttons.nth(3).fill(String(cfg.numAp))
    if (cfg.numSta != null) {
      await spinbuttons.nth(4).fill(String(cfg.numSta))
    }
  }

  // Select segment length
  if (cfg.segmentLength) {
    await page.getByRole('button', { name: `${cfg.segmentLength}w` }).click()
  }

  // Select GCN model
  const modelSelect = page.getByRole('combobox')
  await modelSelect.selectOption({ value: cfg.gcnVersion })

  // Read the auto-generated experiment ID from the placeholder
  const expIdInput = page.getByPlaceholder(/^\d{4}-\d{2}-\d{2}/)
  const expId = await expIdInput.getAttribute('placeholder') ?? `auto-${cfg.scenario}-${cfg.seed}`

  // Click Launch
  await page.getByRole('button', { name: '▶ Launch' }).click()

  return expId
}

/**
 * Wait for an experiment to complete (success or failed).
 * First waits for the run to become active (so we don't read stale history),
 * then polls until it completes.
 * Returns 'success' | 'failed' | 'timeout'.
 */
export async function waitForRunCompletion(page: Page, timeoutMs = 240_000): Promise<'success' | 'failed' | 'timeout'> {
  const deadline = Date.now() + timeoutMs

  // Phase 1: Wait for the experiment to become active (max 30s)
  let experimentId: string | null = null
  const activateDeadline = Date.now() + 30_000
  while (Date.now() < activateDeadline) {
    await page.waitForTimeout(2000)
    const resp = await page.request.get(`${BASE}/api/run/status`)
    const status = await resp.json()
    if (status.active && status.experiment_id) {
      experimentId = status.experiment_id
      break
    }
  }

  if (!experimentId) {
    // Never became active — check if a very fast run already completed
    const histResp = await page.request.get(`${BASE}/api/run/history`)
    const hist = await histResp.json()
    const latest = hist.history?.[0]
    if (latest && (Date.now() - new Date(latest.completed_at).getTime()) < 60_000) {
      return latest.outcome === 'success' ? 'success' : 'failed'
    }
    return 'failed'
  }

  // Phase 2: Wait for the active experiment to complete
  while (Date.now() < deadline) {
    await page.waitForTimeout(3000)
    const resp = await page.request.get(`${BASE}/api/run/status`)
    const status = await resp.json()
    if (!status.active) {
      // Find this specific experiment in history
      const histResp = await page.request.get(`${BASE}/api/run/history`)
      const hist = await histResp.json()
      const entry = hist.history?.find((h: any) => h.experiment_id === experimentId)
      if (entry) return entry.outcome === 'success' ? 'success' : 'failed'
      // Fall back to latest if entry not found yet
      const latest = hist.history?.[0]
      return latest?.outcome === 'success' ? 'success' : 'failed'
    }
  }
  return 'timeout'
}

/** Wait for the pipeline stages panel to reach 'gcn' stage or beyond */
export async function waitForGcnStage(page: Page) {
  await expect(page.getByText('GCN Detector')).toBeVisible({ timeout: 180_000 })
}

/** Assert that experiment results appear in Experiment View */
export async function assertExperimentInView(page: Page, expIdFragment: string) {
  await goToExperimentView(page)
  await expect(page.getByRole('button', { name: new RegExp(expIdFragment, 'i') })).toBeVisible({ timeout: 30_000 })
}
