# Testing Guide for pypgsvg

This guide outlines the standard procedures for running tests in the pypgsvg project. 

And for those who choose to try AI agents, this file can also help as an instruction set.

## Simplified Testing with `run-tests.sh`

A shell script `run-tests.sh` is provided to simplify the entire testing process. This script handles everything from environment setup to running the tests.

### What the Script Does

1.  **Virtual Environment**: It automatically creates a Python virtual environment in a `.venv` directory. This prevents polluting your system's Python packages and ensures a clean, isolated environment for testing.
2.  **Dependency Installation**: It installs all necessary dependencies for running both unit and browser tests. This includes:
    *   [`pytest`](https://docs.pytest.org/): For running Python unit tests.
    *   [`pytest-cov`](https://pytest-cov.readthedocs.io/): For measuring test coverage.
    *   [`playwright`](https://playwright.dev/): For running browser-based functional tests.
    *   It also installs the [`pypgsvg`](https://github.com/blackburnd/pypgsvg) package in editable mode.
3.  **Browser Installation**: For browser tests, it automatically runs `npx playwright install` to download the required browser binaries if they are not already present.

### How to Run Tests

To run the tests, simply execute the script from the root of the project.

**Running Unit Tests**

This is the default behavior and most efficient.
```bash
./run-tests.sh
```

**Running Browser/Functional Tests**

To run the Playwright browser tests, use the `--browser` flag.
```bash
./run-tests.sh --browser
```

You can also run the browser tests in headed mode (with a visible browser window) by passing the `--headed` flag.
```bash
./run-tests.sh --browser --headed
```

**Running Tests with Coverage**

To generate a test coverage report, you can pass the necessary `pytest-cov` arguments to the script. The report will be generated in the `htmlcov` directory.

```bash
# Run unit tests with coverage report
./run-tests.sh --cov=src --cov-report=html

# After running, open the report in your browser
open htmlcov/index.html
```

### Types of Tests

The pypgsvg project has two main test suites:

1.  **Unit Tests** - Python tests using pytest, located in `tests/tests/`
2.  **Functional Tests** - Browser-based tests using Playwright, located in `tests/browser/`

### Manual Test Environment Setup
Instead of running the run-tests.sh, you can manually install the requirements to properly test the software.

#### Virtual Environment

Always use a Python virtual environment for consistent testing ( the run-tests.sh does this also.):

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

#### Manual Install Dependencies

Install the package and its test dependencies in development mode:

```bash
# Install the package with test dependencies
pip install -e ".[test]"
```

This installs:
- The [`pypgsvg`](https://github.com/blackburnd/pypgsvg) package itself
- [`pytest`](https://docs.pytest.org/), [`pytest-cov`](https://pytest-cov.readthedocs.io/) for unit testing
- [`playwright`](https://playwright.dev/) for browser tests

### Manually Running Unit Tests


Unit tests verify the core functionality of the Python code.

```bash
# Run all unit tests with coverage reports
python -m pytest tests/tests/ -v

# Run specific test files
python -m pytest tests/tests/test_erd_generator.py -v

# Run specific test functions
python -m pytest tests/tests/test_parser.py::test_parse_sql_dump -v
```

### Running Browser/Functional Tests

Browser tests verify the interactive features of the SVG outputs.

#### Prerequisites

1.  Ensure Playwright browsers are installed:

```bash
# Install browsers needed for testing
npx playwright install
```

2.  Start the HTTP server (automatic with test suite):

The test suite automatically starts and stops an HTTP server on port 8123.

#### Running the Tests

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

When running in CI/CD environments use run-tests.sh or follow the same pattern:

1.  Set up virtual environment
2.  Install dependencies
3.  Run unit tests
4.  Run browser tests (with proper browser installation)

## Test Development Guidelines

When adding new tests use run-tests.sh or follow this pattern:

1.  Unit tests should focus on individual functions and components
2.  Browser tests should verify end-to-end functionality and user interactions
3.  Maintain the test directory structure (unit tests in `tests/tests/`, browser tests in `tests/browser/`)
4.  Ensure proper assertions and error messages for easy debugging
