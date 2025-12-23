const { test, expect } = require('@playwright/test');

test('table selector is functionally interactive for users', async ({ page }) => {
  // Listen for console messages
  //page.on('console', msg => console.debug('PAGE LOG:', msg.text()));

  await page.goto('/Samples/complex_schema.svg', { waitUntil: 'domcontentloaded' });

  // Wait for the metadata container to be visible
  await page.waitForSelector('#metadata-container', { state: 'visible', timeout: 10000 });

  // Wait for the selector to be attached
  const selector = '#table-selector';
  await page.locator(selector).waitFor({ state: 'attached', timeout: 45000 });

  // Wait for the table selector to be properly populated
  await page.waitForFunction(() => {
    const selectElement = document.getElementById('table-selector');
    return selectElement && selectElement.options.length > 1;
  }, { timeout: 10000 });

  // Clear any existing highlights to put selector in single-select mode
  await page.evaluate(() => {
    // Hide selection container first so clearAllHighlights will work
    const selectionContainer = document.getElementById('selection-container');
    if (selectionContainer) {
      selectionContainer.style.display = 'none';
    }

    // Clear all highlights from nodes and edges
    const highlightedElements = document.querySelectorAll('.node.highlighted, .edge.highlighted');
    highlightedElements.forEach(el => el.classList.remove('highlighted'));

    // Wait a tick for DOM to update
    return new Promise(resolve => setTimeout(resolve, 10));
  });

  // Now call updateTableSelector after highlights are cleared
  const highlightInfo = await page.evaluate(() => {
    const highlighted = document.querySelectorAll('.node.highlighted');
    console.log(`Before update: Found ${highlighted.length} highlighted nodes`);

    if (window.updateTableSelector) {
      window.updateTableSelector();
    }

    const highlightedAfter = document.querySelectorAll('.node.highlighted');
    console.log(`After update: Found ${highlightedAfter.length} highlighted nodes`);

    return {
      before: highlighted.length,
      after: highlightedAfter.length
    };
  });

  console.log(`Highlighted nodes - Before: ${highlightInfo.before}, After: ${highlightInfo.after}`);

  // Wait for selector to update to single-select mode (all tables)
  await page.waitForTimeout(500);

  // Test 1: Verify the select box is attached and enabled
  const selectBox = page.locator(selector);
  await expect(selectBox).toBeAttached();
  await expect(selectBox).toBeEnabled();

  // Test 2: Check how many options we have now (should be 1+ after switching to all tables)
  const optionCount = await page.locator(selector + ' option').count();
  console.log(`Found ${optionCount} options in select box after initialization`);

  // Test 3: Verify we have the expected number of options (0 + tables + 1 default option)

  expect(optionCount).toBeGreaterThan(1);

  // Test 4: Get the second option (first table) and select it
  const firstTableOption = await page.locator(selector + ' option').nth(1);
  const firstTableName = await firstTableOption.textContent();

  // Select the first table - use force:true since the select may be in a container with special styling
  await selectBox.selectOption({ index: 1 }, { force: true });

  // Test 5: Verify that selecting a table triggers highlighting
  // Wait a moment for any JavaScript highlighting to take effect
  await page.waitForTimeout(500);

  // Check if any table got highlighted (should have class 'highlighted')
  const highlightedTables = await page.locator('.node.highlighted').count();
  expect(highlightedTables).toBeGreaterThan(0);

  console.log(`Successfully selected table: ${firstTableName}`);
  console.log(`Number of highlighted elements: ${highlightedTables}`);

  // Test 6: Verify the selection window appears
  const selectionWindow = page.locator('#selection-container');
  await expect(selectionWindow).toBeVisible();

  console.log('Table selector is functionally interactive!');
});
