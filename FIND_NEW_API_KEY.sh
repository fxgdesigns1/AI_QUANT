#!/bin/bash
# Search for the new API key the user gave me

echo "Searching for NEW API key you provided..."
echo "==========================================="
echo ""

# Check Google Drive sync
echo "[1] Checking Google Drive credentials..."
if [ -f "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/oanda_config.env" ]; then
    echo "Found in Google Drive:"
    grep "OANDA_API_KEY" "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/oanda_config.env"
else
    echo "Not found in Google Drive"
fi
echo ""

# Check local project
echo "[2] Checking local project files..."
grep -h "OANDA_API_KEY" google-cloud-trading-system/oanda_config.env 2>/dev/null
echo ""

# Check if there's a symlink
echo "[3] Checking for symlinks..."
ls -la google-cloud-trading-system/oanda_config.env 2>/dev/null
echo ""

# Check accounts.yaml for API key
echo "[4] Checking accounts.yaml..."
if [ -f "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml" ]; then
    grep -i "api" "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml" | head -5
fi
echo ""

echo "==========================================="
echo "Please tell me which of these API keys is the NEW one you gave me."
echo "Or paste the NEW API key here so I can update all files correctly."

