#!/bin/bash
# Start Trading Analytics System
# This script starts both the main trading system and analytics dashboard

set -e

echo "=========================================="
echo "STARTING TRADING ANALYTICS SYSTEM"
echo "=========================================="

# Kill any existing processes on ports 8080 and 8081
echo "🔄 Cleaning up existing processes..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
lsof -ti:8081 | xargs kill -9 2>/dev/null || true

# Wait a moment for ports to be released
sleep 2

# Start main trading system in background
echo "🚀 Starting main trading system on port 8080..."
cd /Users/mac/quant_system_clean/google-cloud-trading-system
python3 main.py > main.log 2>&1 &

# Wait for main system to start
sleep 10

# Check if main system is running
if lsof -i :8080 > /dev/null 2>&1; then
    echo "✅ Main trading system started successfully"
else
    echo "❌ Failed to start main trading system"
    echo "Check main.log for details"
    exit 1
fi

# Check if analytics dashboard is running
if lsof -i :8081 > /dev/null 2>&1; then
    echo "✅ Analytics dashboard started successfully"
else
    echo "⚠️ Analytics dashboard not detected on port 8081"
    echo "It should start automatically with main.py"
fi

echo ""
echo "=========================================="
echo "✅ SYSTEM STARTED SUCCESSFULLY!"
echo "=========================================="
echo ""
echo "🌐 Main Dashboard:      http://localhost:8080"
echo "📊 Analytics Dashboard: http://localhost:8081"
echo ""
echo "📋 Available Analytics Pages:"
echo "   - Overview:           http://localhost:8081/"
echo "   - Strategy Detail:    http://localhost:8081/strategy/[strategy_id]"
echo "   - Trade History:      http://localhost:8081/trades"
echo "   - Strategy Compare:   http://localhost:8081/comparison"
echo "   - Charts:             http://localhost:8081/charts"
echo ""
echo "🔧 API Endpoints:"
echo "   - Health Check:       http://localhost:8081/api/health"
echo "   - All Strategies:     http://localhost:8081/api/strategies"
echo "   - Database Stats:     http://localhost:8081/api/database/stats"
echo ""
echo "📝 Logs:"
echo "   - Main System:        tail -f main.log"
echo "   - Analytics:          Check system logs"
echo ""
echo "🛑 To stop:"
echo "   pkill -f 'python3 main.py'"
echo "   or Ctrl+C in this terminal"
echo ""

# Show status
echo "📊 Current Status:"
echo "   Main System (8080): $(curl -s http://localhost:8080/ | grep -o '<title>[^<]*' | sed 's/<title>//' || echo 'Running')"
echo "   Analytics (8081):   $(curl -s http://localhost:8081/api/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo 'Running')"
echo ""

# Keep script running and show logs
echo "📋 Following logs (Ctrl+C to exit):"
echo "=========================================="
tail -f main.log
