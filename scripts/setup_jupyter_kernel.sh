#!/bin/bash

# Setup Jupyter kernel for pypgsvg
# This script installs the pypgsvg kernel for Jupyter

set -e

echo "Setting up Jupyter kernel for pypgsvg..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Virtual environment is not activated"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

# Install the package with test dependencies (includes Jupyter)
echo "Installing pypgsvg with Jupyter dependencies..."
pip install -e ".[test]"

# Install the Jupyter kernel
echo "Installing Jupyter kernel..."
python -m ipykernel install --user --name=pypgsvg --display-name="pypgsvg - PostgreSQL ERD Generator"

echo ""
echo "Jupyter kernel installed successfully!"
echo ""
echo "To start JupyterLab, run:"
echo "  jupyter lab"
echo ""
echo "To start Jupyter Notebook, run:"
echo "  jupyter notebook"
echo ""
echo "The demo notebook is located at: examples/pypgsvg_demo.ipynb"
