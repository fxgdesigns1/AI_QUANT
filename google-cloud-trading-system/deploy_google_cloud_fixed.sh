#!/bin/bash
"""
Deploy Fixed Dashboard to Google Cloud
Updates the Google Cloud deployment with fully integrated dashboard
"""

echo "🚀 Deploying Fixed Dashboard to Google Cloud"
echo "============================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run from the google-cloud-trading-system directory"
    exit 1
fi

echo "✅ Found main.py - proceeding with Google Cloud deployment"

# Check if gcloud is installed and configured
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install Google Cloud SDK"
    exit 1
fi

echo "✅ Google Cloud SDK found"

# Check if we're logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: Not logged in to Google Cloud. Please run 'gcloud auth login'"
    exit 1
fi

echo "✅ Google Cloud authentication confirmed"

# Set the project
PROJECT_ID="ai-quant-trading"
gcloud config set project $PROJECT_ID
echo "✅ Project set to: $PROJECT_ID"

# Check if the main.py has the WebSocket integration
if ! grep -q "flask_socketio" main.py; then
    echo "❌ Error: main.py doesn't have WebSocket integration. Please update it first."
    exit 1
fi

echo "✅ WebSocket integration found in main.py"

# Check if requirements.txt has flask-socketio
if ! grep -q "flask-socketio" requirements.txt; then
    echo "❌ Error: requirements.txt missing flask-socketio"
    exit 1
fi

echo "✅ flask-socketio found in requirements.txt"

# Deploy to Google Cloud App Engine
echo "🌐 Deploying to Google Cloud App Engine..."
echo "This may take a few minutes..."

gcloud app deploy --quiet --version=$(date +%Y%m%d-%H%M%S)

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo ""
    echo "🌐 Your dashboard is now available at:"
    echo "https://ai-quant-trading.uc.r.appspot.com/dashboard"
    echo ""
    echo "🔧 Features now working:"
    echo "✅ WebSocket real-time updates"
    echo "✅ News integration with countdown"
    echo "✅ AI assistant chat"
    echo "✅ Trading signals display"
    echo "✅ Risk management monitoring"
    echo ""
    echo "🧪 Run the Playwright test to verify:"
    echo "python3 test_dashboard_playwright.py"
else
    echo "❌ Deployment failed. Please check the logs above."
    exit 1
fi
