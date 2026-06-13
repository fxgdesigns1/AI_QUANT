#!/bin/bash
# Setup Cloudflare Tunnel for always-accessible secure dashboard access
# Zero new GCP resources (no LB, no static IP)
# Uses Cloudflare Tunnel (outbound-only) + Cloudflare Access (Google sign-in)

set -euo pipefail

VM="${1:-fxg-quant-paper-e2-micro}"
ZONE="${2:-us-east1-b}"
PROJECT="${3:-fxg-ai-trading}"

echo "=== SETTING UP CLOUDFLARE TUNNEL FOR ALPHA VM ==="
echo "VM: $VM"
echo "ZONE: $ZONE"
echo "PROJECT: $PROJECT"
echo ""
echo "⚠️  PREREQUISITES:"
echo "1. Cloudflare account with Zero Trust (Free plan supports up to 50 users)"
echo "2. Domain configured in Cloudflare"
echo "3. Cloudflare Tunnel created via: cloudflared tunnel create ai-quant-dashboard"
echo "4. Tunnel credentials file (JSON) saved securely"
echo "5. Cloudflare Access application configured with Google IdP"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Install cloudflared if not present
if ! command -v cloudflared &> /dev/null; then
    echo "=== Installing cloudflared ==="
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
    sudo dpkg -i /tmp/cloudflared.deb || sudo apt-get install -f -y
    rm /tmp/cloudflared.deb
else
    echo "✅ cloudflared already installed"
fi

# Create cloudflared config directory
sudo mkdir -p /etc/cloudflared
sudo chmod 700 /etc/cloudflared

echo ""
echo "=== CONFIGURATION REQUIRED ==="
echo "You need to provide:"
echo "1. Tunnel credentials file path (JSON from Cloudflare)"
echo "2. Your domain name (e.g., dashboard.yourdomain.com)"
read -p "Tunnel credentials JSON file path: " TUNNEL_CRED_FILE
read -p "Domain name (e.g., dashboard.yourdomain.com): " DOMAIN_NAME

# Copy tunnel credentials
sudo cp "$TUNNEL_CRED_FILE" /etc/cloudflared/credentials.json
sudo chmod 600 /etc/cloudflared/credentials.json

# Create config file
sudo tee /etc/cloudflared/config.yaml > /dev/null <<EOF
tunnel: $(cat "$TUNNEL_CRED_FILE" | grep -o '"TunnelID":"[^"]*"' | cut -d'"' -f4)
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: $DOMAIN_NAME
    service: http://127.0.0.1:8787
  - service: http_status:404
EOF

sudo chmod 600 /etc/cloudflared/config.yaml

# Create systemd service
sudo tee /etc/systemd/system/cloudflared-tunnel.service > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel for AI Quant Dashboard
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel --config /etc/cloudflared/config.yaml run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable cloudflared-tunnel.service
sudo systemctl start cloudflared-tunnel.service

echo ""
echo "=== VERIFICATION ==="
sleep 3
if sudo systemctl is-active --quiet cloudflared-tunnel.service; then
    echo "✅ Cloudflare Tunnel service is active"
else
    echo "❌ Cloudflare Tunnel service failed to start"
    echo "Check logs: sudo journalctl -u cloudflared-tunnel -n 50"
    exit 1
fi

echo ""
echo "=== NEXT STEPS ==="
echo "1. Verify tunnel is running: sudo systemctl status cloudflared-tunnel"
echo "2. Check tunnel logs: sudo journalctl -u cloudflared-tunnel -f"
echo "3. Configure Cloudflare Access:"
echo "   - Go to Cloudflare Zero Trust Dashboard"
echo "   - Create Access Application for $DOMAIN_NAME"
echo "   - Set up Google identity provider"
echo "   - Add access policy (email allowlist)"
echo "4. Test access: https://$DOMAIN_NAME"
echo ""
echo "✅ Setup complete!"
