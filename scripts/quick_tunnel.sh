#!/bin/bash
# quick_tunnel.sh
# Quick tunnel setup - just starts tunnel and opens browser

set -euo pipefail

VM="fxg-quant-paper-e2-micro"
ZONE="us-east1-b"
PROJECT="fxg-ai-trading"
LOCAL_PORT="28787"
REMOTE_PORT="8787"
DASHBOARD_URL="http://127.0.0.1:${LOCAL_PORT}"

echo "🚇 Quick Tunnel Setup"
echo "   Dashboard: $DASHBOARD_URL"
echo ""

# Check if tunnel already exists
if lsof -i ":$LOCAL_PORT" >/dev/null 2>&1; then
    echo "✅ Tunnel already running on port $LOCAL_PORT"
else
    echo "🚇 Starting tunnel in background..."
    nohup gcloud compute ssh "$VM" \
        --zone "$ZONE" \
        --project "$PROJECT" \
        --tunnel-through-iap \
        -- -N -L "$LOCAL_PORT:127.0.0.1:$REMOTE_PORT" > /tmp/tunnel.log 2>&1 &
    
    TUNNEL_PID=$!
    echo "   Tunnel PID: $TUNNEL_PID"
    echo "   Waiting for connection..."
    sleep 5
    
    # Verify
    if curl -sf --max-time 3 "$DASHBOARD_URL/health" >/dev/null 2>&1; then
        echo "✅ Tunnel connected!"
    else
        echo "⚠️  Tunnel may still be connecting. Check /tmp/tunnel.log"
    fi
fi

# Open browser
echo ""
echo "🌐 Opening browser..."
if command -v open &> /dev/null; then
    open "$DASHBOARD_URL"
elif command -v xdg-open &> /dev/null; then
    xdg-open "$DASHBOARD_URL"
else
    echo "   Please open: $DASHBOARD_URL"
fi

echo ""
echo "✅ Done! Dashboard should be opening in your browser."
echo "   URL: $DASHBOARD_URL"
echo ""
echo "   To stop tunnel: kill \$(lsof -t -i:$LOCAL_PORT)"
