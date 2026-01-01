#!/bin/bash
# Deployment script for Dynamic Multi-Pair Unified Strategy
# Deploys to Google Cloud VM

set -e

echo "=========================================="
echo "Deploying Dynamic Multi-Pair Unified Strategy"
echo "=========================================="

# Configuration
VM_NAME="ai-quant-trading-vm"
ZONE="us-central1-a"
PROJECT="ai-quant-trading"
REMOTE_DIR="/opt/quant_system_clean/google-cloud-trading-system"
LOCAL_BASE="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"

# Files to deploy
FILES=(
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/dynamic_multi_pair_unified.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/trade_with_pat_orb_dual.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/gold_scalping_winrate.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/gold_scalping_strict1.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/gold_scalping_topdown.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/optimized_multi_pair_live.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/registry.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/analytics/topdown_analysis.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/analytics/topdown_scheduler.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/dashboard/advanced_dashboard.py"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/AI_QUANT_credentials/strategy_configs/trade_with_pat_orb_dual_session.yaml"
    "Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/LIVE_TRADING_CONFIG_UNIFIED.yaml"
)

echo ""
echo "Step 1: Setting up gcloud context..."
gcloud config set project $PROJECT
gcloud config set compute/zone $ZONE

echo ""
echo "Step 2: Copying files to VM..."
for file in "${FILES[@]}"; do
    local_path="$LOCAL_BASE/$file"
    if [ ! -f "$local_path" ]; then
        echo "⚠️  Warning: File not found: $local_path"
        continue
    fi
    
    # Determine remote path
    if [[ $file == *"src/strategies"* ]]; then
        remote_path="$REMOTE_DIR/src/strategies/$(basename "$file")"
    elif [[ $file == *"src/analytics"* ]]; then
        remote_path="$REMOTE_DIR/src/analytics/$(basename "$file")"
    elif [[ $file == *"src/dashboard"* ]]; then
        remote_path="$REMOTE_DIR/src/dashboard/$(basename "$file")"
    elif [[ $file == *"accounts.yaml"* ]]; then
        remote_path="$REMOTE_DIR/AI_QUANT_credentials/accounts.yaml"
    elif [[ $file == *"strategy_configs"* ]]; then
        remote_path="$REMOTE_DIR/AI_QUANT_credentials/strategy_configs/$(basename "$file")"
    elif [[ $file == *"LIVE_TRADING_CONFIG_UNIFIED.yaml"* ]]; then
        remote_path="$REMOTE_DIR/LIVE_TRADING_CONFIG_UNIFIED.yaml"
    else
        echo "⚠️  Warning: Unknown file path: $file"
        continue
    fi
    
    echo "   Copying: $(basename "$file")"
    gcloud compute scp "$local_path" "$VM_NAME:$remote_path" --zone=$ZONE
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Copied successfully"
    else
        echo "   ❌ Failed to copy"
        exit 1
    fi
done

echo ""
echo "Step 3: Restarting trading service..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="sudo systemctl restart ai_trading.service"

echo ""
echo "Step 4: Checking service status..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="sudo systemctl status ai_trading.service --no-pager | head -20"

echo ""
echo "Step 5: Checking recent logs..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="journalctl -u ai_trading.service -n 50 --no-pager | grep -i 'dynamic\|strategy\|error' || echo 'No relevant log entries'"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Monitor logs: journalctl -u ai_trading.service -f"
echo "2. Check account status via Telegram: /status"
echo "3. Verify strategy is active on account 101-004-30719775-011"
echo "4. Monitor first trades closely"
echo ""



