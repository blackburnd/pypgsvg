const { test, expect } = require('@playwright/test');
const path = require('path');
const http = require('http');
const serveHandler = require('serve-handler');

const svgDir = path.resolve(__dirname, '../../Samples');
const PORT = 8081;
let server;

test.beforeAll(async () => {
  server = http.createServer((request, response) => {
    return serveHandler(request, response, { public: svgDir });
  });
  await new Promise(resolve => server.listen(PORT, resolve));
});

test.afterAll(async () => {
  await new Promise(resolve => server.close(resolve));
});

test('user loads SVG, waits for DOMContentLoaded, clicks copy button, verifies click and clipboard', async ({ page }) => {
  await page.goto(`http://localhost:${PORT}/schema_erd.svg`);
  await page.waitForLoadState('domcontentloaded');
  const copyButton = page.locator('#metadata-container .copy-button');
  await expect(copyButton).toBeVisible();
  await copyButton.click();
  // Verify button looks clicked (e.g., has a class or style)
  await expect(copyButton).toHaveClass(/clicked|active/);
  // Verify clipboard content
  const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
  expect(clipboardText.length).toBeGreaterThan(0);
});
