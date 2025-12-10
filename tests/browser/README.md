# Browser Functional Tests

This directory contains functional browser tests for the interactive features of the SVG output. Tests are implemented using Playwright for robust browser automation and UI verification.

## Interactive Features Tested

The test suite verifies the following interactive capabilities:

1. **Metadata Container** - Schema statistics, Graphviz settings, database connection controls, and print-friendly export
2. **Table Selection** - Click and double-click interactions, selection highlighting, and relationship navigation
3. **Smart Initial View** - Automatic selection and zoom to the table with most connections
4. **Miniature Navigator** - Interactive overview panel with viewport indicator
5. **Selection Details Panel** - SQL definitions display, copy/download functions, and focused ERD generation
6. **Info Toggle** - Show/hide informational windows
7. **Real-Time Regeneration** - Graphviz settings modification and diagram regeneration

## Setup

Install dependencies:
```bash
pip install playwright
playwright install
```

Or use the automated setup script:
```bash
./run-tests.sh --browser
```

## Running Tests

```bash
# Run all browser tests
npx playwright test tests/browser/

# Run specific test file
npx playwright test tests/browser/metadata-container.spec.js

# Run with visible browser (headed mode)
npx playwright test tests/browser/ --headed

# Run with trace for debugging
npx playwright test tests/browser/ --trace on
```

## Purpose

- Ensure all interactive features work as expected in a real browser environment
- Simulate user interactions (clicks, double-clicks, drags, hovers)
- Verify UI changes and state transitions
- Test responsive behavior of panels and controls
- Validate accessibility and usability

## Extending

Add new test files for additional features as needed. Keep all browser-based tests in this directory for organization. Follow the existing test patterns for consistency.
