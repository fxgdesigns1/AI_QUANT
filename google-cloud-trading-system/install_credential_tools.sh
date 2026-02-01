#!/bin/bash

# AI Quant Trading System - Credential Tools Installation
# ======================================================

echo "🚀 Installing AI Quant Credential Management Tools"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "quick_credential_setup.py" ]; then
    echo "❌ Error: Please run this script from the google-cloud-trading-system directory"
    exit 1
fi

# Install required Python packages
echo "📦 Installing required Python packages..."

pip install --upgrade pip

# Core packages
pip install pyyaml flask

# Google Drive API packages (optional)
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# QR code packages (optional)
pip install qrcode[pil]

echo "✅ Python packages installed"

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x *.py
chmod +x install_credential_tools.sh

echo "✅ Scripts made executable"

# Create credentials directory
echo "📁 Creating credentials directory..."
mkdir -p credentials

echo "✅ Credentials directory created"

# Test installation
echo "🧪 Testing installation..."

if python3 -c "import yaml, flask, json" 2>/dev/null; then
    echo "✅ Core dependencies working"
else
    echo "❌ Core dependencies failed - please check Python installation"
    exit 1
fi

echo ""
echo "🎉 Installation Complete!"
echo "========================"
echo ""
echo "Available tools:"
echo "  📱 Mobile Interface:    python mobile_credential_uploader.py --start-server"
echo "  ⚡ Quick Setup:         python quick_credential_setup.py"
echo "  ☁️  Google Drive Sync:   python gdrive_credential_sync.py --setup"
echo "  🔧 Credential Manager:  python credential_manager.py --help"
echo ""
echo "📖 For detailed instructions, see: CREDENTIAL_WORKAROUNDS.md"
echo ""
echo "🚀 Ready to set up your credentials!"