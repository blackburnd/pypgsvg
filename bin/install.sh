#!/usr/bin/env bash

# Installation script for pypgsvg development environment
# This script installs all prerequisites needed to run tests and develop pypgsvg

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian)
                echo "debian"
                ;;
            centos|rhel|fedora)
                echo "rhel"
                ;;
            *)
                echo "unknown"
                ;;
        esac
    else
        echo "unknown"
    fi
}

# Check if running as root (for package installation)
check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        return 0
    elif sudo -n true 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Install Graphviz
install_graphviz() {
    local os=$1

    if command_exists dot; then
        print_success "Graphviz already installed ($(dot -V 2>&1))"
        return 0
    fi

    print_header "Installing Graphviz"

    case "$os" in
        macos)
            if ! command_exists brew; then
                print_error "Homebrew not found. Please install Homebrew first:"
                echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                return 1
            fi
            brew install graphviz
            ;;
        debian)
            sudo apt-get update
            sudo apt-get install -y graphviz
            ;;
        rhel)
            sudo yum install -y graphviz
            ;;
        *)
            print_error "Unsupported OS. Please install Graphviz manually:"
            echo "  https://graphviz.org/download/"
            return 1
            ;;
    esac

    print_success "Graphviz installed successfully"
}

# Install Node.js and npm
install_nodejs() {
    local os=$1

    if command_exists node && command_exists npm; then
        print_success "Node.js already installed ($(node --version), npm $(npm --version))"
        return 0
    fi

    print_header "Installing Node.js and npm"

    case "$os" in
        macos)
            if ! command_exists brew; then
                print_error "Homebrew not found. Please install Homebrew first."
                return 1
            fi
            brew install node
            ;;
        debian)
            sudo apt-get update
            sudo apt-get install -y nodejs npm
            ;;
        rhel)
            sudo yum install -y nodejs npm
            ;;
        *)
            print_error "Unsupported OS. Please install Node.js manually:"
            echo "  https://nodejs.org/"
            return 1
            ;;
    esac

    print_success "Node.js and npm installed successfully"
}

# Install Python dependencies
install_python_deps() {
    print_header "Installing Python Dependencies"

    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or later."
        return 1
    fi

    local python_version=$(python3 --version | cut -d' ' -f2)
    print_success "Python $python_version found"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate

    # Upgrade pip
    echo "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1

    # Install package in editable mode with test dependencies
    echo "Installing pypgsvg with test dependencies..."
    pip install -e ".[test]" >/dev/null 2>&1

    print_success "Python dependencies installed"
}

# Install Playwright browsers
install_playwright_browsers() {
    print_header "Installing Playwright Browsers"

    if ! command_exists npx; then
        print_error "npm/npx not found. Cannot install Playwright browsers."
        return 1
    fi

    echo "Downloading browser binaries (this may take a few minutes)..."
    npx playwright install

    print_success "Playwright browsers installed"
}

# Verify installation
verify_installation() {
    print_header "Verifying Installation"

    local all_good=true

    # Check Graphviz
    if command_exists dot; then
        print_success "Graphviz: $(dot -V 2>&1)"
    else
        print_error "Graphviz: Not found"
        all_good=false
    fi

    # Check Node.js
    if command_exists node; then
        print_success "Node.js: $(node --version)"
    else
        print_warning "Node.js: Not found (needed for browser tests only)"
    fi

    # Check npm
    if command_exists npm; then
        print_success "npm: $(npm --version)"
    else
        print_warning "npm: Not found (needed for browser tests only)"
    fi

    # Check Python packages
    if source venv/bin/activate 2>/dev/null && python3 -c "import pytest, playwright" 2>/dev/null; then
        print_success "Python packages: Installed"
    else
        print_error "Python packages: Not properly installed"
        all_good=false
    fi

    echo ""
    if [ "$all_good" = true ]; then
        print_success "All prerequisites installed successfully!"
        echo ""
        echo "Next steps:"
        echo "  1. Activate virtual environment: source venv/bin/activate"
        echo "  2. Run unit tests: ./run-tests.sh"
        echo "  3. Run browser tests: ./run-tests.sh --browser"
    else
        print_error "Some prerequisites are missing. Please check the errors above."
        return 1
    fi
}

# Main installation flow
main() {
    print_header "pypgsvg Development Environment Setup"

    echo "This script will install the following prerequisites:"
    echo "  • Graphviz (system package)"
    echo "  • Node.js and npm (system packages)"
    echo "  • Python dependencies (via pip in virtual environment)"
    echo "  • Playwright browser binaries"
    echo ""

    # Detect OS
    OS=$(detect_os)
    if [ "$OS" = "unknown" ]; then
        print_error "Unsupported operating system"
        echo "Please install prerequisites manually:"
        echo "  1. Graphviz: https://graphviz.org/download/"
        echo "  2. Node.js: https://nodejs.org/"
        echo "  3. Run: pip install -e '.[test]'"
        echo "  4. Run: npx playwright install"
        exit 1
    fi

    echo "Detected OS: $OS"
    echo ""

    # Check if we need sudo for system packages
    if [ "$OS" != "macos" ] && ! check_sudo; then
        print_warning "System package installation may require sudo password"
        echo ""
    fi

    read -p "Continue with installation? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi

    # Install prerequisites
    install_graphviz "$OS" || print_warning "Graphviz installation had issues"
    install_nodejs "$OS" || print_warning "Node.js installation had issues"
    install_python_deps || { print_error "Python dependency installation failed"; exit 1; }
    install_playwright_browsers || print_warning "Playwright browser installation had issues"

    # Verify everything
    verify_installation
}

# Run main function
main "$@"
