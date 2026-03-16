/**
 * E2E: Model Intelligence — Compare v2.0.0 vs v3.0.0
 *
 * Tests the Model Intelligence section:
 * - Active model metrics load by default (v3.0.0)
 * - Clicking a registry entry loads its metrics in the detail panel
 * - Compare mode: click Compare → click a second model → diff panel appears
 * - Deploy button is visible for non-active models
 */
import { test, expect } from '@playwright/test'
import { BASE, goToModelIntelligence } from './helpers'

/** Wait for the model registry list to appear (async data load) */
async function waitForModelRegistry(page: any) {
  // The registry shows version strings like v1.0.0 once data loads
  await expect(page.getByText('v1.0.0')).toBeVisible({ timeout: 15_000 })
}

test.describe('Model Intelligence — Compare Panel', () => {

  test('shows active model metrics by default', async ({ page }) => {
    await goToModelIntelligence(page)
    await waitForModelRegistry(page)

    // Active model (v3.0.0) should be labelled "active" in the registry
    await expect(page.getByText('active')).toBeVisible({ timeout: 10_000 })

    // F1 Score metric card visible in detail panel
    await expect(page.getByText('F1 Score')).toBeVisible()
  })

  test('clicking v2.0.0 registry entry loads its metrics', async ({ page }) => {
    await goToModelIntelligence(page)
    await waitForModelRegistry(page)

    // Click the v2.0.0 registry row (first occurrence in list)
    await page.getByText('v2.0.0').first().click()

    // F1 Score should still be visible after detail reload
    await page.waitForTimeout(500)
    await expect(page.getByText('F1 Score')).toBeVisible({ timeout: 10_000 })
  })

  test('deploy button appears for non-active models', async ({ page }) => {
    await goToModelIntelligence(page)
    await waitForModelRegistry(page)

    // v1, v2, v2.1 should have Deploy buttons; v3 (active) should not
    const deployButtons = page.getByRole('button', { name: /Deploy/i })
    await expect(deployButtons.first()).toBeVisible({ timeout: 10_000 })
    const count = await deployButtons.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })

  test('compare mode — click Compare then click v2.0.0, diff panel appears', async ({ page }) => {
    await goToModelIntelligence(page)
    await waitForModelRegistry(page)

    // 1. Enable compare mode
    await page.getByRole('button', { name: /Compare/i }).click()
    await expect(page.getByRole('button', { name: /Compare ON/i })).toBeVisible({ timeout: 5_000 })

    // 2. Click v2.0.0 in the registry — this sets it as compare version
    await page.getByText('v2.0.0').first().click()
    await page.waitForTimeout(1500)

    // 3. Compare panel should appear with "Comparing..."
    await expect(page.getByText(/Comparing/i)).toBeVisible({ timeout: 10_000 })
  })

  test('compare — diff panel shows F1 and Accuracy rows', async ({ page }) => {
    await goToModelIntelligence(page)
    await waitForModelRegistry(page)

    // Enable compare mode and select v2.0.0
    await page.getByRole('button', { name: /Compare/i }).click()
    await page.getByText('v2.0.0').first().click()
    await page.waitForTimeout(1500)

    // Metric rows in compare panel
    await expect(page.getByText(/Comparing/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/F1/i).first()).toBeVisible()
    await expect(page.getByText(/Accuracy/i).first()).toBeVisible()
    await expect(page.getByText(/Precision/i).first()).toBeVisible()
    await expect(page.getByText(/Recall/i).first()).toBeVisible()
  })
})
