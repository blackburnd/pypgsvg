# Testing Guide for pypgsvg

This guide outlines the standard procedures for running tests in the pypgsvg project.

## Types of Tests

The pypgsvg project has two main test suites:

1. **Unit Tests** - Python tests using pytest, located in `tests/tests/`
2. **Functional Tests** - Browser-based tests using Playwright, located in `tests/browser/`

## Test Environment Setup

Before running any tests, ensure your environment is properly configured.

### Virtual Environment

Always use a Python virtual environment for consistent testing:

```bash
# Check if virtual environment exists, create if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
# .venv\Scripts\activate   # Windows
```

### Install Dependencies

Install the package and its test dependencies in development mode:

```bash
# Install the package with test dependencies
pip install -e ".[test]"
```

This installs:
- The pypgsvg package itself
- pytest, pytest-cov for unit testing
- playwright for browser tests

## Running Unit Tests

Unit tests verify the core functionality of the Python code.

```bash
# Run all unit tests with coverage reports
python -m pytest tests/tests/ -v

# Run specific test files
python -m pytest tests/tests/test_erd_generator.py -v

# Run specific test functions
python -m pytest tests/tests/test_parser.py::test_parse_sql_dump -v
```

## Running Browser/Functional Tests

Browser tests verify the interactive features of the SVG outputs.

### Prerequisites

1. Ensure Playwright browsers are installed:

```bash
# Install browsers needed for testing
npx playwright install
```

2. Start the HTTP server (automatic with test suite):

The test suite automatically starts and stops an HTTP server on port 8123.

### Running the Tests

```bash
# Run all browser tests
npx playwright test tests/browser/

# Run a specific browser test file
npx playwright test tests/browser/metadata-container.spec.js

# Run with visible browser (not headless)
npx playwright test tests/browser/ --headed
```

## Common Issues and Solutions

### HTTP Server Issues
- If browser tests fail with connection errors, check that the HTTP server starts properly
- Verify port 8123 is available and not used by another process

### Missing Dependencies
- If tests fail with import errors, ensure all dependencies are installed with `pip install -e ".[test]"`

### Browser Test Failures
- For visual/UI test failures, check that the generated SVGs include the expected elements
- Verify that any CSS class or ID referenced in tests actually exists in the SVG output

## CI/CD Integration

When running in CI/CD environments, follow the same pattern:

1. Set up virtual environment
2. Install dependencies
3. Run unit tests
4. Run browser tests (with proper browser installation)

## Test Development Guidelines

When adding new tests:

1. Unit tests should focus on individual functions and components
2. Browser tests should verify end-to-end functionality and user interactions
3. Maintain the test directory structure (unit tests in `tests/tests/`, browser tests in `tests/browser/`)
4. Ensure proper assertions and error messages for easy debugging
