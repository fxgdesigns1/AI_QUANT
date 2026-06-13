#!/bin/bash
set -e

# Configuration
PROJECT_ROOT="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
FRONTEND_DIR="$PROJECT_ROOT/frontend/fxg-dashboard"
DATA_SOURCE="vm_logs"

echo "========================================================"
echo "   STARTING VM LOG DASHBOARD (LOCAL)"
echo "========================================================"

# 1. Refresh Data
echo "1. Refreshing Data from VM Logs..."
cd "$PROJECT_ROOT"
python3 src/analytics/vm_trade_log_parser.py
python3 src/analytics/stats_engine.py

# 2. Kill existing processes (cleanup)
echo "2. Cleaning up ports..."
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# 3. Start API
echo "3. Starting API Server (Source: $DATA_SOURCE)..."
export DASHBOARD_DATA_SOURCE="$DATA_SOURCE"
python3 dashboard/api_local.py > logs/api_local.log 2>&1 &
API_PID=$!

# 4. Start Frontend
echo "4. Starting Frontend..."
cd "$FRONTEND_DIR"
npm run dev -- --port 5173 > ../../logs/frontend_local.log 2>&1 &
FRONT_PID=$!

echo "========================================================"
echo "   DASHBOARD LIVE"
echo "========================================================"
echo "URL: http://localhost:5173"
echo "API: http://localhost:5001"
echo "Source: VM Execution Logs (Authoritative)"
echo ""
echo "Press Ctrl+C to stop..."

# Wait
wait $API_PID $FRONT_PID
