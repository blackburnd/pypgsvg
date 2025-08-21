// Professional Playwright configuration
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  retries: 0,
  use: {
    headless: true, // Always run tests in headless mode
    viewport: { width: 1280, height: 800 },
    actionTimeout: 10000,
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8081',
  },
  outputDir: 'test-results/playwright',
  reporter: [['list'], ['html', { outputFolder: 'test-results/html-report' }]],
  webServer: {
    command: 'python3 -m http.server 8081',
    port: 8081,
    reuseExistingServer: false,
    timeout: 30000,
  },
});
