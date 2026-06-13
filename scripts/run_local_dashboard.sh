#!/bin/bash
# Quick start script for local dashboard
# Runs all stages and starts the dashboard

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=" | tr -d '\n' | head -c 70
echo ""
echo "🚀 Local OANDA Dashboard - Quick Start"
echo "=" | tr -d '\n' | head -c 70
echo ""
echo ""

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found"
    exit 1
fi

# Stage 1: Pull transactions
echo "📥 Stage 1: Pulling OANDA transactions..."
python3 scripts/local_oanda_trade_pull.py || {
    echo "❌ Stage 1 failed"
    exit 1
}

# Stage 2: Reconstruct trades
echo ""
echo "🔧 Stage 2: Reconstructing trades..."
python3 -m src.analytics.trade_rebuilder || {
    echo "❌ Stage 2 failed"
    exit 1
}

# Stage 3: Compute stats
echo ""
echo "📊 Stage 3: Computing statistics..."
python3 -m src.analytics.stats_engine || {
    echo "❌ Stage 3 failed"
    exit 1
}

echo ""
echo "✅ All stages complete!"
echo ""
echo "To start the dashboard:"
echo "  Terminal 1: python3 dashboard/api_local.py"
echo "  Terminal 2: cd frontend/fxg-dashboard && npm run dev"
echo ""
