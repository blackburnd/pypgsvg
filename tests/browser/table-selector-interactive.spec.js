const { test, expect } = require('@playwright/test');

test('table selector is functionally interactive for users', async ({ page }) => {
  // Listen for console messages
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));

  await page.goto('/Samples/complex_schema.svg', { waitUntil: 'domcontentloaded' });

  // Wait for the selector to be visible and accessible
  const selector = '#table-selector';
  await page.locator(selector).waitFor({ timeout: 45000 });

  // IMPORTANT: Wait for the table selector to be properly populated
  // We need to wait for more than 1 option to appear (indicating initialization is complete)
  await page.waitForFunction(() => {
    const selectElement = document.getElementById('table-selector');
    return selectElement && selectElement.options.length > 1;
  }, { timeout: 10000 });

  // Test 1: Verify the select box is visible and clickable
  const selectBox = page.locator(selector);
  await expect(selectBox).toBeVisible();
  await expect(selectBox).toBeEnabled();

  // Test 2: Check how many options we have now (should be 80+ after proper initialization)
  const optionCount = await page.locator(selector + ' option').count();
  console.log(`Found ${optionCount} options in select box after initialization`);

  // Test 3: Verify we have the expected number of options
  expect(optionCount).toBeGreaterThan(70); // Should have 80 tables + 1 default option

  // Test 4: Click the select box to open it
  await selectBox.click();

  // Test 5: Get the second option (first table) and select it
  const firstTableOption = await page.locator(selector + ' option').nth(1);
  const firstTableName = await firstTableOption.textContent();
  
  // Select the first table
  await selectBox.selectOption({ index: 1 });

  // Test 6: Verify that selecting a table triggers highlighting
  // Wait a moment for any JavaScript highlighting to take effect
  await page.waitForTimeout(500);

  // Check if any table got highlighted (should have class 'highlighted')
  const highlightedTables = await page.locator('.node.highlighted').count();
  expect(highlightedTables).toBeGreaterThan(0);

  console.log(`Successfully selected table: ${firstTableName}`);
  console.log(`Number of highlighted elements: ${highlightedTables}`);

  // Test 7: Verify the selection window appears
  const selectionWindow = page.locator('#selection-container');
  await expect(selectionWindow).toBeVisible();

  console.log('Table selector is functionally interactive!');
});
