// Professional Playwright configuration
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  retries: 0,
  use: {
    headless: true, // Default to headless, override with --headed
    viewport: { width: 1280, height: 800 },
    actionTimeout: 10000,
    baseURL: 'http://localhost:8081',
  },
  outputDir: 'test-results/',
  reporter: [['list'], ['html', { outputFolder: 'test-results/html-report' }]],
});
