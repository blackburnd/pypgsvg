#!/usr/bin/env bash

# Release script for pypgsvg
# This script handles version bumping and triggering PyPI release via GitHub Actions

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if we're on a clean git state
check_git_clean() {
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Git working directory is not clean. Please commit or stash changes."
        git status --short
        exit 1
    fi
    print_success "Git working directory is clean"
}

# Get current version from pyproject.toml
get_current_version() {
    grep -m 1 'version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
}

# Validate version format (semantic versioning)
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $version"
        echo "Version must be in format: MAJOR.MINOR.PATCH (e.g., 1.2.3)"
        exit 1
    fi
}

# Update version in files
update_version() {
    local new_version=$1

    print_info "Updating version to $new_version..."

    # Update pyproject.toml
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    else
        # Linux
        sed -i "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    fi

    # Update setup.py
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/version=\".*\"/version=\"$new_version\"/" setup.py
    else
        sed -i "s/version=\".*\"/version=\"$new_version\"/" setup.py
    fi

    print_success "Version updated in pyproject.toml and setup.py"
}

# Run tests before releasing
run_tests() {
    print_info "Running tests..."
    if ./run-tests.sh; then
        print_success "All tests passed"
    else
        print_error "Tests failed. Please fix before releasing."
        exit 1
    fi
}

# Create git tag and push
create_and_push_tag() {
    local version=$1
    local tag="v$version"

    print_info "Creating git tag $tag..."

    # Commit version changes
    git add pyproject.toml setup.py
    git commit -m "Release version $version"

    # Create annotated tag
    git tag -a "$tag" -m "Release version $version"

    print_success "Created tag $tag"

    # Show what will be pushed
    echo ""
    echo "The following will be pushed:"
    echo "  - Commit: $(git log -1 --oneline)"
    echo "  - Tag: $tag"
    echo ""

    read -p "Push to origin and trigger PyPI release? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main
        git push origin "$tag"
        print_success "Pushed to origin. GitHub Actions will now:"
        echo "  1. Build the package"
        echo "  2. Run tests on the built package"
        echo "  3. Publish to TestPyPI"
        echo "  4. Publish to PyPI (if tag was pushed)"
        echo ""
        echo "Monitor the workflow at:"
        echo "  https://github.com/blackburnd/pypgsvg/actions"
    else
        print_info "Push cancelled. You can push manually later with:"
        echo "  git push origin main"
        echo "  git push origin $tag"
    fi
}

# Main release workflow
main() {
    print_header "pypgsvg Release Script"

    # Check prerequisites
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi

    # Get current version
    current_version=$(get_current_version)
    echo "Current version: $current_version"
    echo ""

    # Get new version
    if [ -z "$1" ]; then
        echo "Usage: ./release.sh <new_version> [--skip-tests]"
        echo ""
        echo "Example: ./release.sh 1.2.0"
        echo ""
        echo "Current version: $current_version"
        echo ""
        echo "Options:"
        echo "  --skip-tests    Skip running tests before release"
        exit 1
    fi

    new_version=$1
    skip_tests=false

    if [ "$2" = "--skip-tests" ]; then
        skip_tests=true
        print_info "Skipping tests (--skip-tests flag provided)"
    fi

    # Validate version
    validate_version "$new_version"

    if [ "$new_version" = "$current_version" ]; then
        print_error "New version ($new_version) is the same as current version"
        exit 1
    fi

    echo "Release summary:"
    echo "  Current version: $current_version"
    echo "  New version:     $new_version"
    echo ""

    read -p "Continue with release? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Release cancelled."
        exit 0
    fi

    # Perform release steps
    check_git_clean

    if [ "$skip_tests" = false ]; then
        run_tests
    fi

    update_version "$new_version"
    create_and_push_tag "$new_version"

    print_header "Release Complete!"
    echo "Next steps:"
    echo "  1. Monitor GitHub Actions: https://github.com/blackburnd/pypgsvg/actions"
    echo "  2. Verify TestPyPI: https://test.pypi.org/project/pypgsvg/"
    echo "  3. Verify PyPI: https://pypi.org/project/pypgsvg/"
    echo "  4. Create GitHub Release with release notes"
}

# Run main function
main "$@"
