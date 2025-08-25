# Testing Best Practices for AI Assistants

This guide outlines the proper approach for AI assistants when running and analyzing tests for the pypgsvg project.

## Core Testing Principles

1. **Fix First, View Later**
   - Focus on making tests pass before examining visual outputs or reports
   - Never open or display test results unless all tests pass successfully

2. **Complete Environment Verification**
   - Always verify virtual environment exists before running tests
   - Install all necessary dependencies (including test dependencies)
   - Use consistent testing environment for all test runs

3. **Methodical Test Execution**
   - Run tests in a systematic way to identify problems
   - Use the provided `run-tests.sh` script for consistency

## Test Execution Workflow

### 1. Environment Setup

```bash
# Check if virtual environment exists, create if needed
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

# Activate the virtual environment
source .venv/bin/activate

# Install package and test dependencies
pip install -e ".[test]"
```

### 2. Unit Test Execution

```bash
# Run unit tests
./run-tests.sh
# or directly
python -m pytest tests/tests/ -v
```

### 3. Browser Test Execution

```bash
# Run browser tests
./run-tests.sh --browser
# or directly
npx playwright test tests/browser/
```

### 4. Test Result Processing

- If tests **FAIL**:
  - Analyze failures methodically
  - Fix issues in order of dependency (fix fundamental issues first)
  - Re-run tests after each fix until all pass
  - DO NOT open or display visual results

- If tests **PASS**:
  - Only then proceed to open and view results
  - Verify visual elements match expected behavior
  - Check generated files for correctness

## Common Test Failures and Solutions

### Unit Test Failures

- **Import errors**: Check dependencies are installed
- **File not found**: Verify file paths and test fixtures
- **Assertion failures**: Check logic in code matches test expectations

### Browser Test Failures

- **Element not found**: Verify HTML/SVG structure includes expected elements
- **Timeout errors**: Increase timeouts or check if elements are being rendered
- **Z-index issues**: Ensure elements are visible and not covered by others
- **JavaScript errors**: Check browser console for errors in JS execution

## Visual Testing Guidelines

When examining visual output (only after tests pass):

1. Verify that UI elements appear as expected
2. Check interactions work correctly (hover, click, drag)
3. Ensure responsive behavior works across different sizes
4. Validate that data is correctly displayed

## AI Assistant Specific Guidelines

AI assistants working with this codebase should:

1. Always run the test suite before suggesting code changes
2. Fix failing tests before proceeding with feature implementation
3. Run incremental tests during development to catch issues early
4. Provide clear explanations of test failures when reporting to users
5. Only share/display test results when they are successful
6. Include test coverage for any new features implemented

By following these guidelines, AI assistants can maintain code quality and ensure a consistent testing approach for the pypgsvg project.
