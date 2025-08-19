#!/bin/bash

# Quick fix for current session
echo "🔧 Quick fixing current environment..."

# Install Graphviz
sudo apt-get update
sudo apt-get install -y graphviz

# Verify installation
which dot && echo "✅ Graphviz is now available" || echo "❌ Still having issues"

# Test pypgsvg
echo "🧪 Testing pypgsvg..."
python -m src.pypgsvg --help > /dev/null 2>&1 && echo "✅ pypgsvg is working" || echo "❌ pypgsvg issues"

echo "🌐 Starting HTTP server on port 8080..."
echo "📂 Files will be available at: https://studious-giggle-x4rgr545j72v4q4-8080.app.github.dev/"
python -m http.server 8080 --bind 0.0.0.0 &
SERVER_PID=$!
echo "🔌 HTTP server started with PID: $SERVER_PID"
echo "🛑 To stop server: kill $SERVER_PID"
