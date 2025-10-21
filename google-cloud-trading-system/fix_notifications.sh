#!/bin/bash

echo "=================================================="
echo "🔧 FIXING TRADING SYSTEM NOTIFICATIONS & CRON JOBS"
echo "=================================================="
echo ""

# Step 1: Deploy cron jobs
echo "📅 Step 1: Deploying cron jobs..."
echo "--------------------------------------------------"
gcloud app deploy cron.yaml --quiet
if [ $? -eq 0 ]; then
    echo "✅ Cron jobs deployed successfully!"
else
    echo "❌ Failed to deploy cron jobs"
    exit 1
fi
echo ""

# Step 2: Verify cron jobs
echo "🔍 Step 2: Verifying cron jobs..."
echo "--------------------------------------------------"
gcloud app cron list
echo ""

# Step 3: Test Telegram notification
echo "📱 Step 3: Testing Telegram notification..."
echo "--------------------------------------------------"
python3 diagnostic_and_fix.py
echo ""

# Step 4: Trigger manual scan
echo "🔄 Step 4: Triggering manual scan to test notifications..."
echo "--------------------------------------------------"
curl -X POST "https://ai-quant-trading.uc.r.appspot.com/tasks/full_scan" -H "Content-Type: application/json" -w "\nHTTP Status: %{http_code}\n"
echo ""

# Step 5: Check recent logs
echo "📋 Step 5: Checking recent logs for scan activity..."
echo "--------------------------------------------------"
gcloud app logs read --service=default --limit=20 | grep -E "(scan|telegram|notification)" | tail -10
echo ""

echo "=================================================="
echo "✅ FIX COMPLETE - CHECK TELEGRAM FOR NOTIFICATIONS"
echo "=================================================="
