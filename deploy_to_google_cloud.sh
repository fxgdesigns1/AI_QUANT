#!/bin/bash
# Deploy trading system to Google Cloud

set -e

echo "🚀 Deploying to Google Cloud..."

cd /workspace/google-cloud-trading-system

# Check if gcloud is available
if ! command -v gcloud &> /dev/null; then
    echo "⚠️ gcloud CLI not found. Installing..."
    # Install instructions would go here
    echo "Please install gcloud CLI manually"
    exit 1
fi

# Set project
gcloud config set project ai-quant-trading

# Deploy to App Engine
echo "📦 Deploying to App Engine..."
gcloud app deploy config/app.yaml --quiet

echo "✅ Deployment complete!"
echo "📊 Dashboard should be available at: https://ai-quant-trading.appspot.com"
