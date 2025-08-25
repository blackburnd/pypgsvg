npx playwright test tests/xvfb-run PLAYWRIGHT_BASE_URL="http://localhost:8081" npx playwright test tests/browser/metadata-container.spec.js --trace on --debugxvfb-run PLAYWRIGHT_BASE_URL="http://localhost:8081" npx playwright test tests/browser/metadata-container.spec.js --trace on --debugxvfb-run --server-args="-screen 0 1280x800x24" bash -c 'PLAYWRIGHT_BASE_URL="http://localhost:8081" npx playwright test tests/browser/metadata-container.spec.js --trace on --debug'browser/metadata-container.spec.jsnpm install --save-dev @playwright/test# Browser Functional Tests

This directory contains functional browser tests for the reactive behavior of the SVG output, specifically focusing on the metadata-container. Tests are implemented using Playwright for robust browser automation and UI verification.

## Setup

- Install dependencies with `pip install playwright` and run `playwright install` to download browser binaries.
- Tests will be added in this directory and can be run using Playwright's CLI or pytest integration.

## Purpose

- Ensure the metadata-container's interactive features work as expected in a real browser environment.
- Simulate user interactions and verify UI changes.

## Extending

Add new test files for additional features as needed. Keep all browser-based tests in this directory for organization.
