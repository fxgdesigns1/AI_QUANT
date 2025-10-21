#!/bin/bash
# Deploy Google Cloud Trading System with News Integration
# This script deploys the enhanced trading system with news APIs

echo "🚀 Deploying enhanced trading system with news integration to Google Cloud"
echo "=========================================================================="

# Set environment variables for news integration
export NEWS_TRADING_ENABLED=true
export HIGH_IMPACT_PAUSE=true
export NEGATIVE_SENTIMENT_THRESHOLD=-0.3
export POSITIVE_SENTIMENT_THRESHOLD=0.3
export NEWS_CONFIDENCE_THRESHOLD=0.5

# Deploy to Google Cloud
echo "📊 Deploying to project: ai-quant-trading"
gcloud app deploy app.yaml --project=ai-quant-trading --quiet

# Check deployment status
echo "🔍 Checking deployment status..."
gcloud app services describe default --project=ai-quant-trading

echo "=========================================================================="
echo "✅ Enhanced deployment complete with news integration"
echo "📊 Visit your Google Cloud console to monitor the application"
echo "🔗 https://console.cloud.google.com/appengine?project=ai-quant-trading"
echo "📰 News APIs are now integrated and running 24/7"
echo "=========================================================================="
