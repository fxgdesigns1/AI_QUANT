#!/bin/bash
# STOP ALL TRADING SYSTEMS

WORKSPACE_DIR="/workspace"
LOG_DIR="$WORKSPACE_DIR/logs"

echo "🛑 STOPPING ALL TRADING SYSTEMS"
echo "=================================="

# Stop by PID files
if [ -d "$LOG_DIR" ]; then
    for pid_file in "$LOG_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            name=$(basename "$pid_file" .pid)
            if ps -p $pid > /dev/null 2>&1; then
                echo "🛑 Stopping $name (PID: $pid)..."
                kill $pid 2>/dev/null || true
                sleep 1
                if ps -p $pid > /dev/null 2>&1; then
                    kill -9 $pid 2>/dev/null || true
                fi
                rm "$pid_file"
                echo "✅ $name stopped"
            else
                echo "⚠️  $name not running (PID: $pid)"
                rm "$pid_file"
            fi
        fi
    done
fi

# Stop by process name
for script in "automated_trading_system.py" "ai_trading_system.py" "advanced_dashboard.py"; do
    pids=$(pgrep -f "$script" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "🛑 Stopping processes for $script..."
        pkill -f "$script" 2>/dev/null || true
        sleep 1
        pkill -9 -f "$script" 2>/dev/null || true
    fi
done

echo ""
echo "✅ ALL SYSTEMS STOPPED"
