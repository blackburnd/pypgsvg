##!/usr/bin/env bash

# Test runner script for pypgsvg
# This script ensures proper environment setup before running tests

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}==== pypgsvg Test Runner ====${NC}"

# 1. Set up virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}Virtual environment created.${NC}"
else
    echo -e "${GREEN}Using existing virtual environment.${NC}"
fi

# 2. Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
. venv/bin/activate

# 3. Install dependencies
echo -e "${YELLOW}Installing package and test dependencies...${NC}"
pip install -e ".[test]"
echo -e "${GREEN}Dependencies installed.${NC}"

# 4. Determine test type from arguments
TEST_TYPE="unit"  # Default to unit tests
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --browser|--playwright|--functional)
            TEST_TYPE="browser"
            shift
            ;;
        --unit|--pytest)
            TEST_TYPE="unit"
            shift
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# 5. Run the appropriate test suite
if [ "$TEST_TYPE" = "unit" ]; then
    echo -e "${YELLOW}Running Python unit tests...${NC}"
    python3 -m pytest tests/tests/ -v $EXTRA_ARGS
    TEST_EXIT_CODE=$?
elif [ "$TEST_TYPE" = "browser" ]; then
    echo -e "${YELLOW}Running browser functional tests...${NC}"
    # Check if Playwright browsers are installed
    if ! npx playwright --version &> /dev/null; then
        echo -e "${YELLOW}Installing Playwright browsers...${NC}"
        npx playwright install
    fi
    npx playwright test tests/browser/ $EXTRA_ARGS
    TEST_EXIT_CODE=$?
else
    echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
    exit 1
fi

# 6. Report result
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Tests failed with exit code $TEST_EXIT_CODE${NC}"
fi

exit $TEST_EXIT_CODE
