#!/bin/bash
# Check Google Cloud Trading System Status

echo "=========================================="
echo "GOOGLE CLOUD TRADING SYSTEM STATUS CHECK"
echo "=========================================="
echo ""

# Project ID
PROJECT_ID="ai-quant-trading"

echo "📊 Project: $PROJECT_ID"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "⚠️  gcloud CLI not installed"
    echo ""
    echo "To check cloud system, you need to:"
    echo "1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install"
    echo "2. Run: gcloud auth login"
    echo "3. Run: gcloud config set project $PROJECT_ID"
    echo ""
    echo "Then use these commands:"
    echo ""
    echo "# Check App Engine status:"
    echo "gcloud app describe --project=$PROJECT_ID"
    echo ""
    echo "# View App Engine logs:"
    echo "gcloud app logs read --service=default --limit=50 --project=$PROJECT_ID"
    echo ""
    echo "# Check App Engine versions:"
    echo "gcloud app versions list --service=default --project=$PROJECT_ID"
    echo ""
    echo "# Check Cloud Run service:"
    echo "gcloud run services describe auto-trading-gbp --region=us-central1 --project=$PROJECT_ID"
    echo ""
    echo "# View Cloud Run logs:"
    echo "gcloud run services logs read auto-trading-gbp --region=us-central1 --limit=50 --project=$PROJECT_ID"
    echo ""
else
    echo "✅ gcloud CLI found"
    echo ""
    
    # Set project
    gcloud config set project $PROJECT_ID 2>/dev/null
    
    echo "📊 APP ENGINE STATUS:"
    echo "-------------------"
    gcloud app describe --project=$PROJECT_ID 2>/dev/null || echo "❌ Could not get App Engine status"
    echo ""
    
    echo "📋 APP ENGINE VERSIONS:"
    echo "----------------------"
    gcloud app versions list --service=default --limit=5 --project=$PROJECT_ID 2>/dev/null || echo "❌ Could not list versions"
    echo ""
    
    echo "📝 RECENT APP ENGINE LOGS:"
    echo "-------------------------"
    gcloud app logs read --service=default --limit=20 --project=$PROJECT_ID 2>/dev/null | tail -20 || echo "❌ Could not read logs"
    echo ""
    
    echo "☁️  CLOUD RUN STATUS:"
    echo "-------------------"
    gcloud run services describe auto-trading-gbp --region=us-central1 --project=$PROJECT_ID 2>/dev/null || echo "❌ Could not get Cloud Run status"
    echo ""
    
    echo "📝 RECENT CLOUD RUN LOGS:"
    echo "------------------------"
    gcloud run services logs read auto-trading-gbp --region=us-central1 --limit=20 --project=$PROJECT_ID 2>/dev/null | tail -20 || echo "❌ Could not read logs"
    echo ""
fi

echo "=========================================="
echo "WEB INTERFACES:"
echo "=========================================="
echo "App Engine Dashboard: https://ai-quant-trading.uc.r.appspot.com"
echo "Cloud Run Status: https://auto-trading-gbp-779507790009.us-central1.run.app/status"
echo ""
