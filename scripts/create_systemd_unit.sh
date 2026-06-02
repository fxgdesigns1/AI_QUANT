#!/usr/bin/env bash
# Create systemd unit for Control Plane (optional persistence)
# Run this inside the VM shell: bash scripts/create_systemd_unit.sh

set -euo pipefail

REPO_ROOT="/home/fxgdesigns1_gmail_com/gcloud-system"
USER=$(whoami)

echo "[6] Creating systemd unit for Control Plane..."

# Verify repo exists
if [ ! -d "$REPO_ROOT" ]; then
    echo "❌ Repo missing at $REPO_ROOT"
    exit 1
fi

# Create systemd unit
sudo tee /etc/systemd/system/ai-quant-control-plane.service >/dev/null <<UNIT
[Unit]
Description=AI_QUANT Control Plane (paper, signals-only)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$REPO_ROOT
Environment=CONTROL_PLANE_BG=0
# Keep binding local; server itself should bind 127.0.0.1
Environment=CONTROL_PLANE_HOST=127.0.0.1
Environment=CONTROL_PLANE_PORT=8787
# Paper mode enforced
Environment=TRADING_MODE=paper
ExecStart=/bin/bash -lc 'cd $REPO_ROOT && source .venv/bin/activate && python -m src.control_plane.api'
Restart=on-failure
RestartSec=3
# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

echo "✅ Systemd unit created"

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable ai-quant-control-plane.service

echo ""
echo "ℹ️  Unit created and enabled. To start it:"
echo "   sudo systemctl start ai-quant-control-plane.service"
echo ""
echo "ℹ️  To check status:"
echo "   sudo systemctl status ai-quant-control-plane.service"
echo ""
echo "ℹ️  To view logs:"
echo "   sudo journalctl -u ai-quant-control-plane.service -f"
echo ""
echo "⚠️  NOTE: If you start the systemd unit, stop any manually started server first:"
echo "   bash scripts/stop_control_plane.sh"
echo ""
