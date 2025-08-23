
# Copilot Instructions: Efficient Testing for pypgsvg

## Quick Setup
- Ensure Graphviz is installed (`sudo apt-get install -y graphviz`).
- Install Python dependencies: `pip install -r requirements.txt`.
- Install Playwright and browsers: `npm install && npx playwright install`.




## Python Virtual Environment
Always ensure you are in the Python virtual environment before running any tests. If not already active, run:

```bash
. venv/bin/activate
```

## Test Workflow (Automated)
Run all tests and generate SVG with a single command—no manual confirmation needed:

```bash
python3 -m src.pypgsvg Samples/complex_schema.dump --output Samples/complex_schema && \
pytest tests/tests && \
npx playwright test tests/browser && \
npx playwright show-report test-results/html-report
```

This will:
- Generate a fresh complex_schema.svg
- Run all Python unit tests
- Run Playwright browser tests in headless mode
- Open the HTML report for results

You do not need to confirm or run steps individually—just execute the above command.

## Quick Playwright-Only Test
To generate a new complex_schema.svg and run only Playwright browser tests:

```bash
python3 -m src.pypgsvg Samples/complex_schema.dump --output Samples/complex_schema && \
npx playwright test tests/browser && \
npx playwright show-report test-results/html-report
```

This will:
- Generate a fresh complex_schema.svg
- Run only Playwright browser tests in headless mode
- Open the HTML report for results

## Automation
- Automate SVG generation before Playwright tests.
- Auto-start HTTP server for browser tests if required.
- Clean up test artifacts after runs.

## File/Folder Ignore
- node_modules, .venv, __pycache__

## Extensions/Tools
- VS Code Python, Playwright, GitLens

---
Add more instructions as your workflow evolves.
