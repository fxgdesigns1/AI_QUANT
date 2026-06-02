#!/bin/bash
# provision_vm.sh — Canonical VM provisioning script
#
# ONE canonical provisioning entrypoint for both ALPHA and BETA VMs.
# Sets up /opt/ai-quant, user, dependencies, systemd services, retention, DNS healthcheck.
#
# USAGE:
#   sudo bash scripts/provision_vm.sh
#   sudo ENABLE_AND_START=1 bash scripts/provision_vm.sh  # also enable and start services
#
# PREREQUISITES:
#   - Code must be copied to /opt/ai-quant (or repo cloned there)
#   - /etc/ai-quant/.env must exist (with OANDA credentials, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENABLE_AND_START="${ENABLE_AND_START:-0}"

echo "=== AI-QUANT — Canonical VM Provisioning ==="
echo "Repo root: $REPO_ROOT"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This script must be run as root (sudo)"
    exit 1
fi

# Check if code exists at /opt/ai-quant (assumes code already copied)
if [ ! -d "/opt/ai-quant" ]; then
    echo "[ERROR] /opt/ai-quant directory not found"
    echo "        Code must be copied to /opt/ai-quant first"
    echo "        Or clone repo: git clone <URL> /opt/ai-quant"
    exit 1
fi

# Phase 1: Ensure aiquant user exists
echo "--- [1] Ensuring aiquant user exists ---"
if ! id -u aiquant >/dev/null 2>&1; then
    useradd -m -s /bin/bash aiquant || { echo "[ERROR] Failed to create aiquant user" >&2; exit 1; }
    echo "[CREATED] aiquant user"
else
    echo "[EXISTS] aiquant user already exists"
fi

# Phase 2: Ensure /opt/ai-quant owned by aiquant
echo ""
echo "--- [2] Setting /opt/ai-quant ownership ---"
chown -R aiquant:aiquant /opt/ai-quant
echo "[OK] /opt/ai-quant owned by aiquant"

# Phase 3: Install system dependencies
echo ""
echo "--- [3] Installing system dependencies ---"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl jq lsof ripgrep || true
echo "[OK] System dependencies installed"

# Phase 4: Ensure /etc/ai-quant/.env exists (critical)
echo ""
echo "--- [4] Checking environment file ---"
ENV_FILE="/etc/ai-quant/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "[ERROR] Environment file not found: $ENV_FILE"
    echo "        Create it with: sudo install -m 600 /path/to/.env $ENV_FILE"
    exit 1
fi
chmod 600 "$ENV_FILE"
chown root:root "$ENV_FILE"
echo "[OK] Environment file exists: $ENV_FILE"

# Phase 5: Install systemd service units
echo ""
echo "--- [5] Installing systemd service units ---"
cd /opt/ai-quant
if [ ! -f "scripts/systemd/install_units.sh" ]; then
    echo "[ERROR] install_units.sh not found in /opt/ai-quant/scripts/systemd/"
    exit 1
fi
bash scripts/systemd/install_units.sh
echo "[OK] Systemd service units installed"

# Phase 6: Install retention timer
echo ""
echo "--- [6] Installing retention timer ---"
if [ -f "/opt/ai-quant/systemd/ai-quant-retention.service" ] && [ -f "/opt/ai-quant/systemd/ai-quant-retention.timer" ]; then
    cp /opt/ai-quant/systemd/ai-quant-retention.service /etc/systemd/system/
    cp /opt/ai-quant/systemd/ai-quant-retention.timer /etc/systemd/system/
    chmod 644 /etc/systemd/system/ai-quant-retention.service
    chmod 644 /etc/systemd/system/ai-quant-retention.timer
    
    # Ensure retention cleanup script is executable
    if [ -f "/opt/ai-quant/scripts/retention_cleanup.sh" ]; then
        chmod +x /opt/ai-quant/scripts/retention_cleanup.sh
    fi
    
    systemctl daemon-reload
    systemctl enable ai-quant-retention.timer
    echo "[INSTALLED] Retention timer (enabled, runs daily at 03:00 UTC)"
