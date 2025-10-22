#!/bin/bash
# Quick Cloud Deployment for Trading Analytics System
# Simplified deployment to Google Cloud Run

set -e

echo "=========================================="
echo "QUICK CLOUD DEPLOYMENT - TRADING ANALYTICS"
echo "=========================================="

# Configuration - UPDATE THESE VALUES
PROJECT_ID="ai-quant-trading"  # Replace with your Google Cloud project ID
SERVICE_NAME="trading-analytics"
REGION="us-central1"

echo "📋 Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Not logged into gcloud. Please run:"
    echo "   gcloud auth login"
    exit 1
fi

# Set project
echo "🔧 Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling APIs..."
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create OANDA credentials secret if it doesn't exist
echo "🔐 Setting up OANDA credentials..."
if ! gcloud secrets describe oanda-credentials >/dev/null 2>&1; then
    echo "Creating OANDA credentials secret..."
    echo "Please enter your OANDA credentials:"
    
    # Create secret with multiple key-value pairs
    {
        echo "api-key: $(echo -n "Enter your OANDA API key: " && read -s API_KEY && echo $API_KEY)"
        echo "primary-account: $(echo -n "Enter primary account ID: " && read PRIMARY_ACCOUNT && echo $PRIMARY_ACCOUNT)"
        echo "gold-account: $(echo -n "Enter gold account ID: " && read GOLD_ACCOUNT && echo $GOLD_ACCOUNT)"
        echo "alpha-account: $(echo -n "Enter alpha account ID: " && read ALPHA_ACCOUNT && echo $ALPHA_ACCOUNT)"
    } | gcloud secrets create oanda-credentials --data-file=-
else
    echo "✅ OANDA credentials secret already exists"
fi

# Build and push Docker image
echo "🐳 Building Docker image..."
docker build -f Dockerfile.analytics -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

echo "📤 Pushing to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 10 \
    --set-env-vars PORT=8080,OANDA_ENVIRONMENT=practice \
    --set-secrets OANDA_API_KEY=oanda-credentials:api-key \
    --set-secrets PRIMARY_ACCOUNT=oanda-credentials:primary-account \
    --set-secrets GOLD_SCALP_ACCOUNT=oanda-credentials:gold-account \
    --set-secrets STRATEGY_ALPHA_ACCOUNT=oanda-credentials:alpha-account

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "🌐 Your Trading Analytics System is now live!"
echo ""
echo "📊 Main Dashboard:"
echo "   $SERVICE_URL"
echo ""
echo "📈 Analytics Dashboard:"
echo "   $SERVICE_URL/analytics/"
echo ""
echo "🔧 Health Check:"
echo "   $SERVICE_URL/api/analytics/health"
echo ""
echo "📋 Available Analytics Pages:"
echo "   - Overview:           $SERVICE_URL/analytics/"
echo "   - Trade History:      $SERVICE_URL/analytics/trades"
echo "   - Strategy Compare:   $SERVICE_URL/analytics/comparison"
echo "   - Charts:             $SERVICE_URL/analytics/charts"
echo ""
echo "🔐 Credentials are securely stored in Google Secret Manager"
echo ""
echo "📝 To view logs:"
echo "   gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "🔄 To update deployment:"
echo "   ./quick_cloud_deploy.sh"
echo ""
echo "🎉 Your analytics system is ready to track trades!"
echo "=========================================="
