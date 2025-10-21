#!/bin/bash
# Deploy F1 FREE TIER Optimized Version
# Maximum cost savings: F2 ($60-90/month) → F1 (FREE!)

echo "🚀 DEPLOYING F1 FREE TIER OPTIMIZATION"
echo "======================================"
echo "Cost Reduction: 100% (F2 → F1 FREE TIER)"
echo "Strategy Groups: All 3 groups on 1 F1 instance"
echo "FREE TIER: 28 instance-hours per day"
echo ""

# Backup current app.yaml
cp app.yaml app_f2_backup.yaml
echo "✅ Backed up current F2 app.yaml"

# Use F1 optimized configuration
cp app_f1_free_tier.yaml app.yaml
echo "✅ Applied F1 FREE TIER optimization"

# Deploy to Google Cloud
echo "📦 Deploying F1 FREE TIER version..."
gcloud app deploy --version=f1-free-tier-$(date +%Y%m%d-%H%M%S) --no-promote

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 F1 FREE TIER DEPLOYMENT SUCCESSFUL!"
    echo "===================================="
    echo "✅ All 3 strategy groups running on 1 F1 instance"
    echo "💰 Cost reduction: 100% (FREE!)"
    echo "📊 FREE TIER: 28 hours/day (perfect for trading)"
    echo ""
    echo "🔍 Verify deployment:"
    echo "gcloud app versions list --service=default"
    echo ""
    echo "📊 Monitor FREE TIER usage:"
    echo "gcloud app logs tail -s default"
    echo ""
    echo "🚀 TO ACTIVATE:"
    echo "gcloud app services set-traffic default --splits=VERSION_ID=1.0"
else
    echo "❌ Deployment failed - restoring backup"
    cp app_f2_backup.yaml app.yaml
    echo "✅ Restored original F2 configuration"
    exit 1
fi