else
    echo "[WARNING] Retention timer files not found (skipping)"
fi

# Phase 7: Install DNS healthcheck timer
echo ""
echo "--- [7] Installing DNS healthcheck timer ---"
if [ -f "/opt/ai-quant/systemd/ai-quant-dns-healthcheck.service" ] && [ -f "/opt/ai-quant/systemd/ai-quant-dns-healthcheck.timer" ]; then
    cp /opt/ai-quant/systemd/ai-quant-dns-healthcheck.service /etc/systemd/system/
    cp /opt/ai-quant/systemd/ai-quant-dns-healthcheck.timer /etc/systemd/system/
    chmod 644 /etc/systemd/system/ai-quant-dns-healthcheck.service
    chmod 644 /etc/systemd/system/ai-quant-dns-healthcheck.timer
    
    systemctl daemon-reload
    systemctl enable ai-quant-dns-healthcheck.timer
    echo "[INSTALLED] DNS healthcheck timer (enabled, runs every 5 minutes)"
else
    echo "[WARNING] DNS healthcheck timer files not found (skipping)"
fi

# Phase 7b: Install pre-open gate timer
echo ""
echo "--- [7b] Installing pre-open gate timer ---"
if [ -f "/opt/ai-quant/systemd/ai-quant-preopen-gate.service" ] && [ -f "/opt/ai-quant/systemd/ai-quant-preopen-gate.timer" ]; then
    # Ensure pre-open gate check script is executable
    if [ -f "/opt/ai-quant/scripts/preopen_gate_check.sh" ]; then
        chmod +x /opt/ai-quant/scripts/preopen_gate_check.sh
    fi
    
    cp /opt/ai-quant/systemd/ai-quant-preopen-gate.service /etc/systemd/system/
    cp /opt/ai-quant/systemd/ai-quant-preopen-gate.timer /etc/systemd/system/
    chmod 644 /etc/systemd/system/ai-quant-preopen-gate.service
    chmod 644 /etc/systemd/system/ai-quant-preopen-gate.timer
    
    systemctl daemon-reload
    systemctl enable ai-quant-preopen-gate.timer
    echo "[INSTALLED] Pre-open gate timer (enabled, runs every 5 minutes)"
else
    echo "[WARNING] Pre-open gate timer files not found (skipping)"
fi

# Phase 8: Enable and start services (if requested)
if [ "$ENABLE_AND_START" = "1" ]; then
    echo ""
    echo "--- [8] Enabling and starting services ---"
    systemctl enable ai-quant-control-plane.service
    systemctl enable ai-quant-runner.service
    systemctl start ai-quant-control-plane.service
    sleep 2
    systemctl start ai-quant-runner.service
    echo "[STARTED] Both services enabled and started"
fi

# Phase 9: Configure Journald Retention
echo ""
echo "--- [9] Configuring Journald Retention ---"
if ! grep -q "SystemMaxUse=200M" /etc/systemd/journald.conf; then
    echo "SystemMaxUse=200M" >> /etc/systemd/journald.conf
    echo "RuntimeMaxUse=200M" >> /etc/systemd/journald.conf
    systemctl restart systemd-journald
    echo "[CONFIGURED] Journald limits set to 200M"
else
    echo "[OK] Journald limits already configured"
fi

