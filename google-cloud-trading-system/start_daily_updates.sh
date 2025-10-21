#!/bin/bash
# Start Daily Telegram Updates - London Time
# Morning briefings at 6:00 AM and evening summaries at 9:30 PM

echo "🚀 Starting Daily Telegram Updates System..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 Telegram Notifications Enabled:"
echo "   • Morning briefing: 6:00 AM London"
echo "   • Evening summary: 9:30 PM London"
echo "   • Trade alerts: Real-time during trading hours"
echo "   • Hourly monitoring: 8am-9pm London"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to the correct directory
cd "$(dirname "$0")"

# Check if .env file exists
if [ ! -f "oanda_config.env" ]; then
    echo "❌ Error: oanda_config.env not found"
    echo "Please ensure your OANDA API key and Telegram credentials are configured"
    exit 1
fi

# Load environment variables
source oanda_config.env

# Verify Telegram configuration
if [ -z "$TELEGRAM_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "❌ Error: Telegram credentials not configured"
    echo "Please set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in oanda_config.env"
    exit 1
fi

echo "✅ Configuration verified"
echo "   Token: ${TELEGRAM_TOKEN:0:10}..."
echo "   Chat ID: $TELEGRAM_CHAT_ID"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

echo "🔄 Starting daily monitor..."
echo ""

# Start the daily monitor in the background
nohup python3 -m src.core.daily_monitor > logs/daily_monitor.log 2>&1 &

# Get the process ID
MONITOR_PID=$!

echo "✅ Daily monitor started!"
echo "   Process ID: $MONITOR_PID"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Schedule Active (London Time):"
echo "   🌅 06:00 - Morning briefing"
echo "   🔍 08:00-21:00 - Hourly monitoring"
echo "   🌙 21:30 - Evening summary"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 You'll receive:"
echo "   • Portfolio status every morning at 6am"
echo "   • Real-time trade alerts during trading"
echo "   • Daily summary every night at 9:30pm"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 To check status:"
echo "   tail -f logs/daily_monitor.log"
echo ""
echo "💡 To stop:"
echo "   kill $MONITOR_PID"
echo ""
echo "✅ All set! Your first morning briefing arrives at 6:00 AM tomorrow!"
echo ""



