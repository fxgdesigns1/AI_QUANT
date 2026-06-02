#!/usr/bin/env bash
# Setup FXG Watchdog Service with PM2
# Installs PM2, configures the watchdog, and starts monitoring
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== FXG Watchdog Service Setup ==="
echo "Script directory: $SCRIPT_DIR"
echo "Root directory: $ROOT_DIR"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js first."
    echo "Suggested commands:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js found: $NODE_VERSION"

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    npm install -g pm2

    # Configure PM2 startup
    echo "Configuring PM2 startup..."
    pm2 startup

    echo "✅ PM2 installed and configured"
else
    echo "✅ PM2 already installed: $(pm2 --version)"
fi

# Create necessary directories
echo "Creating log directories..."
sudo mkdir -p /opt/ai-quant/logs /opt/ai-quant/scripts
sudo chown -R $(whoami):$(whoami) /opt/ai-quant/logs

# Copy scripts to /opt/ai-quant/scripts if not already there
TARGET_SCRIPT="/opt/ai-quant/scripts/fxg-watchdog.js"
TARGET_CONFIG="/opt/ai-quant/scripts/ecosystem.config.js"

if [[ "$SCRIPT_DIR" != "/opt/ai-quant/scripts" ]]; then
    echo "Copying scripts to /opt/ai-quant/scripts..."
    sudo cp "$SCRIPT_DIR/fxg-watchdog.js" "$TARGET_SCRIPT"
    sudo cp "$SCRIPT_DIR/ecosystem.config.js" "$TARGET_CONFIG"
    sudo chown $(whoami):$(whoami) "$TARGET_SCRIPT" "$TARGET_CONFIG"
    sudo chmod +x "$TARGET_SCRIPT"
fi

# Test the watchdog script
echo "Testing watchdog script..."
cd /opt/ai-quant/scripts
if node fxg-watchdog.js --version &> /dev/null; then
    echo "✅ Watchdog script syntax OK"
else
    echo "❌ Watchdog script has issues"
    exit 1
fi

# Stop existing watchdog if running
echo "Stopping any existing FXG watchdog..."
pm2 delete fxg-watchdog 2>/dev/null || true

# Start the watchdog service
echo "Starting FXG watchdog service..."
pm2 start ecosystem.config.js

# Save PM2 configuration
echo "Saving PM2 configuration..."
pm2 save

# Show service status
echo ""
echo "=== FXG Watchdog Service Status ==="
pm2 status fxg-watchdog

echo ""
echo "=== Service Information ==="
echo "Service name: fxg-watchdog"
echo "Check interval: 60 seconds"
echo "Log files:"
echo "  - Main: /opt/ai-quant/logs/fxg-watchdog.log"
echo "  - Error: /opt/ai-quant/logs/fxg-watchdog-error.log"
echo "  - Output: /opt/ai-quant/logs/fxg-watchdog-out.log"

echo ""
echo "=== Useful PM2 Commands ==="
echo "View logs:     pm2 logs fxg-watchdog"
echo "Restart:       pm2 restart fxg-watchdog"
echo "Stop:          pm2 stop fxg-watchdog"
echo "Monitor:       pm2 monit"
echo "Status:        pm2 status fxg-watchdog"

echo ""
echo "✅ FXG Watchdog Service Setup Complete!"
echo ""
echo "The watchdog will now monitor these components every 60 seconds:"
echo "  • ai-quant-control-plane service"
echo "  • ai-quant-runner service"
echo "  • EA heartbeat (via sidecar)"
echo "  • Preflight status"
echo "  • Signal file size"
echo "  • Windows pull loop status"
echo ""
echo "Telegram alerts will be sent for any failures with exact fix commands."