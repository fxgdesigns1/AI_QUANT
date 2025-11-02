#!/bin/bash
# Weekly Trading System Preparation Check
# Comprehensive automated verification script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   WEEKLY TRADING SYSTEM PREPARATION CHECK                  ║${NC}"
echo -e "${BLUE}║   $(date '+%A, %B %d, %Y - %H:%M:%S %Z')                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track results
PASSED=0
FAILED=0
WARNINGS=0

# Function to check result
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

check_warning() {
    echo -e "${YELLOW}⚠️  WARNING${NC}"
    ((WARNINGS++))
}

# ============================================================================
# PHASE 1: CLOUD DEPLOYMENT STATUS
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 1: CLOUD DEPLOYMENT STATUS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -n "1.1 Checking cloud health endpoint... "
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://ai-quant-trading.uc.r.appspot.com/api/health 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    check_result
else
    if [ "$HEALTH_RESPONSE" = "503" ] || [ "$HEALTH_RESPONSE" = "000" ]; then
        check_warning
        echo -e "${YELLOW}   → Cloud instance may be cold-starting (normal on free tier)${NC}"
        echo -e "${YELLOW}   → Wait 30-60 seconds and check again${NC}"
    else
        echo -e "${RED}   → Unexpected status code: $HEALTH_RESPONSE${NC}"
        check_result
    fi
fi

echo -n "1.2 Checking deployment version... "
if command -v gcloud &> /dev/null; then
    VERSION=$(gcloud app versions list --service=default --format="value(id)" --limit=1 2>/dev/null)
    if [ -n "$VERSION" ]; then
        echo -e "${GREEN}✅ Current version: $VERSION${NC}"
        ((PASSED++))
    else
        check_warning
        echo -e "${YELLOW}   → Could not retrieve version (check gcloud auth)${NC}"
    fi
else
    check_warning
    echo -e "${YELLOW}   → gcloud CLI not available (skip cloud checks)${NC}"
fi

# ============================================================================
# PHASE 2: SYSTEM VERIFICATION
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 2: SYSTEM VERIFICATION${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

SYSTEM_DIR="/Users/mac/quant_system_clean/google-cloud-trading-system"

if [ ! -d "$SYSTEM_DIR" ]; then
    echo -e "${RED}❌ System directory not found: $SYSTEM_DIR${NC}"
    ((FAILED++))
    exit 1
fi

cd "$SYSTEM_DIR"

echo -n "2.1 Checking Python dependencies... "
if python3 -c "import oandapyV20, flask, pandas, numpy" 2>/dev/null; then
    check_result
else
    echo -e "${RED}❌ Missing required Python packages${NC}"
    echo -e "${YELLOW}   → Run: pip install -r requirements.txt${NC}"
    ((FAILED++))
fi

echo -n "2.2 Checking configuration files... "
if [ -f "accounts.yaml" ] || [ -f "config/accounts.yaml" ] || [ -f "config/adaptive_config.yaml" ]; then
    check_result
else
    echo -e "${RED}❌ Config files not found in expected locations${NC}"
    echo -e "${YELLOW}   → Checking alternative locations...${NC}"
    find . -name "*.yaml" -o -name "*.yml" 2>/dev/null | head -3
    check_warning
fi

echo -n "2.3 Checking verification script exists... "
if [ -f "verify_all_systems.py" ]; then
    check_result
    echo -n "   → Running system verification... "
    python3 verify_all_systems.py > /tmp/weekly_verification.log 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Systems verified${NC}"
        ((PASSED++))
    else
        check_warning
        echo -e "${YELLOW}   → Some verification checks failed (see /tmp/weekly_verification.log)${NC}"
    fi
else
    check_warning
    echo -e "${YELLOW}   → Verification script not found${NC}"
fi

# ============================================================================
# PHASE 3: MARKET STATUS
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 3: MARKET STATUS CHECK${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

CURRENT_HOUR=$(date -u +%H)
CURRENT_DAY=$(date -u +%w)  # 0=Sunday, 6=Saturday

echo "Current UTC Time: $(date -u '+%H:%M')"
echo "Current Day: $(date -u '+%A')"
echo ""

if [ "$CURRENT_DAY" -eq 0 ] || [ "$CURRENT_DAY" -eq 6 ]; then
    echo -e "${YELLOW}⚠️  Weekend - Markets closed${NC}"
    echo -e "${YELLOW}   → System will resume when markets open (Sunday 22:00 UTC)${NC}"
    ((WARNINGS++))
elif [ "$CURRENT_HOUR" -ge 22 ] || [ "$CURRENT_HOUR" -lt 7 ]; then
    echo -e "${YELLOW}⚠️  Off-peak hours (Asian session)${NC}"
    echo -e "${YELLOW}   → Lower liquidity expected${NC}"
    ((WARNINGS++))
elif [ "$CURRENT_HOUR" -ge 13 ] && [ "$CURRENT_HOUR" -lt 17 ]; then
    echo -e "${GREEN}✅ Prime trading hours (London/NY overlap)${NC}"
    ((PASSED++))
else
    echo -e "${GREEN}✅ Market hours (London session)${NC}"
    ((PASSED++))
fi

# ============================================================================
# PHASE 4: QUICK STATUS CHECK
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 4: QUICK STATUS CHECK${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -n "4.1 Fetching system status... "
STATUS_RESPONSE=$(curl -s --max-time 10 https://ai-quant-trading.uc.r.appspot.com/api/status 2>/dev/null)
if [ -n "$STATUS_RESPONSE" ] && echo "$STATUS_RESPONSE" | grep -q "scanner\|accounts" 2>/dev/null; then
    echo -e "${GREEN}✅ Status API responding${NC}"
    echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null | head -15 || echo "$STATUS_RESPONSE" | head -5
    ((PASSED++))
else
    check_warning
    echo -e "${YELLOW}   → Status API not responding (cloud may be cold)${NC}"
fi

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}SUMMARY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

TOTAL=$((PASSED + FAILED + WARNINGS))

echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL CHECKS PASSED - SYSTEM READY FOR THE WEEK!${NC}"
        exit 0
    else
        echo -e "${YELLOW}✅ SYSTEM OPERATIONAL - Minor warnings (review above)${NC}"
        exit 0
    fi
else
    echo -e "${RED}⚠️  SYSTEM NEEDS ATTENTION - Review failed checks above${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Review failed checks"
    echo "  2. Check logs: gcloud app logs tail --limit=50"
    echo "  3. Verify configurations"
    echo "  4. Re-run this script after fixes"
    exit 1
fi

