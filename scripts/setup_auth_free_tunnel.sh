#!/bin/bash
# Setup Auth-Free Cloudflare Tunnel for Playwright Testing
# 
# This script sets up a persistent tunnel to expose the dashboard
# WITHOUT Cloudflare Access (publicly accessible via tunnel)
# strictly for Playwright testing purposes.
#
# Usage: ./setup_auth_free_tunnel.sh

set -euo pipefail

TUNNEL_NAME="fxg-alpha-dashboard"
HOSTNAME="alpha-dashboard.fxg.internal"
SERVICE_URL="http://127.0.0.1:8787"
CRED_FILE="/etc/cloudflared/credentials.json"
CONFIG_FILE="/etc/cloudflared/config.yml"

echo "=== SETUP AUTH-FREE TUNNEL FOR PLAYWRIGHT ==="
echo "Target Tunnel: $TUNNEL_NAME"
echo "Hostname: $HOSTNAME"
echo "Backend Service: $SERVICE_URL"
echo ""

# 1. Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "⬇️  Installing cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
    echo "✅ cloudflared installed"
else
    echo "✅ cloudflared already installed"
fi

# 2. Authenticate
if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo "⚠️  Authentication required."
    echo "   Please run the following command and log in via the browser:"
    echo "   cloudflared tunnel login"
    echo ""
    echo "   After logging in, re-run this script."
    exit 1
fi

# 3. Create Tunnel
echo "Checking for tunnel '$TUNNEL_NAME'..."
if ! cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo "Creating tunnel..."
    cloudflared tunnel create "$TUNNEL_NAME"
    echo "✅ Tunnel created"
else
    echo "✅ Tunnel already exists"
fi

# Get Tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
echo "Tunnel ID: $TUNNEL_ID"

# 4. Configure
echo "Configuring tunnel..."
sudo mkdir -p /etc/cloudflared

# Copy credentials if they are in the default location
if [ -f ~/.cloudflared/"$TUNNEL_ID".json ]; then
    sudo cp ~/.cloudflared/"$TUNNEL_ID".json "$CRED_FILE"
fi

if [ ! -f "$CRED_FILE" ]; then
    echo "❌ Credentials file not found at $CRED_FILE"
    echo "   Ensure ~/.cloudflared/$TUNNEL_ID.json exists and try again."
    exit 1
fi

# Create Config
cat <<EOF | sudo tee "$CONFIG_FILE"
tunnel: $TUNNEL_ID
credentials-file: $CRED_FILE

ingress:
  - hostname: $HOSTNAME
    service: $SERVICE_URL
  - service: http_status:404
EOF

echo "✅ Configuration written to $CONFIG_FILE"

# 5. Route DNS (Virtual)
echo "📝 NOTE: To bind DNS, you would normally run:"
echo "   cloudflared tunnel route dns $TUNNEL_NAME $HOSTNAME"
echo "   Since '$HOSTNAME' ends in .internal, make sure your network supports this"
echo "   or use a real domain managed by Cloudflare."

# 6. Install Service
echo "Installing systemd service..."
sudo cloudflared service install || echo "Service might already be installed"

echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl restart cloudflared
sudo systemctl enable cloudflared

echo ""
echo "=== SETUP COMPLETE ==="
echo "Tunnel Status:"
sudo systemctl status cloudflared --no-pager

echo ""
echo "To verify:"
echo "curl -I https://$HOSTNAME"
