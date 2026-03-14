import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 300_000,           // 5 min per test (NS-3 sims take ~90s)
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://localhost:8888',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  reporter: [['html', { outputFolder: 'reports/html' }], ['list']],
  // Run tests sequentially — only one NS-3 sim at a time
  workers: 1,
  retries: 0,
})
