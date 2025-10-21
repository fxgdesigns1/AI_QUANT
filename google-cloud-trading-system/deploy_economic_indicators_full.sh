#!/bin/bash
# Deploy Economic Indicators Integration - Complete System
# Integrates GDP, CPI, Fed Funds into all strategies and dashboards

set -e

echo "======================================================================"
echo "  ECONOMIC INDICATORS - FULL INTEGRATION & DEPLOYMENT"
echo "======================================================================"
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}📊 Economic Indicators Integration${NC}"
echo ""

# Step 1: Test economic indicators module
echo "1️⃣  Testing Economic Indicators Module..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from dotenv import load_dotenv
load_dotenv('news_api_config.env')

from src.core.economic_indicators import get_economic_indicators

econ = get_economic_indicators()
print(f'  ✅ Service Enabled: {econ.enabled}')

fed_funds = econ.get_federal_funds_rate()
if fed_funds:
    print(f'  ✅ Fed Funds: {fed_funds.value}%')

cpi = econ.get_cpi()
if cpi:
    print(f'  ✅ CPI: {cpi.value}')

real_rate = econ.get_real_interest_rate()
if real_rate:
    print(f'  ✅ Real Rate: {real_rate:.2f}%')

gold_score = econ.get_gold_fundamental_score()
print(f'  ✅ Gold Score: {gold_score[\"score\"]:.2f} ({gold_score[\"recommendation\"]})')
"

echo ""

# Step 2: Test strategy integration
echo "2️⃣  Testing Strategy Integration..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from dotenv import load_dotenv
load_dotenv('oanda_config.env')
load_dotenv('news_api_config.env')

from src.strategies.gold_scalping import GoldScalpingStrategy

strategy = GoldScalpingStrategy()
print(f'  ✅ Gold Strategy: Economic indicators = {strategy.economic_indicators_enabled}')

if strategy.economic_indicators_enabled:
    fund = strategy.economic_service.get_gold_fundamental_score()
    print(f'  ✅ Fundamental Analysis Working: {fund[\"recommendation\"]}')
"

echo ""

# Step 3: Deploy to Google Cloud
echo "3️⃣  Deploying to Google Cloud..."
echo "     This will update main trading system with economic indicators"
echo ""

gcloud app deploy app.yaml --quiet

echo ""
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
echo ""

# Step 4: Verify deployment
echo "4️⃣  Verifying deployment..."
sleep 10

curl -s https://ai-quant-trading.uc.r.appspot.com/health | python3 -m json.tool

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ ECONOMIC INDICATORS DEPLOYED${NC}"
echo "======================================================================"
echo ""
echo "🎯 Next: Run Playwright tests to verify all dashboards"
echo "   cd tests && npx playwright test"
echo ""

