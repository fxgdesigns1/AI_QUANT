#!/bin/bash
# Deploy Momentum Strategy Fixes - Elite Trade Selection
# Date: October 16, 2025

echo "🚀 DEPLOYING MOMENTUM STRATEGY FIXES"
echo "===================================="
echo "Time: $(date)"
echo ""

# Set project
PROJECT_ID="ai-quant-trading"
VERSION="momentum-elite-oct16"

echo "📦 Files to deploy:"
echo "  ✅ src/strategies/momentum_trading.py (quality scoring)"
echo "  ✅ src/strategies/momentum_trading_optimized.py (parameter fixes)"
echo "  ✅ strategy_config.yaml (strict config)"
echo ""

echo "🔍 Verifying files exist..."
if [ ! -f "src/strategies/momentum_trading.py" ]; then
    echo "❌ momentum_trading.py not found!"
    exit 1
fi

if [ ! -f "src/strategies/momentum_trading_optimized.py" ]; then
    echo "❌ momentum_trading_optimized.py not found!"
    exit 1
fi

if [ ! -f "strategy_config.yaml" ]; then
    echo "❌ strategy_config.yaml not found!"
    exit 1
fi

echo "✅ All files verified"
echo ""

echo "🚀 Deploying to Google Cloud..."
echo "Project: $PROJECT_ID"
echo "Version: $VERSION"
echo ""

# Deploy with gcloud
gcloud app deploy app.yaml \
    --version=$VERSION \
    --promote \
    --quiet \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ DEPLOYMENT SUCCESSFUL!"
    echo ""
    echo "📊 What was deployed:"
    echo "  ✅ Elite quality scoring (70/100 minimum)"
    echo "  ✅ Fixed impossible 40% momentum → 0.8%"
    echo "  ✅ Prime hours only (1-5pm London)"
    echo "  ✅ Max trades: 100 → 10/day"
    echo "  ✅ Confidence: 0.15 → 0.65 (4x stricter)"
    echo "  ✅ R:R ratio: 1:1.67 → 1:3"
    echo ""
    echo "📈 Expected improvements:"
    echo "  • Win rate: 27-36% → 55-65%"
    echo "  • Trades/day: ~100 → 3-10"
    echo "  • Quality: Random → Elite (70+ score)"
    echo ""
    echo "🔍 Checking logs..."
    gcloud app logs read --service=default --limit=30 --project=$PROJECT_ID
    
    echo ""
    echo "✅ MOMENTUM STRATEGY FIX DEPLOYED!"
    echo "🎯 Monitor for: 3-10 elite trades/day with quality scores 70+"
    
else
    echo ""
    echo "❌ DEPLOYMENT FAILED"
    echo "Checking error logs..."
    gcloud app logs read --service=default --limit=20 --project=$PROJECT_ID
    exit 1
fi








