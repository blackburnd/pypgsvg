
const { test, expect } = require('@playwright/test');

test('table selector uses all tables from graphData', async ({ page }) => {
  await page.goto('/Samples/complex_schema.svg', { waitUntil: 'domcontentloaded' });

  // Wait for the selector to be visible
  const selector = '#table-selector';
  await page.locator(selector).waitFor({ timeout: 45000 });

  // Get the graphData object from the page
  const graphData = await page.evaluate(() => {
    const script = document.getElementById('graph-data');
    return script ? JSON.parse(script.textContent) : null;
  });
  expect(graphData).not.toBeNull();
  const tableCount = Object.keys(graphData.tables).length;

  // Get all option elements inside the select
  const options = await page.locator(selector + ' option').elementHandles();

  // The first option is usually 'All Tables', so subtract 1 if needed
  // If you want to count only actual tables, skip the first option
  const actualTableOptions = options.slice(1);
  expect(actualTableOptions.length).toBe(tableCount);

  // Optionally, print the table names for debug
  const tableNames = await Promise.all(actualTableOptions.map(async (opt) => await opt.textContent()));
  console.log('Table names:', tableNames);
});
