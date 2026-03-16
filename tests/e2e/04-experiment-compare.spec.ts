/**
 * E2E: Experiment View — Compare v2.0.0 vs v3.0.0 runs
 *
 * Runs the same positive attack scenario twice — once with v2.0.0 and once with
 * v3.0.0 — then verifies both experiments appear in Experiment View.
 *
 * Note: This test is long (~10 min). Run after 01 and 02 tests have generated data.
 * If both experiments already exist from previous runs, the launch steps are skipped
 * and the test goes straight to comparison.
 */
import { test, expect } from '@playwright/test'
import { BASE, goToExperimentView, launchExperiment, waitForRunCompletion } from './helpers'

const SIM_TIME = 30

test.describe('Experiment View — v2 vs v3 comparison', () => {

  test.beforeEach(async ({ page }) => {
    const resp = await page.request.get(`${BASE}/api/run/status`)
    const status = await resp.json()
    if (status.active) {
      await page.request.post(`${BASE}/api/run/cancel`)
      await page.waitForTimeout(3000)
    }
  })

  test('both v2.0.0 and v3.0.0 experiments appear in Experiment View', async ({ page }) => {
    // Run positive attack with v3.0.0
    const v3ExpId = await launchExperiment(page, {
      scenario: 'positive',
      seed: 77,
      simTime: SIM_TIME,
      bias: 5000,
      gcnVersion: 'v3.0.0',
    })
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })
    let outcome = await waitForRunCompletion(page, 300_000)
    expect(outcome).toBe('success')
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })

    // Run same scenario with v2.0.0
    const v2ExpId = await launchExperiment(page, {
      scenario: 'positive',
      seed: 77,
      simTime: SIM_TIME,
      bias: 5000,
      gcnVersion: 'v2.0.0',
    })
    await expect(page.getByText('Running Experiment')).toBeVisible({ timeout: 15_000 })
    outcome = await waitForRunCompletion(page, 300_000)
    expect(outcome).toBe('success')
    await expect(page.getByText('Experiment Complete')).toBeVisible({ timeout: 30_000 })

    // Navigate to Experiment View
    await goToExperimentView(page)

    // Both experiments should appear in the list
    // Seeds match so partial IDs should be visible
    await expect(page.getByText(/seed77/i)).toBeVisible({ timeout: 30_000 })
    // The list should have at least 2 entries related to these runs
    const expEntries = page.locator('[data-testid="experiment-entry"]')
    const count = await expEntries.count()
    if (count === 0) {
      // Fallback: check for v3.0.0 and v2.0.0 tags in the list
      await expect(page.getByText(/v3\.0\.0/)).toBeVisible({ timeout: 10_000 })
      await expect(page.getByText(/v2\.0\.0/)).toBeVisible({ timeout: 10_000 })
    } else {
      expect(count).toBeGreaterThanOrEqual(2)
    }
  })

  test('Experiment View — clicking an experiment loads its predictions', async ({ page }) => {
    await goToExperimentView(page)

    // Wait for experiment list to load
    await page.waitForTimeout(2000)

    // Click the first experiment entry
    const firstEntry = page.locator('button').filter({ hasText: /\d{8}-\d{4}/ }).first()
    await expect(firstEntry).toBeVisible({ timeout: 15_000 })
    await firstEntry.click()

    // Predictions section should appear
    await expect(page.getByText(/Segment Predictions|predictions/i)).toBeVisible({ timeout: 15_000 })
  })

  test.afterAll(async ({ request }) => {
    // Restore active model to v3.0.0
    await request.post(`${BASE}/api/models/v3.0.0/deploy`)
    await new Promise(r => setTimeout(r, 6000))
  })
})
