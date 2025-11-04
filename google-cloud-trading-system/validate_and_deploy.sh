#!/bin/bash
# Validate-Then-Deploy Workflow
# NO MORE BLIND DEPLOYMENTS! Validate first, deploy only when proven to work.

echo "🔍 VALIDATE-THEN-DEPLOY WORKFLOW"
echo "================================="
echo ""

# Step 1: Run pre-deployment validation
echo "Step 1: Validating all strategies against last 4 hours of REAL market data..."
echo ""

python3 pre_deploy_check.py

VALIDATION_RESULT=$?

if [ $VALIDATION_RESULT -ne 0 ]; then
    echo ""
    echo "❌ VALIDATION FAILED - Stopping deployment"
    echo ""
    echo "Options:"
    echo "  1. Run auto_tune_parameters.py to get recommendations"
    echo "  2. Manually adjust strategy parameters"
    echo "  3. Re-run this script after fixing"
    echo ""
    exit 1
fi

# Step 2: Show auto-tuning recommendations
echo ""
echo "Step 2: Checking auto-tuning recommendations..."
echo ""

python3 auto_tune_parameters.py

# Step 3: Ask for confirmation
echo ""
echo "Step 3: Validation passed. Ready to deploy to production."
echo ""
echo "⚠️  This will deploy to Google Cloud and replace current version."
echo ""
read -p "Type 'yes' to deploy: " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled by user"
    exit 0
fi

# Step 4: Create backup
echo ""
echo "Step 4: Creating backup..."
BACKUP_DIR="backups/pre_deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

cp -r src/strategies/*.py "$BACKUP_DIR/" 2>/dev/null
cp strategy_config.yaml "$BACKUP_DIR/" 2>/dev/null
cp app.yaml "$BACKUP_DIR/" 2>/dev/null

echo "✅ Backup created: $BACKUP_DIR"

# Step 5: Deploy
echo ""
echo "Step 5: Deploying validated strategies to Google Cloud..."
echo ""

VERSION_NAME="validated-$(date +%Y%m%d-%H%M)"

gcloud app deploy app.yaml \
    --version="$VERSION_NAME" \
    --promote \
    --quiet \
    --project=ai-quant-trading

if [ $? -eq 0 ]; then
    echo ""
    echo "=" * 80
    echo "✅ VALIDATED DEPLOYMENT COMPLETE"
    echo "=" * 80
    echo ""
    echo "Version: $VERSION_NAME"
    echo "Time: $(date)"
    echo "Status: LIVE"
    echo ""
    echo "🎯 What was validated:"
    echo "  • All 10 strategies tested against last 4 hours"
    echo "  • Expected signal generation confirmed"
    echo "  • Quality thresholds verified"
    echo "  • Deployment safe to proceed"
    echo ""
    echo "📊 Monitor deployment:"
    echo "  gcloud app logs tail --service=default"
    echo ""
else
    echo ""
    echo "❌ DEPLOYMENT FAILED"
    echo "Check errors above and retry"
    echo ""
    exit 1
fi




















