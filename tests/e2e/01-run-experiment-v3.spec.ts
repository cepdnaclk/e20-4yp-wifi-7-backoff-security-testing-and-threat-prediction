/**
 * E2E: Run Experiment — GCN v3.0.0
 *
 * Tests three scenarios (normal, positive attack, negative attack) with GCN v3.0.0.
 * Each uses sim_time=30s for fast turnaround.
 * Verifies: launch succeeds, pipeline progresses, results appear in Experiment View.
 */
import { test, expect } from '@playwright/test'
import { BASE, goToRun, goToExperimentView, goToModelIntelligence, launchExperiment, waitForRunCompletion } from './helpers'

const GCN_V3 = 'v3.0.0' as const
const SIM_TIME = 30  // seconds — fast enough for CI

test.describe('GCN v3.0.0 — Run Experiment', () => {

  test.beforeEach(async ({ page }) => {
    // Ensure no run is active before each test
    const resp = await page.request.get(`${BASE}/api/run/status`)
    const status = await resp.json()
    if (status.active) {
      await page.request.post(`${BASE}/api/run/cancel`)
      await page.waitForTimeout(3000)
    }
  })

  test('form renders with GCN v3.0.0 as default active model', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByRole('heading', { name: 'Run Experiment' })).toBeVisible()
    await expect(page.getByText('Simulation Configuration')).toBeVisible()

    // Scenario buttons present
    await expect(page.getByRole('button', { name: /Normal/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /Attack \(\+\)/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /Attack \(−\)/ })).toBeVisible()

    // GCN model dropdown shows v3.0.0 as active
    const modelSelect = page.getByRole('combobox')
    await expect(modelSelect).toBeVisible()
    const selectedOption = await modelSelect.evaluate((el: HTMLSelectElement) =>
      el.options[el.selectedIndex].text
    )
    expect(selectedOption).toMatch(/v3\.0\.0/)

    // Launch button present
    await expect(page.getByRole('button', { name: '▶ Launch' })).toBeVisible()
  })

  test('seed ? button shows explanation', async ({ page }) => {
    await goToRun(page)
    await page.getByRole('button', { name: '?' }).click()
    await expect(page.getByText(/random seed/i)).toBeVisible()
    await expect(page.getByText(/same seed.*identical/i)).toBeVisible()
  })

  test('normal scenario with v3.0.0 — full pipeline run', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

    // Configure: normal, seed=10, 30s, v3.0.0
    await page.getByRole('button', { name: /Normal/ }).click()
    await page.getByRole('spinbutton').nth(0).fill('10')
    await page.getByRole('spinbutton').nth(1).fill(String(SIM_TIME))
    const modelSelect = page.getByRole('combobox')
    await modelSelect.selectOption({ value: 'v3.0.0' })

    await page.getByRole('button', { name: '▶ Launch' }).click()

    // Form hides and progress panel appears
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('NS-3 Simulation')).toBeVisible()

    // Wait for completion
    const outcome = await waitForRunCompletion(page, 240_000)
    expect(outcome).toBe('success')

    // Post-run card appears
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByRole('button', { name: /View Results/ })).toBeVisible()
  })

  test('positive attack scenario with v3.0.0 — detects attack', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: /Attack \(\+\)/ }).click()
    await page.getByRole('spinbutton').nth(0).fill('42')
    await page.getByRole('spinbutton').nth(1).fill(String(SIM_TIME))
    await page.getByRole('spinbutton').nth(2).fill('5000')  // bias
    const modelSelect = page.getByRole('combobox')
    await modelSelect.selectOption({ value: 'v3.0.0' })

    // Note auto-generated experiment ID
    const expIdPlaceholder = await page.getByPlaceholder(/^\d{4}/).getAttribute('placeholder') ?? ''

    await page.getByRole('button', { name: '▶ Launch' }).click()
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })

    const outcome = await waitForRunCompletion(page, 240_000)
    expect(outcome).toBe('success')
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })

    // Navigate to Experiment View and verify attack predictions appear
    await page.getByRole('button', { name: /View Results/ }).click()
    await page.waitForTimeout(2000)
    // Should see attack predictions in the segment predictions table
    await expect(page.getByText(/Attack/i)).toBeVisible({ timeout: 20_000 })
  })

  test('negative attack scenario with v3.0.0', async ({ page }) => {
    await goToRun(page)
    await expect(page.getByText('Simulation Configuration')).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: /Attack \(−\)/ }).click()
    await page.getByRole('spinbutton').nth(0).fill('43')
    await page.getByRole('spinbutton').nth(1).fill(String(SIM_TIME))
    await page.getByRole('spinbutton').nth(2).fill('5000')
    await page.getByRole('combobox').selectOption({ value: 'v3.0.0' })

    await page.getByRole('button', { name: '▶ Launch' }).click()
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })

    const outcome = await waitForRunCompletion(page, 240_000)
    expect(outcome).toBe('success')
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })
  })

  test('run history shows v3.0.0 tag in entries', async ({ page }) => {
    await goToRun(page)
    // History should show entries from previous tests with v3.0.0
    const history = page.getByText('Recent Runs')
    await expect(history).toBeVisible({ timeout: 10_000 })
    // At least one entry should reference v3.0.0
    await expect(page.getByText(/v3\.0\.0/)).toBeVisible()
  })
})
