# Working with Claude on pypgsvg

This document provides guidance for developers using Claude AI to contribute to the `pypgsvg` project. It covers best practices, common workflows, and tips for effective collaboration.

## Project Overview

`pypgsvg` is a Python tool that generates interactive SVG diagrams from PostgreSQL database dumps. The project includes:

- **Python backend**: Parses SQL dumps and generates ERD diagrams using Graphviz
- **JavaScript frontend**: Provides interactivity within the generated SVG files
- **Playwright tests**: Automated browser testing for the interactive features
- **Agent-based workflow**: Automated development pipeline (see `CONTRIBUTING.md`)

## Getting Started with Claude

### Essential Commands

Before working on the project, always ensure the environment is properly set up:

```bash
# Activate the Python virtual environment
source venv/bin/activate

# Install dependencies in editable mode
pip install -e .

# Start the web server for tests (background)
python3 -m http.server 8000 &

# Generate a fresh SVG for testing
pypgsvg Samples/complex_schema.dump -o Samples/complex_schema

# Run all tests
npx playwright test
```

### Key Files and Their Purposes

- **`src/pypgsvg.py`**: Main entry point for the command-line tool
- **`src/pypgsvg/erd_generator.py`**: Core logic for generating ERD diagrams
- **`src/pypgsvg/svg_interactivity.js`**: JavaScript for SVG interactivity
- **`tests/browser/`**: Playwright browser tests
- **`Samples/complex_schema.svg`**: Generated test SVG file
- **`copilot-instructions.md`**: Automation instructions for the testing workflow

### Common Workflows

#### 1. Adding New Features

1. **Understand the codebase**: Read the relevant files first
2. **Make changes**: Implement the feature in the appropriate modules
3. **Test locally**: Generate a new SVG and verify it works
4. **Run tests**: Execute the full test suite
5. **Commit changes**: Use descriptive commit messages

#### 2. Debugging Issues

1. **Reproduce the issue**: Generate a fresh SVG to see the current state
2. **Check logs**: Look for Python errors or JavaScript console errors
3. **Isolate the problem**: Determine if it's in the Python generation or JavaScript interaction
4. **Fix incrementally**: Make small changes and test frequently

#### 3. Working with Tests

The project uses Playwright for browser testing. Tests verify that:
- SVG elements are properly generated
- JavaScript interactivity works correctly
- The table selector is populated with correct data

Always run tests after making changes:
```bash
npx playwright test
```

## Best Practices for Claude Users

### Code Changes

1. **Read before writing**: Always examine existing code patterns and follow them
2. **Test incrementally**: Generate and test SVGs after each significant change
3. **Preserve functionality**: Don't break existing features when adding new ones
4. **Use the agent workflow**: Follow the structured approach in `CONTRIBUTING.md`

### File Editing

1. **Use precise edits**: When using tools like `replace_string_in_file`, include enough context
2. **Maintain consistency**: Follow existing code style and naming conventions
3. **Handle edge cases**: Consider error conditions and null values
4. **Document changes**: Add comments for complex logic

### Testing Strategy

1. **Test early and often**: Don't wait until the end to run tests
2. **Use both unit and browser tests**: Python tests for logic, Playwright for UI
3. **Check multiple browsers**: Ensure cross-browser compatibility
4. **Validate SVG output**: Manually inspect generated diagrams

### Git Workflow

1. **Stage changes carefully**: Review what you're committing
2. **Write meaningful commits**: Describe what changed and why
3. **Keep commits focused**: One logical change per commit
4. **Use branch names that describe the feature**

## Common Pitfalls and Solutions

### Python Environment Issues

**Problem**: Commands fail with module not found errors
**Solution**: Always activate the virtual environment first:
```bash
source venv/bin/activate
```

### SVG Generation Problems

**Problem**: No SVG file is generated, but no error is shown
**Solution**: Check that `src/pypgsvg.py` is not empty and contains the proper entry point

### Test Failures

**Problem**: Browser tests fail to find elements
**Solution**: Ensure the web server is running and the SVG file exists:
```bash
python3 -m http.server 8000 &
ls -la Samples/complex_schema.svg
```

### JavaScript Errors

**Problem**: Interactive features don't work in the SVG
**Solution**: Check the browser console for errors and verify that `svg_interactivity.js` is properly embedded

## Advanced Tips

### Debugging JavaScript in SVG

1. Open the SVG file directly in a browser
2. Use browser developer tools to inspect the embedded JavaScript
3. Check the console for errors
4. Use `console.log()` for debugging (temporarily)

### Working with Large Database Schemas

1. Test with the provided `complex_schema.dump` sample
2. Be aware of performance implications with very large schemas
3. Consider memory usage when processing many tables

### Extending Functionality

1. Follow the existing patterns in `erd_generator.py`
2. Add corresponding tests in `tests/browser/`
3. Update the JavaScript if adding new interactive features
4. Document new command-line options in the help text

## Getting Help

1. **Read the code**: The codebase is well-structured and documented
2. **Check existing tests**: They show how features are expected to work
3. **Use the agent workflow**: Let the automated testing catch issues early
4. **Refer to `CONTRIBUTING.md`**: For the structured development process

## Useful Resources

- **Graphviz documentation**: For understanding the underlying diagram generation
- **Playwright documentation**: For writing and debugging browser tests
- **PostgreSQL documentation**: For understanding dump file formats
- **SVG specification**: For working with SVG elements and JavaScript

Remember: The goal is to maintain a robust, automated workflow that produces high-quality, interactive ERD diagrams from PostgreSQL database dumps.
