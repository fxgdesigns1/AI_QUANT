#!/bin/bash

echo "📊 Starting AI Trading Dashboard with TradingView Integration"
echo "============================================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "dashboard/advanced_dashboard.py" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

echo "✅ Python3 found"
echo "✅ Dashboard files found"

# Start the dashboard
echo ""
echo "🚀 Starting Advanced Dashboard with TradingView..."
echo "📍 Dashboard will be available at: http://localhost:8080"
echo "📊 TradingView charts will be integrated automatically"
echo ""
echo "🎯 Features available:"
echo "   • Live TradingView charts with real-time data"
echo "   • Symbol selector for major pairs and crypto"
echo "   • Timeframe switching (1H, 4H, 1D)"
echo "   • Technical indicators (RSI, MACD, EMA)"
echo "   • Dark theme matching your dashboard"
echo "   • London timezone for UK trading hours"
echo ""
echo "🔄 Starting dashboard in 3 seconds..."
sleep 3

# Start the dashboard
cd dashboard
python3 advanced_dashboard.py
