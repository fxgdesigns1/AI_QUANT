#!/bin/bash
"""
WebSocket Testing Script
Runs comprehensive websocket tests with Playwright
"""

echo "🧪 WebSocket Testing with Playwright"
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check if Playwright is installed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "📦 Installing Playwright..."
    pip install playwright
    playwright install chromium
fi

# Check if socketio is installed
if ! python3 -c "import socketio" 2>/dev/null; then
    echo "📦 Installing python-socketio..."
    pip install python-socketio[client]
fi

# Check if requests is installed
if ! python3 -c "import requests" 2>/dev/null; then
    echo "📦 Installing requests..."
    pip install requests
fi

echo "✅ Dependencies checked"

# Run the comprehensive test
echo "🚀 Starting comprehensive WebSocket tests..."
python3 playwright_websocket_test.py

echo "🏁 Testing complete!"
