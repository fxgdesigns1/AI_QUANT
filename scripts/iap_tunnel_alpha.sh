#!/bin/bash
# iap_tunnel_alpha.sh
# Establishes an IAP SSH tunnel to ALPHA VM for dashboard access.
# Designed to be run by launchd or manually.

set -euo pipefail

VM="fxg-quant-paper-e2-micro"
ZONE="us-east1-b"
PROJECT="fxg-ai-trading"
LOCAL_PORT="28787"
REMOTE_PORT="8787"

echo "=== STARTING IAP TUNNEL TO $VM ($ZONE) ==="
echo "Forwarding localhost:$LOCAL_PORT -> $VM:localhost:$REMOTE_PORT"

# Check if port is already in use
if lsof -i ":$LOCAL_PORT" >/dev/null 2>&1; then
    echo "⚠️  Port $LOCAL_PORT is already in use."
    PID=$(lsof -t -i ":$LOCAL_PORT")
    echo "    PID: $PID"
    # Optional: kill it? For now, we fail or let ssh handle it (ssh will complain)
fi

# Run the tunnel command
# -N: Do not execute a remote command (forwarding only)
# -L: Local port forwarding
# -q: Quiet mode
exec gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    -- -N -q -L "$LOCAL_PORT:127.0.0.1:$REMOTE_PORT"
