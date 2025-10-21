#!/bin/bash
# Google Cloud Deployment Script with Calibrated Parameters
# This script deploys the trading system to Google Cloud with calibrated parameters

echo "🚀 Deploying calibrated trading system to Google Cloud"
echo "============================================================"

# Set environment variables for calibration
export PRIMARY_MAX_PORTFOLIO_RISK=0.75
export GOLD_MAX_PORTFOLIO_RISK=0.75
export ALPHA_MAX_PORTFOLIO_RISK=0.75
export FORCED_TRADING_MODE=enabled
export POSITION_SIZE_MULTIPLIER=0.5
export MIN_CONFIDENCE_THRESHOLD=0.5
export MIN_TRADES_TODAY=2

# Deploy to Google Cloud
echo "📊 Deploying to project: ai-quant-trading"
gcloud app deploy app.yaml --project=ai-quant-trading --quiet

# Check deployment status
echo "🔍 Checking deployment status..."
gcloud app services describe default --project=ai-quant-trading

echo "============================================================"
echo "✅ Deployment complete"
echo "📊 Visit your Google Cloud console to monitor the application"
echo "🔗 https://console.cloud.google.com/appengine?project=ai-quant-trading"
echo "============================================================"
