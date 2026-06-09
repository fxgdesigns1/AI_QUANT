#!/usr/bin/env bash
set -euo pipefail

echo "[VM] Installing prerequisites..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git curl jq lsof
sudo apt-get install -y python-is-python3 || true

echo "[VM] Repo root: $(pwd)"
test -f src/control_plane/api.py
test -f scripts/start_control_plane_clean.sh
test -f scripts/verify_control_plane.sh

echo "[VM] Creating/activating venv..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel

if [ -f requirements.txt ]; then
  echo "[VM] Installing requirements.txt..."
  pip install -r requirements.txt
else
  echo "[VM] requirements.txt not found (continuing)."
fi

echo "[VM] Compile check..."
python3 -m py_compile src/control_plane/api.py

echo "[VM] Stop any existing server..."
bash scripts/stop_control_plane.sh || true

echo "[VM] Start control plane in background (CONTROL_PLANE_BG=1)..."
CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh

echo "[VM] Read token (redacted)..."
TOKEN=$(cat /tmp/control_plane_token_current.txt)
echo "Token(first8): ${TOKEN:0:8}..."

echo "[VM] Run verification..."
bash scripts/verify_control_plane.sh "$TOKEN"

echo "[VM] Confirm status..."
curl -s http://127.0.0.1:8787/api/status | jq

echo "[VM] Evidence:"
echo "  PID: /tmp/control_plane_pid"
echo "  Logs: /tmp/control_plane.out"
echo "  Token file: /tmp/control_plane_token_current.txt (do not share)"
echo "  Playwright log (if present): scripts/artifacts/pw_forbidden_requests.log"
echo "[VM] Tail logs:"
tail -50 /tmp/control_plane.out || true

echo "[VM] Safe access via SSH tunnel from your Mac:"
echo "  gcloud compute ssh --project fxg-ai-trading --zone us-east1-b fxg-quant-paper-e2-micro -- -L 8787:127.0.0.1:8787"
echo "  Then open: http://127.0.0.1:8787"
