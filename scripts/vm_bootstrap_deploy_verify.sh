#!/usr/bin/env bash
# One-shot idempotent bootstrap+deploy+verify for Control Plane on GCP VM
# Run this inside the VM shell: bash scripts/vm_bootstrap_deploy_verify.sh

set -euo pipefail

REPO_ROOT="/home/fxgdesigns1_gmail_com/gcloud-system"

echo "=========================================="
echo "Control Plane VM Bootstrap+Deploy+Verify"
echo "=========================================="

# Phase 0: Preflight
echo ""
echo "[0] Preflight checks..."
whoami=$(whoami)
host=$(hostname)
echo "User: $whoami, Host: $host"
uname -a || true
cat /etc/os-release || true
echo ""
echo "[0] Tool checks:"
command -v python3 || echo "⚠️  python3 missing"
command -v git || echo "⚠️  git missing"
command -v curl || echo "⚠️  curl missing"
command -v jq || echo "⚠️  jq missing"
command -v lsof || echo "⚠️  lsof missing"
command -v rg || echo "⚠️  ripgrep missing (will install)"

# Phase 1: Install prerequisites
echo ""
echo "[1] Installing prerequisites..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git curl jq lsof ripgrep
sudo apt-get install -y python-is-python3 || true
python3 --version
rg --version
jq --version

# Phase 2: Verify repo presence
echo ""
echo "[2] Checking repo..."
if [ ! -d "$REPO_ROOT" ]; then
    echo "❌ Repo missing at $REPO_ROOT"
    echo "➡️  Copy it from Mac (recommended):"
    echo "   gcloud compute scp --recurse --zone us-east1-b --project fxg-ai-trading \\"
    echo "     '<LOCAL_PATH>/Gcloud system' fxg-quant-paper-e2-micro:~/gcloud-system"
    exit 2
fi
cd "$REPO_ROOT"
test -f src/control_plane/api.py
test -f scripts/start_control_plane_clean.sh
test -f scripts/stop_control_plane.sh
test -f scripts/verify_control_plane.sh
echo "✅ Repo OK: $REPO_ROOT"

# Phase 3: Setup venv and deps
echo ""
echo "[3] Setting up venv and dependencies..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel
if [ -f requirements.txt ]; then
    echo "[3] Installing requirements.txt..."
    pip install -r requirements.txt
else
    echo "[3] ⚠️  requirements.txt not found (continuing)"
fi
if [ -f requirements-dev.txt ]; then
    echo "[3] Installing requirements-dev.txt..."
    pip install -r requirements-dev.txt
fi
echo "[3] Compile check..."
python3 -m py_compile src/control_plane/api.py
echo "✅ py_compile OK"

# Phase 4: Start background and verify
echo ""
echo "[4] Stopping any existing server..."
bash scripts/stop_control_plane.sh || true

echo ""
echo "[4] Starting server in background mode..."
CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh

echo ""
echo "[4] Reading token (redacted)..."
if [ ! -f /tmp/control_plane_token_current.txt ]; then
    echo "❌ Token file not found. Server may not have started correctly."
    exit 1
fi
TOKEN=$(cat /tmp/control_plane_token_current.txt)
echo "Token(first8): ${TOKEN:0:8}..."

echo ""
echo "[4] Running verification..."
bash scripts/verify_control_plane.sh "$TOKEN"
VERIFY_EXIT=$?
echo "verify_exit_code=$VERIFY_EXIT"

if [ "$VERIFY_EXIT" -ne 0 ]; then
    echo "❌ Verification failed with exit code $VERIFY_EXIT"
    echo "Check logs: tail -200 /tmp/control_plane.out"
    exit 1
fi

echo ""
echo "[4] Confirming status..."
curl -s http://127.0.0.1:8787/api/status | jq

echo ""
echo "[4] Evidence:"
echo "  PID file: /tmp/control_plane_pid"
if [ -f /tmp/control_plane_pid ]; then
    echo "  PID: $(cat /tmp/control_plane_pid)"
fi
echo "  Log file: /tmp/control_plane.out"
echo "  Token file: /tmp/control_plane_token_current.txt (token: ${TOKEN:0:8}...)"

echo ""
echo "[4] Log tail (last 40 lines):"
tail -40 /tmp/control_plane.out || true

echo ""
echo "=========================================="
echo "✅ Bootstrap+Deploy+Verify Complete!"
echo "=========================================="
echo ""
echo "[7] Safe access from your Mac:"
echo "  1. Open SSH tunnel:"
echo "     gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \\"
echo "       fxg-quant-paper-e2-micro -- -L 8787:127.0.0.1:8787"
echo ""
echo "  2. In another terminal (or after tunnel is established), open:"
echo "     http://127.0.0.1:8787"
echo ""
echo "  3. Get token from VM:"
echo "     gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \\"
echo "       fxg-quant-paper-e2-micro -- 'cat /tmp/control_plane_token_current.txt'"
echo ""
echo "  4. Paste token (first 8: ${TOKEN:0:8}...) into dashboard Settings ⚙️"
echo ""
echo "⚠️  IMPORTANT: Server binds to 127.0.0.1 only (localhost)."
echo "   No public firewall port opened. Access via SSH tunnel only."
echo ""
