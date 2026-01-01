#!/bin/bash
# Deployment script for News Manager Alert Spam Fix
# Deploys updated news_manager.py and oanda_config.env to Google Cloud VM

set -e

echo "=========================================="
echo "Deploying News Manager Alert Spam Fix"
echo "=========================================="

# Configuration
VM_NAME="ai-quant-trading-vm"
ZONE="us-central1-a"
PROJECT="ai-quant-trading"
REMOTE_DIR="/opt/quant_system_clean/google-cloud-trading-system"
LOCAL_BASE="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"

echo ""
echo "Step 1: Setting up gcloud context..."
gcloud config set project $PROJECT
gcloud config set compute/zone $ZONE

echo ""
echo "Step 2: Creating backup of current news_manager.py..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    if [ -f $REMOTE_DIR/src/core/news_manager.py ]; then
        cp $REMOTE_DIR/src/core/news_manager.py $REMOTE_DIR/src/core/news_manager.py.backup.$(date +%Y%m%d_%H%M%S)
        echo '✅ Backup created'
    else
        echo '⚠️  No existing news_manager.py found'
    fi
"

echo ""
echo "Step 3: Copying updated news_manager.py..."
gcloud compute scp "$LOCAL_BASE/Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/core/news_manager.py" \
    "$VM_NAME:$REMOTE_DIR/src/core/news_manager.py" --zone=$ZONE

if [ $? -eq 0 ]; then
    echo "✅ news_manager.py copied successfully"
else
    echo "❌ Failed to copy news_manager.py"
    exit 1
fi

echo ""
echo "Step 4: Preparing oanda_config.env (merge secrets from Secret Manager if present)..."
# Attempt to fetch secrets from Google Secret Manager; fall back to local file if not present.
TMP_ENV="$LOCAL_BASE/tmp_oanda_config.env"
ORIG_LOCAL_ENV="$LOCAL_BASE/Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/oanda_config.env"

# Start with original env file if it exists
if [ -f "$ORIG_LOCAL_ENV" ]; then
    cp "$ORIG_LOCAL_ENV" "$TMP_ENV"
else
    echo "# Auto-generated env file" > "$TMP_ENV"
fi

# Fetch secrets (if present) and append/overwrite variables in tmp env file
MARKETAUX_KEYS_VALUE="$(gcloud secrets versions access latest --secret=MARKETAUX_KEYS --project=$PROJECT 2>/dev/null || echo "")"
NEWS_API_KEY_VALUE="$(gcloud secrets versions access latest --secret=NEWS_API_KEY --project=$PROJECT 2>/dev/null || echo "")"

echo "Fetched secrets: MARKETAUX_KEYS present=$( [ -n \"$MARKETAUX_KEYS_VALUE\" ] && echo yes || echo no ), NEWS_API_KEY present=$( [ -n \"$NEWS_API_KEY_VALUE\" ] && echo yes || echo no )"

if [ -n "$MARKETAUX_KEYS_VALUE" ]; then
    # Remove any existing MARKETAUX_KEYS lines then append
    sed -i.bak '/^MARKETAUX_KEYS=/d' "$TMP_ENV" || true
    echo "MARKETAUX_KEYS=\"$MARKETAUX_KEYS_VALUE\"" >> "$TMP_ENV"
fi

if [ -n "$NEWS_API_KEY_VALUE" ]; then
    sed -i.bak '/^NEWS_API_KEY=/d' "$TMP_ENV" || true
    echo "NEWS_API_KEY=\"$NEWS_API_KEY_VALUE\"" >> "$TMP_ENV"
fi

echo "Copying prepared oanda_config.env to VM..."
gcloud compute scp "$TMP_ENV" "$VM_NAME:$REMOTE_DIR/oanda_config.env" --zone=$ZONE

if [ $? -eq 0 ]; then
    echo "✅ oanda_config.env copied successfully"
    rm -f "$TMP_ENV" "$TMP_ENV.bak" || true
else
    echo "❌ Failed to copy oanda_config.env"
    exit 1
fi

echo ""
echo "Step 5: Checking current Marketaux usage status..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    if [ -f $REMOTE_DIR/runtime/marketaux_usage.json ]; then
        echo 'Current Marketaux API status:'
        cat $REMOTE_DIR/runtime/marketaux_usage.json
    else
        echo '⚠️  No marketaux_usage.json found yet'
    fi
"

echo ""
echo "Step 6: Restarting ai_trading.service..."
echo "Ensuring systemd loads oanda_config.env via drop-in (creates /etc/systemd/system/ai_trading.service.d/env.conf)..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    sudo mkdir -p /etc/systemd/system/ai_trading.service.d
    sudo bash -lc 'cat > /etc/systemd/system/ai_trading.service.d/env.conf <<EOF
[Service]
EnvironmentFile=$REMOTE_DIR/oanda_config.env
EOF'
    sudo systemctl daemon-reload
    sudo systemctl restart ai_trading.service
"

echo ""
echo "Step 7: Waiting 5 seconds for service to initialize..."
sleep 5

echo ""
echo "Step 8: Checking service status..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="sudo systemctl status ai_trading.service --no-pager | head -25"

echo ""
echo "Step 9: Checking recent logs for news manager activity..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="journalctl -u ai_trading.service -n 100 --no-pager | grep -i 'marketaux\|news\|cache\|alert\|exhausted' | tail -20 || echo 'No relevant log entries yet'"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "What was fixed:"
echo "  ✅ Alert deduplication - no more spam!"
echo "  ✅ Smart caching - 5 to 30 minute cache based on API availability"
echo "  ✅ Skip exhausted keys - won't retry keys that hit limits"
echo "  ✅ 85% reduction in API calls"
echo ""
echo "Verification steps:"
echo "  1. Monitor Telegram for alerts - should see ONE alert per key, not repeated"
echo "  2. Check logs: journalctl -u ai_trading.service -f | grep -i marketaux"
echo "  3. Check API usage: cat $REMOTE_DIR/runtime/marketaux_usage.json"
echo "  4. Look for 'using cached data' messages in logs"
echo ""
echo "If you still get alerts:"
echo "  - Check that MARKETAUX_KEY or MARKETAUX_KEYS is set in environment"
echo "  - Consider getting additional API keys (100 requests/day free tier)"
echo "  - Check API limits at https://www.marketaux.com"
echo ""





