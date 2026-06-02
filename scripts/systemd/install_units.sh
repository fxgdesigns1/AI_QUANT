#!/bin/bash
# install_units.sh — Install both AI_QUANT systemd units
#
# WHAT IT DOES:
# - Copies service files to /etc/systemd/system/
# - Reloads systemd daemon
# - Optionally enables and starts services (if ENABLE_AND_START=1)
#
# USAGE:
#   sudo bash scripts/systemd/install_units.sh
#   sudo ENABLE_AND_START=1 bash scripts/systemd/install_units.sh  # also enable and start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ENABLE_AND_START="${ENABLE_AND_START:-0}"

echo "=== AI_QUANT — Systemd Units Installer ==="
echo "Repo root: $REPO_ROOT"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This script must be run as root (sudo)"
    exit 1
fi

# Check service files exist
CONTROL_PLANE_UNIT="$REPO_ROOT/scripts/systemd/ai-quant-control-plane.service"
RUNNER_UNIT="$REPO_ROOT/scripts/systemd/ai-quant-runner.service"

if [ ! -f "$CONTROL_PLANE_UNIT" ]; then
    echo "[ERROR] Control plane unit not found: $CONTROL_PLANE_UNIT"
    exit 1
fi

if [ ! -f "$RUNNER_UNIT" ]; then
    echo "[ERROR] Runner unit not found: $RUNNER_UNIT"
    exit 1
fi

echo "--- Installing systemd units ---"
cp "$CONTROL_PLANE_UNIT" "/etc/systemd/system/ai-quant-control-plane.service"
chmod 644 "/etc/systemd/system/ai-quant-control-plane.service"
echo "[INSTALLED] /etc/systemd/system/ai-quant-control-plane.service"

cp "$RUNNER_UNIT" "/etc/systemd/system/ai-quant-runner.service"
chmod 644 "/etc/systemd/system/ai-quant-runner.service"
echo "[INSTALLED] /etc/systemd/system/ai-quant-runner.service"

echo ""
echo "--- Reloading systemd daemon ---"
systemctl daemon-reload
echo "[RELOADED] systemd daemon"

echo ""
echo "--- Checking environment file ---"
ENV_FILE="/etc/ai-quant/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "[WARNING] Environment file not found: $ENV_FILE"
    echo "          Services will fail to start without this file."
    echo "          Create it with: sudo install -m 600 /path/to/.env $ENV_FILE"
else
    echo "[OK] Environment file exists: $ENV_FILE"
    # Check permissions
    PERMS=$(stat -c "%a" "$ENV_FILE" 2>/dev/null || stat -f "%OLp" "$ENV_FILE" 2>/dev/null || echo "unknown")
    if [ "$PERMS" != "600" ]; then
        echo "[WARNING] Environment file permissions are $PERMS (should be 600)"
        echo "          Fix with: sudo chmod 600 $ENV_FILE"
    else
        echo "[OK] Environment file permissions: 600"
    fi
fi

if [ "$ENABLE_AND_START" = "1" ]; then
    echo ""
    echo "--- Enabling and starting services ---"
    
    systemctl enable ai-quant-control-plane.service
    systemctl enable ai-quant-runner.service
    echo "[ENABLED] Both services"
    
    systemctl start ai-quant-control-plane.service
    echo "[STARTED] ai-quant-control-plane.service"
    
    # Wait a moment for control plane to be ready
    sleep 2
    
    systemctl start ai-quant-runner.service
    echo "[STARTED] ai-quant-runner.service"
    
    echo ""
    echo "--- Service status ---"
    systemctl status ai-quant-control-plane.service --no-pager -l || true
    echo ""
    systemctl status ai-quant-runner.service --no-pager -l || true
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "NEXT STEPS:"
echo "  1. Ensure environment file exists:"
echo "     sudo install -m 600 /path/to/.env /etc/ai-quant/.env"
echo ""
echo "  2. Enable and start services:"
echo "     sudo systemctl enable ai-quant-control-plane.service"
echo "     sudo systemctl enable ai-quant-runner.service"
echo "     sudo systemctl start ai-quant-control-plane.service"
echo "     sudo systemctl start ai-quant-runner.service"
echo ""
echo "  3. Check status:"
echo "     sudo systemctl status ai-quant-control-plane.service"
echo "     sudo systemctl status ai-quant-runner.service"
echo "     sudo journalctl -u ai-quant-control-plane.service -f"
echo "     sudo journalctl -u ai-quant-runner.service -f"
echo ""
echo "  4. Verify endpoints:"
echo "     curl -s http://127.0.0.1:8787/health"
echo "     curl -s http://127.0.0.1:8787/api/status"
