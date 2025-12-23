// Professional Playwright configuration
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './browser',
  timeout: 30000,
  retries: 0,
  globalSetup: require.resolve('./browser/global-setup.js'),
  globalTeardown: require.resolve('./browser/global-teardown.js'),
  use: {
    headless: true, // Default to headless, override with --headed
    viewport: { width: 1280, height: 800 },
    actionTimeout: 10000,
    baseURL: `http://localhost:${process.env.TEST_HTTP_PORT || 8123}`,
    javaScriptEnabled: true,
    permissions: ['clipboard-read', 'clipboard-write'],
  },
  outputDir: 'test-results/artifacts/',
  reporter: [['list'], ['html', { outputFolder: 'test-results/html-report' }]],
});
