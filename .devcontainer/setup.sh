#!/bin/bash

# Setup script for pypgsvg development environment
# This runs automatically when the codespace is created

echo "🚀 Setting up pypgsvg development environment..."

# Update package list
sudo apt-get update

# Install Graphviz (required for pypgsvg)
echo "📦 Installing Graphviz..."
sudo apt-get install -y graphviz graphviz-dev

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --upgrade pip
pip install -e .

# Install development dependencies if they exist
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Install testing dependencies
pip install pytest pytest-cov

# Create test directories if they don't exist
mkdir -p test_output
mkdir -p Samples

# Make sure dot is in PATH
echo "🔍 Verifying Graphviz installation..."
which dot && echo "✅ Graphviz installed successfully" || echo "❌ Graphviz installation failed"

# Test pypgsvg installation
echo "🧪 Testing pypgsvg installation..."
python -c "from src.pypgsvg.db_parser import parse_sql_dump; print('✅ pypgsvg imports successfully')" || echo "❌ pypgsvg import failed"

echo "🎉 Development environment setup complete!"
echo "📝 You can now run: python -m src.pypgsvg Samples/complex_schema.dump --output test"
echo "🌐 HTTP server can be started with: python -m http.server 8080"
