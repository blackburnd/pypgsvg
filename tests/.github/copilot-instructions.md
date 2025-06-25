<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Python ERD Generator Project Instructions

This project contains a Python application that parses SQL dump files and generates Entity Relationship Diagrams (ERDs) using Graphviz.

## Code Style and Patterns
- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Write comprehensive docstrings for all functions and classes
- Use pytest for testing with proper fixtures and parametrization
- Include edge case testing and error handling tests

## Testing Guidelines
- Test all functions with multiple scenarios including edge cases
- Mock external dependencies (file I/O, Graphviz rendering)
- Use parametrized tests for testing multiple inputs
- Aim for high code coverage (>90%)
- Test error conditions and exception handling

## Project Structure
- Main code in `create_graph.py`
- Tests in `tests/` directory
- Use pytest fixtures for common test data
- Separate unit tests and integration tests
