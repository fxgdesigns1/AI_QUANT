#!/bin/bash
# dev_tunnel_alpha.sh
# Development tunnel for ALPHA VM - bypasses Google security for local development
# For dashboard development without Cloudflare/Google security layers

set -euo pipefail

VM="fxg-quant-paper-e2-micro"
ZONE="us-east1-b"
PROJECT="fxg-ai-trading"
LOCAL_PORT="28787"
REMOTE_PORT="8787"

echo "=== DEVELOPMENT TUNNEL TO ALPHA VM ==="
echo "Forwarding localhost:$LOCAL_PORT -> $VM:localhost:$REMOTE_PORT"
echo "This tunnel bypasses Google Cloud security for local development"
echo ""

# Check if port is already in use
if lsof -i ":$LOCAL_PORT" >/dev/null 2>&1; then
    echo "⚠️  Port $LOCAL_PORT is already in use."
    PID=$(lsof -t -i ":$LOCAL_PORT")
    echo "    PID: $PID"
    echo "    To kill existing tunnel: kill $PID"
    read -p "Kill existing tunnel and continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill "$PID" || true
        sleep 1
    else
        echo "Exiting. Please free port $LOCAL_PORT or use a different port."
        exit 1
    fi
fi

echo "🚀 Starting tunnel..."
echo "   Dashboard will be available at: http://127.0.0.1:$LOCAL_PORT/"
echo "   Press Ctrl+C to stop the tunnel"
echo ""

# Run the tunnel command (IAP bypassed by using direct SSH with port forwarding)
# -N: Do not execute a remote command (forwarding only)
# -L: Local port forwarding
exec gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    -- -N -L "$LOCAL_PORT:127.0.0.1:$REMOTE_PORT"
