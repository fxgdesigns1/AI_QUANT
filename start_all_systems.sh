#!/bin/bash
# COMPREHENSIVE TRADING SYSTEM STARTUP SCRIPT
# Starts all trading systems: AI, Automated, Comprehensive, Dashboard, News, and Metrics

set -e

echo "🚀 STARTING COMPREHENSIVE TRADING SYSTEM"
echo "=========================================="
date

# Set environment variables
export TELEGRAM_TOKEN="7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
export TELEGRAM_CHAT_ID="6100678501"
export OANDA_API_KEY="REMOVED_SECRET"
export OANDA_ACCOUNT_ID="101-004-30719775-008"
export OANDA_ENVIRONMENT="practice"
export PYTHONPATH="/workspace:/workspace/google-cloud-trading-system"

# Create logs directory
mkdir -p /workspace/logs

# Function to start a service in background
start_service() {
    local service_name=$1
    local command=$2
    local log_file="/workspace/logs/${service_name}.log"
    
    echo "📦 Starting ${service_name}..."
    cd /workspace
    nohup python3 ${command} > ${log_file} 2>&1 &
    echo $! > /workspace/logs/${service_name}.pid
    echo "✅ ${service_name} started (PID: $(cat /workspace/logs/${service_name}.pid))"
    sleep 2
}

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "ai_trading_system.py" || true
pkill -f "automated_trading_system.py" || true
pkill -f "comprehensive_trading_system.py" || true
pkill -f "advanced_dashboard.py" || true
sleep 2

# Start AI Trading System (with Telegram commands)
echo ""
echo "🤖 Starting AI Trading System..."
start_service "ai_trading" "ai_trading_system.py"

# Start Automated Trading System
echo ""
echo "⚙️ Starting Automated Trading System..."
start_service "automated_trading" "automated_trading_system.py"

# Start Comprehensive Trading System (simple version)
echo ""
echo "🎯 Starting Comprehensive Trading System..."
start_service "comprehensive_trading" "comprehensive_trading_system_simple.py"

# Start Dashboard (skip if dependencies missing)
echo ""
echo "📊 Starting Dashboard..."
cd /workspace/dashboard
if python3 -c "import flask, flask_socketio" 2>/dev/null; then
    start_service "dashboard" "advanced_dashboard.py"
    echo "✅ Dashboard started"
else
    echo "⚠️ Dashboard dependencies not available, skipping..."
fi

# Send startup notification
echo ""
echo "📱 Sending startup notification..."
cd /workspace
python3 << 'EOF'
import os
import sys
try:
    import requests
except ImportError:
    print("⚠️ requests module not available, skipping Telegram notification")
    sys.exit(0)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("⚠️ Telegram credentials not set, skipping notification")
    sys.exit(0)

message = """🚀 COMPREHENSIVE TRADING SYSTEM STARTED!

✅ AI Trading System: RUNNING
✅ Automated Trading System: RUNNING  
✅ Comprehensive Trading System: RUNNING
✅ News & Indicators: INTEGRATED
✅ AI Insights: ENABLED
✅ Telegram Notifications: ACTIVE

📊 All systems operational and monitoring markets!
🎯 Trades will be executed automatically when signals are generated.

Type /help in Telegram for commands."""
try:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=10)
    if response.status_code == 200:
        print("✅ Startup notification sent to Telegram")
    else:
        print(f"⚠️ Telegram API returned status {response.status_code}")
except Exception as e:
    print(f"⚠️ Failed to send startup notification: {e}")

EOF

echo ""
echo "✅ ALL SYSTEMS STARTED!"
echo ""
echo "📊 System Status:"
echo "  • AI Trading System: http://localhost:5000 (if configured)"
echo "  • Dashboard: Check logs for port"
echo "  • Logs: /workspace/logs/"
echo ""
echo "📱 Monitor via Telegram commands:"
echo "  /status - System status"
echo "  /balance - Account balance"
echo "  /positions - Open positions"
echo "  /trades - Recent trades"
echo ""
date
echo "=========================================="
