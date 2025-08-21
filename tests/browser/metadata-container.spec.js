const { test, expect } = require('@playwright/test');
const path = require('path');

test('metadata container exists in SVG', async ({ page }) => {
  // Use file:// URL to load the SVG directly from filesystem
  const svgPath = path.resolve(__dirname, '../../Samples/complex_schema.svg');
  const fileUrl = `file://${svgPath}`;
  
  await page.goto(fileUrl);
  await page.waitForLoadState('domcontentloaded');
  
  // Wait a bit for any dynamic content to load
  await page.waitForTimeout(2000);
  
  // Simple check - just verify the metadata container exists
  const metadataContainer = page.locator('#metadata-container');
  await expect(metadataContainer).toBeVisible();
});

test('copy button exists and can be clicked', async ({ page }) => {
  // Use file:// URL to load the SVG directly from filesystem
  const svgPath = path.resolve(__dirname, '../../Samples/complex_schema.svg');
  const fileUrl = `file://${svgPath}`;
  
  await page.goto(fileUrl);
  await page.waitForLoadState('domcontentloaded');
  
  // Wait a bit for any dynamic content to load
  await page.waitForTimeout(2000);
  
  // Verify the copy button exists and is visible
  const copyButton = page.locator('#metadata-container .copy-btn');
  await expect(copyButton).toBeVisible();
  
  // Click the copy button
  await copyButton.click();
  
  // Verify the button was successfully clicked by checking if it's still visible
  // (we can't easily test clipboard functionality in headless mode without special permissions)
  await expect(copyButton).toBeVisible();
});
