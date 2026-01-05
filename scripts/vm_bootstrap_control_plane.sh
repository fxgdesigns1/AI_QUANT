#!/usr/bin/env bash
# VM Bootstrap Script for Control Plane on GCP Debian
# Run this script on the VM after cloning/copying the repo

set -euo pipefail

echo "=========================================="
echo "Control Plane VM Bootstrap"
echo "=========================================="

# Phase 0: Preflight
echo ""
echo "[0] System info"
uname -a || true
cat /etc/os-release || true
echo ""
echo "[0] Check tools"
command -v python3 || true
command -v git || true
command -v curl || true
command -v jq || true

# Phase 1: Install prerequisites
echo ""
echo "[1] Install prereqs if missing"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Installing python3..."
    sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
fi
if ! command -v git >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1 || ! command -v lsof >/dev/null 2>&1; then
    echo "Installing git, curl, jq, lsof..."
    sudo apt-get update && sudo apt-get install -y git curl jq lsof
fi
sudo apt-get install -y python-is-python3 || true
python3 --version
pip3 --version || true

# Phase 2: Locate repo
echo ""
echo "[2] Locate repo root (find start script)"
cd ~
REPO_SCRIPT_PATH=$(find ~ -maxdepth 6 -type f -name 'scripts/start_control_plane_clean.sh' 2>/dev/null | head -1 || true)
if [ -z "$REPO_SCRIPT_PATH" ]; then
    echo "❌ Repo not found on VM. You must provide a git URL or copy the repo to this VM."
    echo "HINT: set REPO_URL env var, or place repo under ~ and rerun."
    exit 2
fi
REPO_ROOT=$(dirname "$(dirname "$REPO_SCRIPT_PATH")")
echo "✅ Repo root: $REPO_ROOT"
cd "$REPO_ROOT"
ls -la
test -f src/control_plane/api.py
test -f scripts/verify_control_plane.sh
test -f scripts/start_control_plane_clean.sh

# Phase 3: Setup venv and deps
echo ""
echo "[3] Create/activate venv"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel
echo ""
echo "[3] Install python deps (best-effort)"
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
if [ -f requirements-dev.txt ]; then
    pip install -r requirements-dev.txt
fi
echo ""
echo "[3] Sanity import compile"
python -m py_compile src/control_plane/api.py
echo "✅ Python compilation successful"

# Phase 4: Start and verify
echo ""
echo "[4] Stop any existing server"
bash scripts/stop_control_plane.sh || true
echo ""
echo "[4] Start server in background mode"
if grep -q 'CONTROL_PLANE_BG' scripts/start_control_plane_clean.sh 2>/dev/null; then
    CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh
    SERVER_PID=$(cat /tmp/control_plane_pid 2>/dev/null || echo "")
else
    echo "⚠️  Background mode not supported, starting in foreground..."
    bash scripts/start_control_plane_clean.sh &
    SERVER_PID=$!
    sleep 3
fi

echo ""
echo "[4] Read token (DO NOT PRINT FULL)"
if [ -f /tmp/control_plane_token_current.txt ]; then
    TOKEN=$(cat /tmp/control_plane_token_current.txt)
    echo "Token(first8): ${TOKEN:0:8}..."
else
    echo "❌ Token file not found. Server may not have started correctly."
    exit 1
fi

echo ""
echo "[4] Wait for server to be ready..."
for i in {1..10}; do
    if curl -sf http://127.0.0.1:8787/api/status >/dev/null 2>&1; then
        echo "✅ Server is ready"
        break
    fi
    sleep 1
done

echo ""
echo "[4] Run verification"
bash scripts/verify_control_plane.sh "$TOKEN"

echo ""
echo "[4] Confirm paper mode + execution disabled"
curl -s http://127.0.0.1:8787/api/status | jq

echo ""
echo "[4] Confirm noise shims"
curl -s -o /dev/null -w 'favicon=%{http_code}\n' http://127.0.0.1:8787/favicon.ico
curl -s -o /dev/null -w 'socketio_get=%{http_code}\n' 'http://127.0.0.1:8787/socket.io/?EIO=4&transport=polling&t=test'
curl -s -o /dev/null -w 'insights=%{http_code}\n' http://127.0.0.1:8787/api/insights
curl -s -o /dev/null -w 'trade_ideas=%{http_code}\n' http://127.0.0.1:8787/api/trade_ideas
curl -s -o /dev/null -w 'full_scan_post=%{http_code}\n' -X POST http://127.0.0.1:8787/tasks/full_scan

echo ""
echo "=========================================="
echo "✅ Bootstrap complete!"
echo "=========================================="
echo "Server PID: $SERVER_PID"
echo "Token(first8): ${TOKEN:0:8}..."
echo "Stop server: kill $SERVER_PID or bash scripts/stop_control_plane.sh"
echo ""
