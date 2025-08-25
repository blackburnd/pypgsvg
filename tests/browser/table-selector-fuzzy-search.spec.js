const { test, expect } = require('@playwright/test');
const path = require('path');

test.describe('Table Selector Fuzzy Search', () => {
  test.beforeEach(async ({ page }) => {
  // Use HTTP server URL to load the SVG
  const fileUrl = `${process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8123'}/Samples/complex_schema.svg`;
  await page.goto(fileUrl);
    await page.waitForLoadState('domcontentloaded');
    
    // Wait for metadata container to be available, then we're ready
    await page.locator('#metadata-container').waitFor({ state: 'visible' });
  });

  test('fuzzy search input field exists in metadata container', async ({ page }) => {
    // Check if the metadata container exists
    const metadataContainer = page.locator('#metadata-container');
    await expect(metadataContainer).toBeVisible();
    
    // Look for the fuzzy search input field
    const searchInput = page.locator('#table-search-input');
    await expect(searchInput).toBeVisible();
    
    // Verify it has the correct placeholder
    await expect(searchInput).toHaveAttribute('placeholder', 'Search tables...');
  });

  test('fuzzy search filters tables as user types', async ({ page }) => {
    // Get the search input
    const searchInput = page.locator('#table-search-input');
    
    // Type a search query (we'll use a common word that might appear in table names)
    await searchInput.fill('data');
    
    // Wait briefly for results to appear
    await page.waitForTimeout(200);
    
    // Check that search results container is visible
    const searchResults = page.locator('.search-results');
    await expect(searchResults).toBeVisible();
    
    // Check that result items are present
    const resultItems = page.locator('.search-results .result-item');
    const resultCount = await resultItems.count();
    expect(resultCount).toBeGreaterThan(0);
  });

  test('fuzzy search handles partial matches', async ({ page }) => {
    const searchInput = page.locator('#table-search-input');
    
    // Test partial matching (e.g., "ord" should match "order", "orders", etc.)
    await searchInput.fill('ord');
    await page.waitForTimeout(200);
    
    // Verify that some results are shown (fuzzy matching)
    const searchResults = page.locator('.search-results');
    await expect(searchResults).toBeVisible();
    
    const resultItems = page.locator('.search-results .result-item');
    const resultCount = await resultItems.count();
    expect(resultCount).toBeGreaterThan(0);
  });

  test('selecting a search result highlights the table', async ({ page }) => {
    const searchInput = page.locator('#table-search-input');
    
    // Search for a table
    await searchInput.fill('or');
    await page.waitForTimeout(200);
    
    // Click on the first search result
    const firstResult = page.locator('.search-results .result-item').first();
    await expect(firstResult).toBeVisible();
    await firstResult.click();
    
    // Verify that a table becomes highlighted in the SVG
    const highlightedTable = page.locator('g.node.highlighted');
    await expect(highlightedTable).toBeVisible();
    
    // Verify search input is cleared and results are hidden
    await expect(searchInput).toHaveValue('');
    const searchResults = page.locator('.search-results');
    await expect(searchResults).toBeHidden();
  });

  test('search clears results when input is empty', async ({ page }) => {
    const searchInput = page.locator('#table-search-input');
    
    // Type search query
    await searchInput.fill('data');
    await page.waitForTimeout(200);
    
    // Verify results are shown
    const searchResults = page.locator('.search-results');
    await expect(searchResults).toBeVisible();
    
    // Clear the search
    await searchInput.fill('');
    await page.waitForTimeout(200);
    
    // Verify results are hidden
    await expect(searchResults).toBeHidden();
  });

  test('fuzzy search is case insensitive', async ({ page }) => {
    const searchInput = page.locator('#table-search-input');
    
    // Test with uppercase
    await searchInput.fill('ORDER');
    await page.waitForTimeout(200);
    
    const searchResults = page.locator('.search-results');
    await expect(searchResults).toBeVisible();
    
    const upperCaseResults = page.locator('.search-results .result-item');
    const upperCaseCount = await upperCaseResults.count();
    
    // Clear and test with lowercase
    await searchInput.fill('');
    await page.waitForTimeout(100);
    await searchInput.fill('order');
    await page.waitForTimeout(200);
    
    const lowerCaseResults = page.locator('.search-results .result-item');
    const lowerCaseCount = await lowerCaseResults.count();
    
    // Both should return results (case insensitive)
    expect(upperCaseCount).toBeGreaterThan(0);
    expect(lowerCaseCount).toBeGreaterThan(0);
    expect(upperCaseCount).toBe(lowerCaseCount);
  });
});
