#!/bin/bash

# =============================================================================
# MANUAL TRADING START - OVERRIDE WEEKEND MODE
# =============================================================================
# This script manually starts trading by overriding weekend mode
# Use this when market is open but system thinks it's weekend
# =============================================================================

set -e

echo "🚀 MANUALLY STARTING TRADING SYSTEM"
echo "=" * 50

# Set environment variables to override weekend mode
export WEEKEND_MODE=false
export TRADING_DISABLED=false
export SIGNAL_GENERATION=enabled

echo "✅ Environment variables set:"
echo "   WEEKEND_MODE=false"
echo "   TRADING_DISABLED=false"
echo "   SIGNAL_GENERATION=enabled"
echo ""

# Update app.yaml with environment variables
echo "📝 Updating app.yaml with trading enabled..."

cat > app.yaml << 'EOF'
runtime: python39
instance_class: F2

env_variables:
  WEEKEND_MODE: "false"
  TRADING_DISABLED: "false"
  SIGNAL_GENERATION: "enabled"

automatic_scaling:
  target_cpu_utilization: 0.65
  min_instances: 1
  max_instances: 5

handlers:
- url: /static
  static_dir: src/static
  secure: always

- url: /.*
  script: auto
  secure: always
EOF

echo "✅ app.yaml updated with trading enabled"
echo ""

echo "🚀 Deploying to Google Cloud..."
gcloud app deploy --quiet

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "🎯 Trading system is now ACTIVE"
echo "📊 Monitor at: https://ai-quant-trading.uc.r.appspot.com"
echo ""
echo "⚠️  IMPORTANT:"
echo "   - System will now execute trades"
echo "   - Weekend mode is DISABLED"
echo "   - All 4 strategies are ACTIVE"
echo "   - Monitor Telegram for signals"
echo ""





