const { test, expect } = require('@playwright/test');

// Use the HTML wrapper for the SVG to ensure scripts run
const HTML_URL = process.env.PLAYWRIGHT_BASE_URL
  ? `${process.env.PLAYWRIGHT_BASE_URL}/tests/browser/documents/complex_schema_inline.html`
  : path.join(__dirname, 'documents/complex_schema_inline.html');

test('user loads SVG via HTTP, interacts with copy button inside SVG', async ({ page }) => {
  await page.goto(HTML_URL, { timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 45000 });
  // Wait for the inline SVG to be present
  const svgElement = page.locator('svg');
  await expect(svgElement).toBeVisible({ timeout: 45000 });
  // Interact with the metadata-container copy button inside the SVG
  const copyButton = page.locator('#metadata-container .copy-button');
  await expect(copyButton).toBeVisible({ timeout: 45000 });
  const initialText = await copyButton.innerText();
  await copyButton.click();
  const changedText = await copyButton.innerText();
  expect(changedText).not.toBe(initialText);
});
