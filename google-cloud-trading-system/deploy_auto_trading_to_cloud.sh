#!/bin/bash

echo "=============================================================="
echo "🚀 DEPLOYING AUTO-TRADING SYSTEM TO GOOGLE CLOUD"
echo "=============================================================="
echo ""

# Set version name
VERSION="auto-trading-fixed-$(date +%Y%m%d-%H%M%S)"

echo "📦 Deployment Version: $VERSION"
echo ""
echo "🔧 What's being deployed:"
echo "   ✅ Fixed GBP strategies (with scan_for_signal method)"
echo "   ✅ Fixed auto-trading scanner"
echo "   ✅ All 3 account configs (006, 007, 008)"
echo ""
echo "⏳ Starting deployment (this takes 3-5 minutes)..."
echo ""

# Deploy to App Engine
gcloud app deploy --quiet --version="$VERSION" --promote

if [ $? -eq 0 ]; then
    echo ""
    echo "=============================================================="
    echo "✅ DEPLOYMENT SUCCESSFUL!"
    echo "=============================================================="
    echo ""
    echo "🌐 Your Auto-Trading System is now live at:"
    echo "   https://ai-quant-trading.uc.r.appspot.com"
    echo ""
    echo "🤖 Next: Setting up Cloud Scheduler for auto-trading..."
    echo "   (Creating scheduled job to scan market every 5 minutes)"
    echo ""
else
    echo ""
    echo "❌ Deployment failed. Check errors above."
    exit 1
fi

