#!/bin/bash
# Verify Analytics Dashboard is Ready for Cloud Deployment

set -e

echo "======================================================================"
echo "  ANALYTICS DASHBOARD - DEPLOYMENT VERIFICATION"
echo "======================================================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Check 1: Directory exists
echo -n "1. Checking analytics directory... "
if [ -d "analytics" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Core files
echo -n "2. Checking app.py... "
if [ -f "analytics/app.py" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo -n "3. Checking app_analytics.yaml... "
if [ -f "analytics/app_analytics.yaml" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo -n "4. Checking requirements.txt... "
if [ -f "analytics/requirements.txt" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Database schema
echo -n "5. Checking database schema... "
if [ -f "analytics/database/schema.sql" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Collectors
echo -n "6. Checking OANDA collector... "
if [ -f "analytics/collectors/oanda_collector.py" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Analytics engine
echo -n "7. Checking performance analytics... "
if [ -f "analytics/analytics/performance.py" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Templates
echo -n "8. Checking templates... "
if [ -f "analytics/templates/overview.html" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: gcloud installed
echo -n "9. Checking gcloud CLI... "
if command -v gcloud &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Not installed${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 8: Project configured
echo -n "10. Checking Google Cloud project... "
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -n "$PROJECT_ID" ]; then
    echo -e "${GREEN}✅ ($PROJECT_ID)${NC}"
else
    echo -e "${RED}❌ Not configured${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "======================================================================"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED - READY TO DEPLOY${NC}"
    echo ""
    echo "🚀 To deploy, run:"
    echo "   ./deploy_analytics_cloud.sh"
    echo ""
    echo "📊 After deployment, access at:"
    echo "   https://analytics-dot-${PROJECT_ID}.uc.r.appspot.com/overview"
    echo ""
else
    echo -e "${RED}❌ $ERRORS CHECK(S) FAILED${NC}"
    echo ""
    echo "Please fix the issues above before deploying."
    exit 1
fi

echo "======================================================================"