# Phase 9b: Optional Cloudflare Tunnel (Mode B)
echo ""
echo "--- [9b] Checking for Cloudflare Tunnel Token ---"
if [ -n "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]; then
    echo "[FOUND] CLOUDFLARE_TUNNEL_TOKEN present. Installing cloudflared..."
    
    # 1. Install cloudflared if needed
    if ! command -v cloudflared &> /dev/null; then
        echo "    Installing cloudflared binary..."
        curl -L --retry 5 https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
        dpkg -i /tmp/cloudflared.deb || apt-get install -f -y
        rm /tmp/cloudflared.deb
    else
        echo "    cloudflared already installed."
    fi
    
    # 2. Install Systemd Service
    echo "    Configuring cloudflared service..."
    cat > /etc/systemd/system/cloudflared-tunnel.service <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
TimeoutStartSec=0
Type=notify
ExecStart=/usr/bin/cloudflared tunnel run --token ${CLOUDFLARE_TUNNEL_TOKEN}
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    
    chmod 644 /etc/systemd/system/cloudflared-tunnel.service
    systemctl daemon-reload
    systemctl enable cloudflared-tunnel.service
    systemctl restart cloudflared-tunnel.service
    
    echo "[STARTED] cloudflared-tunnel service active."
else
    echo "[SKIP] No CLOUDFLARE_TUNNEL_TOKEN env var found. Skipping Cloudflare Tunnel setup."
fi

# Phase 10: Verification (if requested)
if [ "${VERIFY:-0}" = "1" ]; then
    echo ""
    echo "=== VERIFICATION MODE ==="
    
    FAIL=0
    
    echo -n "Checking services... "
    if systemctl is-active --quiet ai-quant-control-plane && systemctl is-active --quiet ai-quant-runner; then
        echo "PASS"
    else
        echo "FAIL"
        FAIL=1
    fi

    echo -n "Checking timers... "
    if systemctl is-enabled --quiet ai-quant-dns-healthcheck.timer && \
       systemctl is-enabled --quiet ai-quant-preopen-gate.timer && \
       systemctl is-enabled --quiet ai-quant-retention.timer; then
        echo "PASS"
    else
        echo "FAIL (missing enabled timers)"
        systemctl list-timers --all | grep ai-quant
        FAIL=1
    fi

    echo -n "Checking API health... "
    if curl -sS --fail --max-time 5 http://127.0.0.1:8787/health >/dev/null; then
        echo "PASS"
    else
        echo "FAIL"
        FAIL=1
    fi

    echo -n "Checking API status (one truth)... "
    STATUS=$(curl -sS --max-time 5 http://127.0.0.1:8787/api/status)
    LAST_WRITE=$(echo "$STATUS" | jq -r .last_status_write_at)
    if [ "$LAST_WRITE" != "null" ] && [ "$LAST_WRITE" != "" ]; then
        echo "PASS"
    else
        echo "FAIL (last_status_write_at is null)"
        FAIL=1
    fi

    echo -n "Checking API config (one truth)... "
    CONFIG=$(curl -sS --max-time 5 http://127.0.0.1:8787/api/config)
    OK=$(echo "$CONFIG" | jq -r .ok)
    COUNT=$(echo "$CONFIG" | jq -r .account_risk_limits_count)
    if [ "$OK" = "true" ] && [ "$COUNT" != "null" ]; then
        echo "PASS"
    else
        echo "FAIL (ok=$OK, count=$COUNT)"
        FAIL=1
    fi
    
    if [ "$FAIL" = "0" ]; then
        echo ""
        echo "✅ VERIFICATION PASSED: System is clean, lean, and one-truth compliant."
    else
        echo ""
        echo "❌ VERIFICATION FAILED"
        exit 1
    fi
fi

echo ""
echo "=== Provisioning Complete ==="
echo ""
echo "NEXT STEPS:"
echo "  1. Verify environment file: sudo cat /etc/ai-quant/.env | head -5"
echo "  2. Enable and start services:"
echo "     sudo systemctl enable ai-quant-control-plane ai-quant-runner"
echo "     sudo systemctl start ai-quant-control-plane"
echo "     sudo systemctl start ai-quant-runner"
echo "  3. Check status:"
echo "     sudo systemctl status ai-quant-control-plane ai-quant-runner"
echo "  4. Verify endpoints:"
echo "     curl -s http://127.0.0.1:8787/health"
echo "     curl -s http://127.0.0.1:8787/api/status"
