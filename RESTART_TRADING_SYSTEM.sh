#!/bin/bash
# RESTART TRADING SYSTEM - Complete cleanup and restart
# This script stops the running system, clears cache, and restarts

echo "🛑 Stopping trading system..."
pkill -f "python.*main.py"
pkill -f "python.*google-cloud-trading-system"

echo "⏳ Waiting for clean shutdown..."
sleep 5

echo "🧹 Clearing Python cache..."
cd /Users/mac/quant_system_clean/google-cloud-trading-system
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

echo "🚀 Restarting system..."
nohup python3 main.py > logs/trading_system.log 2>&1 &

echo "✅ System restarted!"
echo "📊 Checking logs in 3 seconds..."
sleep 3

echo ""
echo "==================== LAST 30 LINES OF LOG ===================="
tail -30 logs/trading_system.log
echo ""
echo "==================== END OF LOG ===================="
echo ""
echo "💡 To follow live logs, run: tail -f google-cloud-trading-system/logs/trading_system.log"



