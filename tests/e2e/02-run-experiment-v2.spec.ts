/**
 * E2E: Run Experiment — GCN v2.0.0
 *
 * Tests three scenarios (normal, positive attack, negative attack) with GCN v2.0.0.
 * Each uses sim_time=30s for fast turnaround.
 * Verifies: launch succeeds, pipeline progresses, results appear in Experiment View.
 */
import { test, expect } from '@playwright/test'
import { BASE, goToRun, goToExperimentView, launchExperiment, waitForRunCompletion } from './helpers'

const GCN_V2 = 'v2.0.0' as const
const SIM_TIME = 30  // seconds — fast enough for CI

test.describe('GCN v2.0.0 — Run Experiment', () => {

  test.beforeEach(async ({ page }) => {
    // Ensure no run is active before each test
    const resp = await page.request.get(`${BASE}/api/run/status`)
    const status = await resp.json()
    if (status.active) {
      await page.request.post(`${BASE}/api/run/cancel`)
      await page.waitForTimeout(3000)
    }
  })

  test('form allows selecting v2.0.0 from model dropdown', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

    const modelSelect = page.getByRole('combobox')
    await expect(modelSelect).toBeVisible()

    // All versions should be present
    await expect(modelSelect.getByText('v2.0.0')).toBeAttached()
    await expect(modelSelect.getByText('v3.0.0')).toBeAttached()

    // Select v2.0.0
    await modelSelect.selectOption({ value: 'v2.0.0' })
    const selected = await modelSelect.evaluate((el: HTMLSelectElement) =>
      el.options[el.selectedIndex].value
    )
    expect(selected).toBe('v2.0.0')

    // Warning about deploy should appear if v2 ≠ active (which is v3)
    await expect(page.getByText(/Will deploy v2\.0\.0/i)).toBeVisible({ timeout: 5_000 })
  })

  test('normal scenario with v2.0.0 — full pipeline run', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

    // Configure: normal, seed=10, 30s, v2.0.0
    await page.getByRole('button', { name: /Normal/ }).click()
    await page.getByRole('spinbutton').nth(0).fill('10')
    await page.getByRole('spinbutton').nth(1).fill(String(SIM_TIME))
    await page.getByRole('combobox').selectOption({ value: 'v2.0.0' })

    await page.getByRole('button', { name: '▶ Launch' }).click()

    // Form hides and progress panel appears
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('NS-3 Simulation')).toBeVisible()

    // Wait for completion (allow extra time since v2 deploy adds ~5s)
    const outcome = await waitForRunCompletion(page, 300_000)
    expect(outcome).toBe('success')

    // Post-run card appears
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByRole('button', { name: /View Results/ })).toBeVisible()
  })

  test('positive attack scenario with v2.0.0 — detects attack', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: /Attack \(\+\)/ }).click()
    await page.getByRole('spinbutton').nth(0).fill('44')
    await page.getByRole('spinbutton').nth(1).fill(String(SIM_TIME))
    await page.getByRole('spinbutton').nth(2).fill('5000')  // bias
    await page.getByRole('combobox').selectOption({ value: 'v2.0.0' })

    await page.getByRole('button', { name: '▶ Launch' }).click()
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })

    const outcome = await waitForRunCompletion(page, 300_000)
    expect(outcome).toBe('success')
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })

    // Navigate to Experiment View and verify attack predictions appear
    await page.getByRole('button', { name: /View Results/ }).click()
    await page.waitForTimeout(2000)
    await expect(page.getByText(/Attack/i)).toBeVisible({ timeout: 20_000 })
  })

  test('negative attack scenario with v2.0.0', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: /Attack \(−\)/ }).click()
    await page.getByRole('spinbutton').nth(0).fill('45')
    await page.getByRole('spinbutton').nth(1).fill(String(SIM_TIME))
    await page.getByRole('spinbutton').nth(2).fill('5000')
    await page.getByRole('combobox').selectOption({ value: 'v2.0.0' })

    await page.getByRole('button', { name: '▶ Launch' }).click()
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })

    const outcome = await waitForRunCompletion(page, 300_000)
    expect(outcome).toBe('success')
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })
  })

  test.afterAll(async ({ request }) => {
    // Restore active model to v3.0.0 after v2.0.0 tests
    await request.post(`${BASE}/api/models/v3.0.0/deploy`)
    // Give detector time to restart
    await new Promise(r => setTimeout(r, 6000))
  })
})
