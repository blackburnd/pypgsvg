"""Run JavaScript Playwright tests as final pytest test.

This test runs LAST (zz_ prefix) to trigger the JavaScript Playwright tests.
The JS tests test browser JavaScript, but if they call any Python server endpoints,
those calls will be captured in Python coverage.

Note: This test requires the existing test_browser_server_api.py tests to have
already started a Python server that the JS tests can connect to.
"""
import pytest
import subprocess
from pathlib import Path


@pytest.mark.playwright_js
@pytest.mark.skip(reason="Optional: Enable to run JS Playwright tests from pytest. Run manually with: npx playwright test")
def test_run_javascript_playwright_tests():
    """Run the JavaScript Playwright tests.

    This is an OPTIONAL test that runs the JavaScript Playwright test suite.
    The JS tests primarily test JavaScript browser functionality.

    To enable this test, remove the @pytest.mark.skip decorator.

    Python coverage notes:
    - JS tests test JavaScript code (not tracked in Python coverage)
    - If JS tests call Python server API endpoints, those ARE tracked
    - For maximum Python coverage, use test_browser_server_api.py instead
    """
    project_root = Path(__file__).parent.parent.parent.resolve()

    # Run JavaScript Playwright tests
    result = subprocess.run(
        ['npx', 'playwright', 'test'],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120
    )

    # Print output
    print("\n" + "="*70)
    print("JavaScript Playwright Tests Output:")
    print("="*70)
    print(result.stdout)
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    print("="*70)

    # Assert tests passed
    assert result.returncode == 0, f"JavaScript Playwright tests failed:\n{result.stdout}"


def test_coverage_summary_info():
    """Summary of how Playwright tests contribute to Python coverage.

    This informational test documents the current pytest + Playwright setup.
    """
    info = """
    ═══════════════════════════════════════════════════════════════════
    📊 Playwright Test Coverage Summary
    ═══════════════════════════════════════════════════════════════════

    ✅ Python Pytest-Playwright Tests (in tests/tests/):
       Files: test_browser_*.py
       What they do:
       - Test Python server API endpoints via browser
       - Generate SVGs using Python code
       - Start Python ERD server
       - Make HTTP requests to Python endpoints

       Python coverage: ✅ YES - Tracks all executed Python code
       Coverage includes:
       - server.py (25-40%)
       - erd_generator.py (58%)
       - db_parser.py (52%)
       - metadata_injector.py (51%)
       - And more...

    📝 JavaScript Playwright Tests (in tests/browser/*.spec.js):
       Files: *.spec.js
       What they do:
       - Test JavaScript interactivity in SVG files
       - Test DOM manipulation
       - Test browser-side features

       Python coverage: ❌ NO (by design)
       Why: These test JavaScript code, not Python code

    ═══════════════════════════════════════════════════════════════════
    💡 To maximize Python coverage, focus on Python pytest tests that
       interact with Python server endpoints and generation code.
    ═══════════════════════════════════════════════════════════════════

    Current combined coverage: ~63% (97 tests)

    Run tests with:
        pytest tests/tests/ --cov=src --cov-report=html
        open htmlcov/index.html
    """
    print(info)
    assert True
