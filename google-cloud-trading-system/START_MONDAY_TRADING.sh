#!/bin/bash

echo "=============================================================="
echo "🚀 STARTING AUTO-TRADING FOR MONDAY MARKET OPEN"
echo "=============================================================="
echo ""
echo "📊 Your 3 GBP Strategy Accounts:"
echo "   Account ...008 (Strategy #1 - Sharpe 35.90)"
echo "   Account ...007 (Strategy #2 - Sharpe 35.55)"
echo "   Account ...006 (Strategy #3 - Sharpe 35.18)"
echo ""
echo "⚙️  Scanner Settings:"
echo "   - Scans every 5 minutes"
echo "   - Max 5 positions per account"
echo "   - GBP/USD on 5-minute timeframe"
echo ""
echo "Starting in 3 seconds..."
sleep 3

cd /Users/mac/quant_system_clean/google-cloud-trading-system

# Start scanner in background
nohup python3 auto_trade_gbp_strategies.py > monday_trading.log 2>&1 &
SCANNER_PID=$!
echo $SCANNER_PID > scanner.pid

sleep 2

echo ""
echo "✅ Auto-trading scanner STARTED!"
echo "   PID: $SCANNER_PID"
echo ""
echo "📊 Monitor real-time activity:"
echo "   tail -f monday_trading.log"
echo ""
echo "⏹️  To stop scanner:"
echo "   kill \$(cat scanner.pid)"
echo ""
echo "=============================================================="
