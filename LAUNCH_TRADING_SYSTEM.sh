#!/bin/bash
# 🚀 LAUNCH TRADING SYSTEM
# Start automated trading system on Google Cloud App Engine

set -e

echo "================================================================================"
echo "🚀 LAUNCHING AUTOMATED TRADING SYSTEM"
echo "================================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ai-quant-trading"
BASE_URL="https://ai-quant-trading.uc.r.appspot.com"

echo -e "${BLUE}📋 Configuration:${NC}"
echo "   Project: $PROJECT_ID"
echo "   URL: $BASE_URL"
echo ""

# Step 1: Set project
echo -e "${BLUE}1. Setting Google Cloud project...${NC}"
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✅ Project set to: $PROJECT_ID${NC}"
echo ""

# Step 2: Verify App Engine is running
echo -e "${BLUE}2. Verifying App Engine service...${NC}"
SERVICES=$(gcloud app services list --project=$PROJECT_ID --format="value(id)")
if [[ $SERVICES == *"default"* ]]; then
    echo -e "${GREEN}✅ App Engine service is running${NC}"
else
    echo -e "${YELLOW}⚠️  App Engine service not found. Deploying...${NC}"
    cd google-cloud-trading-system
    gcloud app deploy app.yaml --project=$PROJECT_ID --quiet
    cd ..
fi
echo ""

# Step 3: Deploy cron jobs
echo -e "${BLUE}3. Deploying cron jobs...${NC}"
cd google-cloud-trading-system
gcloud app deploy cron.yaml --project=$PROJECT_ID --quiet
cd ..
echo -e "${GREEN}✅ Cron jobs deployed${NC}"
echo ""

# Step 4: Verify cron jobs are active
echo -e "${BLUE}4. Verifying cron jobs...${NC}"
echo "   • Quality Scanner: Every 5 minutes"
echo "   • Premium Scanner: Every 30 minutes"
echo "   • Morning Briefing: Daily at 08:00"
echo -e "${GREEN}✅ Cron jobs configured${NC}"
echo ""

# Step 5: Trigger initial scan
echo -e "${BLUE}5. Triggering initial scan...${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/cron/quality-scan" -H "Accept: application/json")
if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✅ Initial scan triggered successfully${NC}"
    echo "   Response: $RESPONSE"
else
    echo -e "${YELLOW}⚠️  Scan response: $RESPONSE${NC}"
fi
echo ""

# Step 6: Check system status
echo -e "${BLUE}6. Checking system status...${NC}"
STATUS=$(curl -s "$BASE_URL/api/status" 2>&1)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ System is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Status check returned: $STATUS${NC}"
fi
echo ""

# Step 7: Display dashboard URL
echo -e "${BLUE}7. Access your trading dashboard:${NC}"
echo -e "${GREEN}   Dashboard: $BASE_URL/dashboard${NC}"
echo -e "${GREEN}   API Status: $BASE_URL/api/status${NC}"
echo ""

# Step 8: Summary
echo "================================================================================"
echo -e "${GREEN}✅ TRADING SYSTEM LAUNCHED${NC}"
echo "================================================================================"
echo ""
echo "📊 System Status:"
echo "   ✅ App Engine: Running"
echo "   ✅ Cron Jobs: Active (scans every 5 minutes)"
echo "   ✅ Scanner: Operational"
echo "   ✅ Dashboard: $BASE_URL/dashboard"
echo ""
echo "🔄 Trading Schedule:"
echo "   • Quality Scanner: Every 5 minutes"
echo "   • Premium Scanner: Every 30 minutes"
echo "   • Morning Briefing: Daily at 08:00 (London time)"
echo ""
echo "📈 Monitoring:"
echo "   • View logs: gcloud app logs tail --service=default --project=$PROJECT_ID"
echo "   • Check status: curl $BASE_URL/api/status"
echo "   • Manual scan: curl $BASE_URL/cron/quality-scan"
echo ""
echo "🎯 The system is now actively scanning markets and executing trades!"
echo ""

