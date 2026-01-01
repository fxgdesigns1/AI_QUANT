#!/bin/bash
# Deploy fixes and restart trading system on Google Cloud VM

set -e

PROJECT="ai-quant-trading"
ZONE="us-central1-a"
VM_NAME="ai-quant-trading-vm"
VM_PATH="/opt/quant_system_clean"
CAPACITY_PERCENT=${CAPACITY_PERCENT:-75}
TIMEZONE=${TIMEZONE:-Europe/London}

echo "=========================================="
echo "DEPLOYING FIXES TO PRODUCTION"
echo "=========================================="

# Set project
echo "Setting project context..."
gcloud config set project $PROJECT
gcloud config set compute/zone $ZONE

# Copy updated files to VM
echo ""
echo "Copying updated files to VM..."

# Copy main trading system file
echo "  - Copying ai_trading_system_FIXED.py..."
gcloud compute scp "ai_trading_system_FIXED.py" $VM_NAME:$VM_PATH/ \
    --zone=$ZONE

# Copy the entire src directory
echo "  - Copying the entire src directory..."
gcloud compute scp --recurse "src" $VM_NAME:$VM_PATH/google-cloud-trading-system/ \
    --zone=$ZONE

echo ""
echo "Applying capacity and timezone configuration on VM..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
  set -e
  CONFIG_DIR=\"$VM_PATH/google-cloud-trading-system/config\"
  mkdir -p \"$CONFIG_DIR\"
  cat > \"$CONFIG_DIR/capacity.yaml\" << 'YAML'
capacity_percentage: ${CAPACITY_PERCENT}
YAML
  cat > \"$CONFIG_DIR/timezone.yaml\" << 'YAML'
timezone: ${TIMEZONE}
YAML
  mkdir -p \"$VM_PATH/LOGS\"
  echo \"$(date) - Set capacity to ${CAPACITY_PERCENT}%, timezone to ${TIMEZONE}\" >> \"$VM_PATH/LOGS/deployment_capacity.log\"
"

echo ""
echo "Files copied successfully!"

# Restart service
echo ""
echo "Restarting ai_trading.service..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    export PYTHONPATH=$PYTHONPATH:/opt/quant_system_clean/google-cloud-trading-system/
    sudo systemctl restart ai_trading.service
    sleep 2
    sudo systemctl status ai_trading.service --no-pager -l
"

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Next: Check logs to verify strategies are loading"
echo "Command: gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo journalctl -u ai_trading.service -n 50 --no-pager'"



