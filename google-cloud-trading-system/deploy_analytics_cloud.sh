#!/bin/bash
# Deploy Analytics Dashboard to Google Cloud
# Separate service from main trading system

set -e

echo "======================================================================"
echo "  DEPLOYING ANALYTICS DASHBOARD TO GOOGLE CLOUD"
echo "======================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${BLUE}📊 Analytics Dashboard Deployment${NC}"
echo ""

# Check project is set
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No Google Cloud project set"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✅ Project: $PROJECT_ID${NC}"
echo ""

# Navigate to analytics directory
cd "$(dirname "$0")/analytics"

echo "📦 Preparing deployment..."
echo ""

# Create .gcloudignore if it doesn't exist
if [ ! -f .gcloudignore ]; then
    cat > .gcloudignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# Testing
.pytest_cache/
test_analytics.db
tests/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Database (local only)
test_analytics.db
analytics.db

# Node
node_modules/
package-lock.json

# Playwright
playwright-report/
test-results/

# Documentation
*.md
EOF
    echo "✅ Created .gcloudignore"
fi

# Verify app_analytics.yaml exists
if [ ! -f app_analytics.yaml ]; then
    echo "❌ app_analytics.yaml not found"
    exit 1
fi

# Verify requirements.txt exists
if [ ! -f requirements.txt ]; then
    echo "❌ requirements.txt not found"
    exit 1
fi

echo "🔍 Pre-deployment checks..."
echo ""

# Check if app.py exists
if [ ! -f app.py ]; then
    echo "❌ app.py not found"
    exit 1
fi

# Check if database directory exists
if [ ! -d database ]; then
    echo "❌ database directory not found"
    exit 1
fi

# Check if collectors directory exists
if [ ! -d collectors ]; then
    echo "❌ collectors directory not found"
    exit 1
fi

# Check if templates directory exists
if [ ! -d templates ]; then
    echo "❌ templates directory not found"
    exit 1
fi

echo -e "${GREEN}✅ All files present${NC}"
echo ""

# Show what will be deployed
echo -e "${YELLOW}📋 Deployment Summary:${NC}"
echo "  • Service: analytics"
echo "  • Runtime: python39"
echo "  • Instance: F2 (1 vCPU, 1GB RAM)"
echo "  • Scaling: 1-3 instances"
echo "  • Mode: Read-Only Analytics"
echo ""

# Confirm deployment
read -p "Deploy analytics dashboard to Google Cloud? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo ""
echo "🚀 Deploying to Google Cloud..."
echo ""

# Deploy to App Engine
gcloud app deploy app_analytics.yaml --quiet

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ ANALYTICS DASHBOARD DEPLOYED SUCCESSFULLY${NC}"
echo "======================================================================"
echo ""

# Get the service URL
SERVICE_URL="https://analytics-dot-${PROJECT_ID}.uc.r.appspot.com"

echo "🌐 Analytics Dashboard URLs:"
echo "  • Dashboard: ${SERVICE_URL}/overview"
echo "  • Health Check: ${SERVICE_URL}/health"
echo "  • API Status: ${SERVICE_URL}/api/stats"
echo ""

echo "📊 Quick Access Commands:"
echo "  # View logs"
echo "  gcloud app logs tail -s analytics"
echo ""
echo "  # Check status"
echo "  gcloud app services list"
echo ""
echo "  # Open dashboard"
echo "  open ${SERVICE_URL}/overview"
echo ""

echo "✅ Deployment complete!"
echo ""
echo "⚠️  Note: The analytics service runs independently from your trading system."
echo "    It only reads data and cannot execute trades."
echo ""


