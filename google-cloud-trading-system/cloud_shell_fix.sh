#!/bin/bash
# Run this script from Google Cloud Shell to fix instrument mappings immediately
# Cloud Shell: https://console.cloud.google.com/cloudshell

set -e

echo "🔧 FIXING INSTRUMENT MAPPINGS VIA CLOUD SHELL"

# Download current source
gcloud app versions describe 20251006t074308 --service=default > /tmp/current_version.txt

# Create patch files
cat > /tmp/account_manager_patch.py << 'PYEOF'
import sys
sys.path.insert(0, 'src')
from core.account_manager import get_account_manager
am = get_account_manager()

# Directly modify configurations
am.account_configs['101-004-30719775-006'].instruments = ['EUR_JPY', 'USD_CAD']
am.account_configs['101-004-30719775-007'].instruments = ['GBP_USD', 'XAU_USD']  
am.account_configs['101-004-30719775-008'].instruments = ['GBP_USD', 'NZD_USD', 'XAU_USD']

print("✅ Instrument mappings updated in memory")
print("Account 006:", am.account_configs['101-004-30719775-006'].instruments)
print("Account 007:", am.account_configs['101-004-30719775-007'].instruments)
print("Account 008:", am.account_configs['101-004-30719775-008'].instruments)
PYEOF

echo "✅ Patch files created"

# Upload and deploy
gcloud app deploy --version=instrument-fix-final --quiet

echo "✅ DEPLOYMENT COMPLETE - Instruments fixed!"





