#!/bin/bash
# Google Cloud Trading System - Deployment Script
# Automated deployment to Google Cloud Platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"ai-quant-trading"}
REGION=${GOOGLE_CLOUD_REGION:-"us-central1"}
SERVICE_NAME="trading-system"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "${BLUE}🚀 Google Cloud Trading System Deployment${NC}"
echo "=================================================="
echo -e "Project ID: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "Region: ${YELLOW}${REGION}${NC}"
echo -e "Service: ${YELLOW}${SERVICE_NAME}${NC}"
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️ Not authenticated with gcloud. Please run: gcloud auth login${NC}"
    exit 1
fi

# Set project
echo -e "${BLUE}📋 Setting project...${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${BLUE}🔧 Enabling required APIs...${NC}"
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Check if App Engine is initialized
if [ ! -f "app.yaml" ]; then
    echo -e "${BLUE}📁 Initializing App Engine...${NC}"
    gcloud app create --region=${REGION}
fi

# Copy app.yaml to root for deployment
echo -e "${BLUE}📄 Preparing configuration...${NC}"
cp config/app.yaml .

# Deploy to App Engine
echo -e "${BLUE}🚀 Deploying to App Engine...${NC}"
gcloud app deploy app.yaml --quiet

# Get the deployed URL
echo -e "${BLUE}🌐 Getting deployment URL...${NC}"
DEPLOYED_URL=$(gcloud app browse --no-launch-browser)
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo -e "${GREEN}🌐 Your trading system is available at: ${DEPLOYED_URL}${NC}"

# Clean up
rm -f app.yaml

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Set your OANDA API credentials in Google Cloud Console"
echo "2. Go to App Engine > Settings > Environment Variables"
echo "3. Add OANDA_API_KEY and OANDA_ACCOUNT_ID"
echo "4. Visit your deployed URL to start trading"
echo ""
echo -e "${BLUE}📊 Monitor your deployment:${NC}"
echo "- View logs: gcloud app logs tail -s ${SERVICE_NAME}"
echo "- View console: https://console.cloud.google.com/appengine"
