#!/usr/bin/env bash
# Deploy dashboard fixes to VM and restart service
# This script ensures the service picks up the new dashboard files

set -euo pipefail

PROJECT="fxg-ai-trading"
ZONE="us-east1-b"
INSTANCE="fxg-quant-paper-e2-micro"

echo "[DEPLOY] Stopping Control Plane service on VM..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" --command \
  "cd ~/gcloud-system && bash scripts/stop_control_plane.sh" || true

echo "[DEPLOY] Waiting for port to be free..."
sleep 3

echo "[DEPLOY] Starting Control Plane service with new code..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" --command \
  "cd ~/gcloud-system && CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh"

echo "[DEPLOY] Waiting for service to be ready..."
sleep 5

echo "[DEPLOY] Verifying deployment..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" --command \
  "cd ~/gcloud-system && curl -sf http://127.0.0.1:8787/api/status > /dev/null && echo '✅ Service is responding' || echo '❌ Service not responding'"

echo ""
echo "[DEPLOY] ✅ Dashboard deployment complete!"
echo ""
echo "📋 To access dashboard:"
echo "   1. Open SSH tunnel: gcloud compute ssh --project $PROJECT --zone $ZONE $INSTANCE -- -L 8787:127.0.0.1:8787"
echo "   2. Open browser: http://127.0.0.1:8787"
echo "   3. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)"
echo ""
echo "⚠️  IMPORTANT: Do a hard refresh (Cmd+Shift+R) to clear browser cache!"
