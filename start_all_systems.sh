#!/bin/bash
# UNIFIED STARTUP SCRIPT FOR ALL TRADING SYSTEMS
# This script starts: Automated, Semi-Automated, and AI Trading Systems

set -e

WORKSPACE_DIR="/workspace"
LOG_DIR="$WORKSPACE_DIR/logs"
mkdir -p "$LOG_DIR"

# Set environment variables
export OANDA_API_KEY="REMOVED_SECRET"
export OANDA_ACCOUNT_ID="101-004-30719775-008"
export OANDA_ENVIRONMENT="practice"
export TELEGRAM_TOKEN="7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
export TELEGRAM_CHAT_ID="6100678501"
export PYTHONPATH="$WORKSPACE_DIR:/home/ubuntu/.local/lib/python3.12/site-packages:$PYTHONPATH"
export PATH="/home/ubuntu/.local/bin:$PATH"

echo "🚀 STARTING ALL TRADING SYSTEMS"
echo "=================================="
echo "📊 Workspace: $WORKSPACE_DIR"
echo "📝 Logs: $LOG_DIR"
echo ""

# Function to start a system
start_system() {
    local name=$1
    local script=$2
    local log_file="$LOG_DIR/${name}.log"
    
    echo "🔄 Starting $name..."
    
    # Check if already running
    if pgrep -f "$script" > /dev/null; then
        echo "⚠️  $name is already running (PID: $(pgrep -f "$script"))"
        return 0
    fi
    
    # Start in background
    nohup python3 "$WORKSPACE_DIR/$script" >> "$log_file" 2>&1 &
    local pid=$!
    
    sleep 2
    
    # Check if started successfully
    if ps -p $pid > /dev/null; then
        echo "✅ $name started (PID: $pid)"
        echo "$pid" > "$LOG_DIR/${name}.pid"
        return 0
    else
        echo "❌ Failed to start $name"
        echo "📋 Last 20 lines of log:"
        tail -20 "$log_file"
        return 1
    fi
}

# Start all systems
echo "1️⃣ Starting Automated Trading System..."
start_system "automated" "automated_trading_system.py"

echo ""
echo "2️⃣ Starting AI Trading System..."
start_system "ai_trading" "ai_trading_system.py"

echo ""
echo "3️⃣ Starting Dashboard..."
start_system "dashboard" "dashboard/advanced_dashboard.py"

echo ""
echo "=================================="
echo "✅ ALL SYSTEMS STARTED"
echo ""
echo "📊 System Status:"
ps aux | grep -E "(automated_trading|ai_trading|advanced_dashboard)" | grep -v grep | awk '{print "  " $2 " - " $11 " " $12 " " $13}'
echo ""
echo "📝 Logs are in: $LOG_DIR"
echo "🔍 Check logs with: tail -f $LOG_DIR/*.log"
echo ""
echo "🛑 To stop all systems: ./stop_all_systems.sh"
