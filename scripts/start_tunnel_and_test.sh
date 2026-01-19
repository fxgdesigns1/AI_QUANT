#!/bin/bash
# start_tunnel_and_test.sh
# Creates IAP tunnel to dashboard and runs Playwright tests + opens browser

set -euo pipefail

VM="fxg-quant-paper-e2-micro"
ZONE="us-east1-b"
PROJECT="fxg-ai-trading"
LOCAL_PORT="28787"
REMOTE_PORT="8787"
DASHBOARD_URL="http://127.0.0.1:${LOCAL_PORT}"

echo "=== DASHBOARD TUNNEL & TEST SETUP ==="
echo "VM: $VM"
echo "Tunnel: localhost:$LOCAL_PORT -> $VM:localhost:$REMOTE_PORT"
echo "Dashboard URL: $DASHBOARD_URL"
echo ""

# Check if tunnel is already running
if lsof -i ":$LOCAL_PORT" >/dev/null 2>&1; then
    PID=$(lsof -t -i ":$LOCAL_PORT")
    echo "⚠️  Port $LOCAL_PORT is already in use (PID: $PID)"
    echo "   Using existing tunnel..."
    TUNNEL_RUNNING=true
else
    TUNNEL_RUNNING=false
fi

# Function to cleanup tunnel on exit
cleanup() {
    if [ "$TUNNEL_RUNNING" = false ] && [ -n "${TUNNEL_PID:-}" ]; then
        echo ""
        echo "🧹 Cleaning up tunnel (PID: $TUNNEL_PID)..."
        kill $TUNNEL_PID 2>/dev/null || true
        wait $TUNNEL_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start tunnel if not already running
if [ "$TUNNEL_RUNNING" = false ]; then
    echo "🚇 Starting IAP tunnel..."
    gcloud compute ssh "$VM" \
        --zone "$ZONE" \
        --project "$PROJECT" \
        --tunnel-through-iap \
        -- -N -L "$LOCAL_PORT:127.0.0.1:$REMOTE_PORT" &
    TUNNEL_PID=$!
    
    echo "   Tunnel PID: $TUNNEL_PID"
    echo "   Waiting for tunnel to establish..."
    sleep 5
fi

# Verify tunnel is working
echo ""
echo "🔍 Verifying tunnel connection..."
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf --max-time 3 "$DASHBOARD_URL/health" >/dev/null 2>&1; then
        echo "✅ Tunnel is working! Dashboard is accessible."
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "   Waiting for tunnel... (attempt $RETRY_COUNT/$MAX_RETRIES)"
            sleep 2
        else
            echo "❌ Tunnel failed to connect after $MAX_RETRIES attempts"
            echo "   Please check:"
            echo "   1. VM is running"
            echo "   2. Control plane service is running on VM (port $REMOTE_PORT)"
            echo "   3. You have gcloud access configured"
            exit 1
        fi
    fi
done

# Get dashboard status
echo ""
echo "📊 Dashboard Status:"
STATUS=$(curl -sf --max-time 5 "$DASHBOARD_URL/api/status" | python3 -m json.tool 2>/dev/null || echo "Unable to parse status")
echo "$STATUS" | head -20

# Run Playwright tests
echo ""
echo "🧪 Running Playwright tests..."
export DASHBOARD_URL="$DASHBOARD_URL"
export CONTROL_PLANE_TOKEN="${CONTROL_PLANE_TOKEN:-}"

# Check if Playwright is installed
if ! command -v npx &> /dev/null; then
    echo "⚠️  npx not found. Installing Playwright..."
    npm install
fi

# Run Playwright test
if [ -f "src/verification/playwright_dashboard_full.spec.ts" ]; then
    echo "   Running: playwright_dashboard_full.spec.ts"
    npx playwright test src/verification/playwright_dashboard_full.spec.ts --headed || echo "⚠️  Playwright test had issues (check output above)"
else
    echo "⚠️  Playwright test file not found: src/verification/playwright_dashboard_full.spec.ts"
fi

# Open browser
echo ""
echo "🌐 Opening dashboard in browser..."
if command -v open &> /dev/null; then
    # macOS
    open "$DASHBOARD_URL"
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open "$DASHBOARD_URL"
elif command -v start &> /dev/null; then
    # Windows
    start "$DASHBOARD_URL"
else
    echo "   Please manually open: $DASHBOARD_URL"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Summary:"
echo "   Dashboard URL: $DASHBOARD_URL"
echo "   Tunnel PID: ${TUNNEL_PID:-existing}"
echo ""
echo "⚠️  Keep this terminal open to maintain the tunnel."
echo "   Press Ctrl+C to stop the tunnel and exit."

# Keep script running to maintain tunnel
if [ "$TUNNEL_RUNNING" = false ]; then
    wait $TUNNEL_PID
else
    # If tunnel was already running, just wait
    echo "   (Tunnel was already running - press Ctrl+C to exit this script)"
    while true; do
        sleep 60
        # Check if tunnel is still alive
        if ! lsof -i ":$LOCAL_PORT" >/dev/null 2>&1; then
            echo "⚠️  Tunnel appears to have closed. Exiting..."
            exit 1
        fi
    fi
fi
