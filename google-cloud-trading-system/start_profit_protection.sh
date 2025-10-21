#!/bin/bash
# Start Profit Protection System
# Actively manages trades to secure profits and prevent give-backs

echo "🛡️ Starting Profit Protection System..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will protect all open trades by:"
echo "  • Moving stops to breakeven after 15 pips profit"
echo "  • Taking 50% profit at 20 pips"
echo "  • Trailing stops after 25 pips (15 pips trailing distance)"
echo "  • Time-based exits after 4 hours"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to directory
cd "$(dirname "$0")"

# Load environment
if [ -f "oanda_config.env" ]; then
    source oanda_config.env
else
    echo "❌ Error: oanda_config.env not found"
    exit 1
fi

# Create logs directory
mkdir -p logs

echo "🔄 Starting profit protector for all accounts..."
echo ""

# Start for each account (run in separate processes)
for account in "101-004-30719775-006" "101-004-30719775-007" "101-004-30719775-008" "101-004-30719775-010" "101-004-30719775-011"
do
    echo "Starting protection for account $account..."
    OANDA_API_KEY=$OANDA_API_KEY OANDA_ACCOUNT_ID=$account OANDA_ENVIRONMENT=$OANDA_ENVIRONMENT nohup python3 -m src.core.profit_protector > logs/profit_protector_${account: -3}.log 2>&1 &
    LAST_PID=$!
    echo "  PID: $LAST_PID"
    sleep 1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Profit Protection ACTIVE for all accounts!"
echo ""
echo "What's happening now:"
echo "  🛡️ Checking trades every 30 seconds"
echo "  📊 Breakeven after +15 pips"
echo "  💰 Partial profit at +20 pips (50%)"
echo "  📈 Trailing after +25 pips"
echo ""
echo "Monitor logs:"
echo "  tail -f logs/profit_protector_*.log"
echo ""
echo "Stop all:"
echo "  pkill -f profit_protector"
echo ""

