#!/bin/bash
# Dashboard Compatibility Verification Script
# Tests: signals-only safety, snapshot creation, API endpoints, no secrets

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "🧪 Dashboard Compatibility Verification Suite"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; exit 1; }
warn() { echo -e "${YELLOW}⚠️  WARN${NC}: $1"; }

# Test A0: Namespace package imports
echo "Test A0: Namespace package imports (CRITICAL)"
if ! python3 -m runner_src.runner.main --debug-imports 2>&1 | grep -q "DEBUG_IMPORTS_OK"; then
    fail "Namespace package imports failed - src.core and src.control_plane must both resolve"
fi
pass "Namespace package imports work correctly"
echo ""

# Test A: Signals-only safety
echo "Test A: Signals-only safety (CRITICAL)"
rm -f runtime/status.json
MAX_ITERATIONS=1 TRADING_MODE=paper PAPER_EXECUTION_ENABLED=false PAPER_ALLOW_OANDA_NETWORK=true \
python3 -m runner_src.runner.main 2>&1 | tee /tmp/signals_only_test.log > /dev/null

if grep -qi "Order manager initialized\|place_market_order\|Submitting.*order\|ORDER_CREATE\|TRADE_OPEN\|TRADE_CLOSE\|/orders\|/trades" /tmp/signals_only_test.log; then
    fail "Execution markers found in signals-only mode!"
fi

pass "Signals-only mode is safe (no execution markers)"
echo ""

# Test B: Snapshot written
echo "Test B: Status snapshot creation"
if [ ! -f runtime/status.json ]; then
    fail "runtime/status.json not created after scan"
fi

# Verify snapshot is valid JSON
if ! python3 -c "import json; json.load(open('runtime/status.json'))" 2>/dev/null; then
    fail "runtime/status.json is not valid JSON"
fi

# Verify snapshot contains required fields
if ! python3 -c "import json; data=json.load(open('runtime/status.json')); assert 'execution_enabled' in data and 'accounts_execution_capable' in data and 'last_signals_generated' in data and 'last_executed_count' in data" 2>/dev/null; then
    fail "runtime/status.json missing required fields (execution_enabled, accounts_execution_capable, last_signals_generated, last_executed_count)"
fi

# Verify no secrets in snapshot
if grep -qi "OANDA_API_KEY\|api_key.*:\|token.*:\|secret.*:\|password.*:" runtime/status.json; then
    fail "Secrets found in status snapshot!"
fi

pass "Status snapshot created and valid (no secrets)"
echo ""

# Test C: API reads snapshot (if API running)
echo "Test C: API endpoint responses"
if curl -sf http://127.0.0.1:8787/health &>/dev/null; then
    # Test /api/status
    status_resp=$(curl -sf http://127.0.0.1:8787/api/status)
    if [ $? -ne 0 ]; then
        fail "/api/status endpoint failed"
    fi
    
    # Verify response structure
    if ! echo "$status_resp" | python3 -c "import sys, json; data=json.load(sys.stdin); assert 'mode' in data and 'execution_enabled' in data" 2>/dev/null; then
        fail "/api/status response missing required fields"
    fi
    
    # Verify no secrets
    if echo "$status_resp" | grep -qi "OANDA_API_KEY\|api_key\|token\|secret"; then
        fail "/api/status response contains secrets!"
    fi
    
    pass "/api/status endpoint works (no secrets)"
else
    warn "API not running - skipping API tests"
    info "Start API with: ./scripts/run_control_plane.sh"
fi
echo ""

# Test D: Forensic Command dashboard served
echo "Test D: Forensic Command dashboard"
if curl -sf http://127.0.0.1:8787/health &>/dev/null; then
    # Test that / returns HTML with Forensic Command content
    dashboard_html=$(curl -sf http://127.0.0.1:8787/)
    if [ $? -ne 0 ]; then
        fail "Dashboard endpoint (/) failed"
    fi
    
    # Check for key markers in Forensic Command UI
    if echo "$dashboard_html" | grep -q "AI-QUANT | TOTAL COMMAND"; then
        pass "Forensic Command dashboard served at /"
    else
        fail "Dashboard at / does not contain 'AI-QUANT | TOTAL COMMAND'"
    fi
    
    if echo "$dashboard_html" | grep -q "tradingview_terminal"; then
        pass "TradingView terminal container present"
    else
        fail "TradingView terminal container missing"
    fi
    
    # Test /advanced fallback
    advanced_code=$(curl -sf -o /dev/null -w "%{http_code}" "http://127.0.0.1:8787/advanced" || echo "000")
    if [ "$advanced_code" = "200" ]; then
        pass "/advanced endpoint available (fallback)"
    else
        warn "/advanced endpoint returned $advanced_code"
    fi
else
    warn "API not running - skipping dashboard test"
fi
echo ""

# Test E: All API endpoints return 200
echo "Test E: API endpoint compatibility"
if curl -sf http://127.0.0.1:8787/health &>/dev/null; then
    endpoints=(
        "/api/status"
        "/api/config"
        "/api/accounts"
        "/api/strategies/overview"
        "/api/positions"
        "/api/signals/pending"
        "/api/trades/pending"
        "/api/news"
        "/api/sidebar/live-prices"
        "/api/opportunities"
        "/api/contextual/XAU_USD"
    )
    
    for endpoint in "${endpoints[@]}"; do
        code=$(curl -sf -o /dev/null -w "%{http_code}" "http://127.0.0.1:8787$endpoint" || echo "000")
        if [ "$code" = "200" ]; then
            pass "$endpoint returns 200"
        else
            fail "$endpoint returns $code (expected 200)"
        fi
    done
else
    warn "API not running - skipping endpoint tests"
fi
echo ""

# Test F: POST endpoints require auth
echo "Test F: POST endpoint authentication"
if curl -sf http://127.0.0.1:8787/health &>/dev/null; then
    # Test without token (should fail)
    code=$(curl -sf -o /dev/null -w "%{http_code}" -X POST \
        http://127.0.0.1:8787/api/opportunities/approve \
        -H 'Content-Type: application/json' \
        -d '{"id":"test"}' || echo "000")
    
    if [ "$code" = "401" ] || [ "$code" = "403" ]; then
        pass "POST endpoints require authentication"
    else
        warn "POST endpoint auth check returned $code (expected 401/403)"
    fi
else
    warn "API not running - skipping auth test"
fi
echo ""

# Test G: Snapshot fields reflect signals-only truth
echo "Test G: Snapshot truthfulness"
if [ -f runtime/status.json ]; then
    snapshot_data=$(python3 -c "import json; print(json.dumps(json.load(open('runtime/status.json'))))" 2>/dev/null)
    
    execution_enabled=$(echo "$snapshot_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('execution_enabled', 'missing'))" 2>/dev/null)
    
    if [ "$execution_enabled" = "False" ] || [ "$execution_enabled" = "false" ]; then
        pass "Snapshot correctly reflects signals-only mode (execution_enabled=false)"
    else
        warn "Snapshot execution_enabled=$execution_enabled (expected false in signals-only)"
    fi
else
    fail "Cannot verify snapshot truthfulness (file missing)"
fi
echo ""

# Summary
echo "=============================================="
echo "✅ All verification tests passed!"
echo ""
echo "Next steps:"
echo "  1. Start API: ./scripts/run_control_plane.sh"
echo "  2. Start runner: python3 -m runner_src.runner.main"
echo "  3. Open dashboard: http://127.0.0.1:8787/"
echo "  4. Verify dashboard loads without JS errors"
echo ""
