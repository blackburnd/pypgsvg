# Contributing to pypgsvg

This document outlines the automated development and testing workflow for the `pypgsvg` repository. The process is managed by a team of specialized AI agents to ensure code quality, reliability, and a fully automated, hands-off experience for the user.

## Agent Team Structure

The project is managed by a team of four specialized agents, each with a distinct role:

1.  **Project Manager Agent:**
    *   **Responsibilities:** Defines and codifies the overall development workflow, manages the agent team structure, and ensures the entire process is followed correctly. This agent is responsible for creating and maintaining this `CONTRIBUTING.md` file.

2.  **Development Agent:**
    *   **Responsibilities:** Writes, fixes, and refactors code based on user requests and feedback. This agent is responsible for implementing new features and resolving bugs.

3.  **QA Agent:**
    *   **Responsibilities:** Manages and executes the automated testing pipeline. After every code change, this agent runs the full suite of Python and Playwright tests to verify the changes and prevent regressions.

4.  **Feedback Agent:**
    *   **Responsibilities:** Provides clear, actionable feedback on all generated outputs. This agent is responsible for ensuring that the final result meets all user requirements and that the automated workflow is functioning as expected.

## Automated Development Workflow

The standard workflow for all changes is as follows:

1.  **Code Change:** The **Development Agent** implements the required code changes.
2.  **SVG Generation:** The `complex_schema.svg` file is automatically regenerated to reflect the changes.
3.  **Automated Testing:** The **QA Agent** immediately runs all browser tests against the newly generated SVG to ensure there are no regressions or new issues.
4.  **Feedback and Verification:** The **Feedback Agent** reviews the results and provides final verification.

This entire process is fully automated and requires no manual intervention from the user. The goal is to create a seamless, reliable, and efficient development pipeline.
