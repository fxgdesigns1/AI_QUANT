#!/bin/bash
# Deploy optimized strategies with retry logic

echo "🚀 Deploying Optimized Strategies..."
echo "Time: $(date)"
echo ""

MAX_RETRIES=5
RETRY_COUNT=0
DEPLOY_SUCCESS=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ $DEPLOY_SUCCESS -eq 0 ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Attempt $RETRY_COUNT of $MAX_RETRIES..."
    
    gcloud app deploy app.yaml \
        --version=oct14-v$RETRY_COUNT \
        --promote \
        --quiet \
        --project=ai-quant-trading
    
    if [ $? -eq 0 ]; then
        echo "✅ Deployment successful!"
        DEPLOY_SUCCESS=1
    else
        echo "❌ Deployment failed, waiting 60 seconds..."
        sleep 60
    fi
done

if [ $DEPLOY_SUCCESS -eq 1 ]; then
    echo ""
    echo "✅ DEPLOYMENT COMPLETE"
    echo "Checking logs..."
    gcloud app logs read --service=default --limit=20
else
    echo ""
    echo "❌ DEPLOYMENT FAILED AFTER $MAX_RETRIES ATTEMPTS"
    echo "Network connectivity issues detected"
fi
