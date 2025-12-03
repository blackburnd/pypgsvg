const { test, expect } = require('@playwright/test');

test('I key toggles informational windows visibility', async ({ page }) => {
  // Navigate to the SVG
  await page.goto('/Samples/complex_schema.svg', { waitUntil: 'domcontentloaded' });

  // Wait for the containers to be loaded
  await page.waitForSelector('#metadata-container', { timeout: 10000 });
  await page.waitForSelector('#miniature-container', { timeout: 10000 });

  // Verify all info containers are initially visible
  const metadataContainer = page.locator('#metadata-container');
  const miniatureContainer = page.locator('#miniature-container');
  
  await expect(metadataContainer).toBeVisible();
  await expect(miniatureContainer).toBeVisible();

  // Press 'I' key to hide containers
  await page.keyboard.press('i');

  // Verify containers are now hidden
  await expect(metadataContainer).toBeHidden();
  await expect(miniatureContainer).toBeHidden();

  // Press 'I' key again to show containers
  await page.keyboard.press('i');

  // Verify containers are visible again
  await expect(metadataContainer).toBeVisible();
  await expect(miniatureContainer).toBeVisible();

  // Test uppercase 'I' as well
  await page.keyboard.press('I');
  await expect(metadataContainer).toBeHidden();
  await expect(miniatureContainer).toBeHidden();
});

test('URL parameter hide starts with informational windows hidden', async ({ page }) => {
  // Navigate to the SVG with hide parameter (using the format that works manually)
  await page.goto('/Samples/complex_schema.svg?hide=t', { waitUntil: 'domcontentloaded' });

  // Wait for the containers to be created AND visible first (normal initialization)
  await page.waitForSelector('#metadata-container', { state: 'visible', timeout: 10000 });
  await page.waitForSelector('#miniature-container', { state: 'visible', timeout: 10000 });

  // Give a small delay for the URL parameter processing to complete
  await page.waitForTimeout(500);

  // Now verify containers are hidden due to URL parameter
  const metadataContainer = page.locator('#metadata-container');
  const miniatureContainer = page.locator('#miniature-container');
  
  await expect(metadataContainer).toBeHidden();
  await expect(miniatureContainer).toBeHidden();

  // Press 'I' to show them
  await page.keyboard.press('i');
  
  await expect(metadataContainer).toBeVisible();
  await expect(miniatureContainer).toBeVisible();
});

test('selection container is also toggled with I key', async ({ page }) => {
  // Navigate to the SVG
  await page.goto('/Samples/complex_schema.svg', { waitUntil: 'domcontentloaded' });

  // Wait for containers to load
  await page.waitForSelector('#metadata-container', { timeout: 10000 });

  // Click on a table to show selection container
  await page.click('g.node');
  
  // Wait for selection container to appear
  const selectionContainer = page.locator('#selection-container');
  await expect(selectionContainer).toBeVisible();

  // Press 'I' to hide all info containers including selection
  await page.keyboard.press('i');
  
  await expect(selectionContainer).toBeHidden();

  // Press 'I' again to show all containers
  await page.keyboard.press('i');
  
  await expect(selectionContainer).toBeVisible();
});