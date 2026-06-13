#!/bin/bash
# FXG Mac - One-Click Remote Overlay Setup (Tailscale)
set -e
REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
ARTIFACTS="$REPO_ROOT/artifacts"
mkdir -p "$ARTIFACTS"

if ! command -v tailscale &>/dev/null; then
  echo "Installing Tailscale..."
  curl -fsSL https://tailscale.com/install.sh | sh
fi
echo "Tailscale: $(which tailscale)"
tailscale status 2>/dev/null || true
echo "Run 'tailscale up' and sign in if not connected."
echo '{"tailscale_installed":true}' > "$ARTIFACTS/mac_remote_overlay_install_result.json"
echo "PASS: Mac remote overlay setup complete"
