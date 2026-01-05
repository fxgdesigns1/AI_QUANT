#!/bin/bash
# install_canonical_service.sh — Install canonical systemd unit (NON-DESTRUCTIVE)
#
# WHAT IT DOES:
# - Copies service template to /etc/systemd/system/
# - Creates /etc/ai-quant/ directory if needed
# - Creates ai-quant.env.example with PLACEHOLDERS ONLY (never real secrets)
# - NEVER writes real secrets
# - NEVER enables or starts the service automatically
#
# USAGE:
#   sudo bash scripts/systemd/install_canonical_service.sh
#   DRY_RUN=1 bash scripts/systemd/install_canonical_service.sh  # preview only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DRY_RUN="${DRY_RUN:-0}"
SERVICE_NAME="ai-quant-control-plane.service"
ENV_DIR="/etc/ai-quant"
ENV_FILE="$ENV_DIR/ai-quant.env"
ENV_EXAMPLE="$ENV_DIR/ai-quant.env.example"

echo "=== FXG AI-QUANT — Canonical Service Installer ==="
echo "Repo root: $REPO_ROOT"
echo "Dry run: $DRY_RUN"
echo ""

if [ "$(id -u)" -ne 0 ] && [ "$DRY_RUN" = "0" ]; then
    echo "[ERROR] This script must be run as root (sudo)"
    echo "        Or run with DRY_RUN=1 to preview"
    exit 1
fi

# Check template exists
TEMPLATE="$REPO_ROOT/systemd/ai-quant-control-plane.service.template"
if [ ! -f "$TEMPLATE" ]; then
    echo "[ERROR] Service template not found: $TEMPLATE"
    exit 1
fi

# Guard: refuse to proceed if template contains hardcoded secrets
echo "--- Verifying template contains no hardcoded secrets ---"
if rg -q "Environment=(OANDA_API_KEY|TELEGRAM_BOT_TOKEN|OPENAI_API_KEY|GEMINI_API_KEY|GOOGLE_API_KEY|MARKETAUX_KEY|MARKETAUX_KEYS)=\S+" "$TEMPLATE" 2>/dev/null; then
    echo "[ERROR] Template contains hardcoded secrets in Environment= directives!"
    echo "        Use EnvironmentFile=/etc/ai-quant/ai-quant.env instead"
    exit 1
fi
echo "[OK] Template verified (no hardcoded secrets)"

echo "--- Installing service unit ---"
if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY] Would copy: $TEMPLATE -> /etc/systemd/system/$SERVICE_NAME"
else
    cp "$TEMPLATE" "/etc/systemd/system/$SERVICE_NAME"
    chmod 644 "/etc/systemd/system/$SERVICE_NAME"
    echo "[INSTALLED] /etc/systemd/system/$SERVICE_NAME"
fi

echo ""
echo "--- Creating environment directory ---"
if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY] Would create: $ENV_DIR"
else
    mkdir -p "$ENV_DIR"
    chmod 700 "$ENV_DIR"
    echo "[CREATED] $ENV_DIR (mode 700)"
fi

echo ""
echo "--- Creating example environment file ---"

EXAMPLE_CONTENT='# ai-quant.env.example — Environment variables for AI-QUANT Control Plane
#
# COPY this file to /etc/ai-quant/ai-quant.env and fill in values.
# NEVER commit the actual ai-quant.env file to git!
#
# Required permissions: chmod 600 /etc/ai-quant/ai-quant.env
#                       chown root:root /etc/ai-quant/ai-quant.env

# === OANDA CREDENTIALS (REQUIRED) ===
# Get from: https://www.oanda.com/demo-account/
OANDA_API_KEY=your-oanda-api-key-here
OANDA_ACCOUNT_ID=your-oanda-account-id-here

# Base URL (use practice for demo, leave blank to use default)
# Default: https://api-fxpractice.oanda.com
# Live (DANGER): https://api-fxtrade.oanda.com
OANDA_BASE_URL=https://api-fxpractice.oanda.com

# === TELEGRAM ALERTS (OPTIONAL) ===
# Create bot: https://t.me/BotFather
# Get chat ID: https://api.telegram.org/bot<token>/getUpdates
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# === CONTROL PLANE AUTH ===
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
CONTROL_PLANE_TOKEN=generate-a-secure-token-here

# === AI SERVICES (OPTIONAL) ===
# OpenAI: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Google AI: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=

# === PAPER MODE SETTINGS (default safe values) ===
# These are overridden by service unit to ensure safety
# Do not change unless you understand the implications
PAPER_EXECUTION_ENABLED=false
TRADING_MODE=paper
'

if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY] Would create: $ENV_EXAMPLE"
    echo "[DRY] Would set permissions: 644"
else
    echo "$EXAMPLE_CONTENT" > "$ENV_EXAMPLE"
    chmod 644 "$ENV_EXAMPLE"
    echo "[CREATED] $ENV_EXAMPLE (mode 644)"
fi

echo ""
echo "--- Checking for existing env file ---"
if [ -f "$ENV_FILE" ]; then
    echo "[EXISTS] $ENV_FILE already exists - NOT overwriting"
else
    echo "[INFO] $ENV_FILE does not exist"
    echo "       Copy from example: sudo cp $ENV_EXAMPLE $ENV_FILE"
    echo "       Then edit and set real values"
fi

if [ "$DRY_RUN" = "0" ]; then
    echo ""
    echo "--- Reloading systemd daemon ---"
    systemctl daemon-reload
    echo "[RELOADED] systemd daemon"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "NEXT STEPS:"
echo "  1. Copy and configure environment file:"
echo "     sudo cp $ENV_EXAMPLE $ENV_FILE"
echo "     sudo chmod 600 $ENV_FILE"
echo "     sudo nano $ENV_FILE  # fill in real values"
echo ""
echo "  2. Enable and start service:"
echo "     sudo systemctl enable $SERVICE_NAME"
echo "     sudo systemctl start $SERVICE_NAME"
echo ""
echo "  3. Check status:"
echo "     sudo systemctl status $SERVICE_NAME"
echo "     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "IMPORTANT: Never commit the actual env file to git!"
echo "           Only the .example file should be in the repo."
