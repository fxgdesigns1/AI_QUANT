#!/bin/bash
# Restart API Service on VM
# Run this ON THE VM (you're already SSH'd in)

cd ~/gcloud-system

echo "🛑 Stopping existing API service..."
pkill -f 'uvicorn.*api:app'
sleep 2

echo "🚀 Starting new API service..."
nohup python3 -m uvicorn src.control_plane.api:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &

sleep 3

echo "✅ Checking if API started..."
PID=$(pgrep -f 'uvicorn.*api:app')
if [ -n "$PID" ]; then
    echo "✅ API service running (PID: $PID)"
    echo ""
    echo "📋 Last 20 lines of log:"
    tail -20 /tmp/api.log
else
    echo "❌ API service failed to start"
    echo ""
    echo "📋 Full log:"
    cat /tmp/api.log
fi
