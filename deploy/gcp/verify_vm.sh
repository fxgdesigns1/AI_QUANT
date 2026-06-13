#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GCP_ZONE:=europe-west2-a}"
: "${GCP_VM_NAME:=ai-quant-control-plane}"

# Runs remote verification and prints safe outputs only.

gcloud compute ssh "$GCP_VM_NAME" --zone "$GCP_ZONE" --project "$GCP_PROJECT_ID" --command '
set -euo pipefail
cd /opt/ai-quant
source .venv/bin/activate

# Ensure service is active
if ! sudo systemctl is-active ai-quant-control-plane >/dev/null 2>&1; then
  echo "❌ Service ai-quant-control-plane is not active" >&2
  sudo systemctl --no-pager -l status ai-quant-control-plane | tail -n 40
  exit 1
fi

# Show service status (safe: no secrets)
sudo systemctl --no-pager -l status ai-quant-control-plane | tail -n 40

# Token is stored on VM at /tmp/control_plane_token_current.txt
if [[ ! -f /tmp/control_plane_token_current.txt ]]; then
  echo "❌ Token file not found: /tmp/control_plane_token_current.txt" >&2
  exit 1
fi

TOKEN="$(sudo -u aiquant cat /tmp/control_plane_token_current.txt | head -1)"
if [[ -z "$TOKEN" ]]; then
  echo "❌ Token is empty" >&2
  exit 1
fi

# Print only token prefix (first 8 chars) for verification
echo "Token prefix: ${TOKEN:0:8}..." >&2

export CP_BASE="http://127.0.0.1:8787"

# Full verification with all requirements
REQUIRE_LIVE_DATA=1 REQUIRE_NEWS_DATA=1 REQUIRE_NEWS_PERSISTENCE=1 REQUIRE_TELEGRAM=1 bash scripts/verify_control_plane.sh "$TOKEN" || {
  echo "❌ Verification failed" >&2
  exit 1
}
'

if [[ $? -eq 0 ]]; then
  echo "✅ VM verify complete."
else
  echo "❌ VM verify failed" >&2
  exit 1
fi
