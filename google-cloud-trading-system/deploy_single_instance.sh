#!/bin/bash
# Deploy Single Instance Optimized Version
# 75% cost reduction: 4 instances → 1 instance

echo "🚀 DEPLOYING SINGLE INSTANCE OPTIMIZATION"
echo "=========================================="
echo "Cost Reduction: 75% (4 instances → 1 instance)"
echo "Strategy Groups: All 3 groups on 1 F2 instance"
echo ""

# Backup current app.yaml
cp app.yaml app_multi_instance_backup.yaml
echo "✅ Backed up current app.yaml"

# Use optimized single instance configuration
cp app_single_instance.yaml app.yaml
echo "✅ Applied single instance optimization"

# Deploy to Google Cloud
echo "📦 Deploying single instance version..."
gcloud app deploy --quiet

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SINGLE INSTANCE DEPLOYMENT SUCCESSFUL!"
    echo "========================================"
    echo "✅ All 3 strategy groups running on 1 F2 instance"
    echo "💰 Expected cost reduction: 75%"
    echo "📊 New monthly cost: ~$60-90 (vs $230-350)"
    echo ""
    echo "🔍 Verify deployment:"
    echo "gcloud app instances list"
    echo ""
    echo "📊 Monitor performance:"
    echo "gcloud app logs tail -s default"
else
    echo "❌ Deployment failed - restoring backup"
    cp app_multi_instance_backup.yaml app.yaml
    echo "✅ Restored original configuration"
    exit 1
fi
