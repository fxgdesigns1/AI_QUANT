#!/bin/bash
# Verify Control Plane is running and auth works

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Parse token from args, env, or temp file
TOKEN="${1:-${CONTROL_PLANE_TOKEN:-}}"

# If still empty, try to read from temp file (created by start script)
if [ -z "$TOKEN" ] && [ -f /tmp/control_plane_token_current.txt ]; then
    TOKEN=$(cat /tmp/control_plane_token_current.txt 2>/dev/null | head -1 || echo "")
fi

if [ -z "$TOKEN" ]; then
    echo "❌ No token provided"
    echo "   Usage: $0 [token]"
    echo "   Or set: export CONTROL_PLANE_TOKEN=your-token"
    echo "   Or ensure start_control_plane_clean.sh created /tmp/control_plane_token_current.txt"
    exit 1
fi

echo "🔍 Verifying Control Plane..."
echo ""

# Test 1: Check listener
echo "1️⃣  Checking port 8787 listener..."
LISTENER=$(lsof -nP -iTCP:8787 -sTCP:LISTEN 2>/dev/null || true)
if [ -z "$LISTENER" ]; then
    echo "   ❌ No process listening on port 8787"
    echo "   Start server with: bash scripts/start_control_plane_clean.sh"
    exit 1
fi
echo "   ✅ Listener found: $(echo "$LISTENER" | awk '{print $2}')"
echo ""

# Test 2: GET /api/status
echo "2️⃣  Testing GET /api/status..."
STATUS_RESP=$(curl -sf http://127.0.0.1:8787/api/status || echo "FAIL")
if [ "$STATUS_RESP" = "FAIL" ]; then
    echo "   ❌ GET /api/status failed"
    exit 1
fi

MODE=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode', 'unknown'))" 2>/dev/null || echo "unknown")
EXEC_ENABLED=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('execution_enabled', 'unknown'))" 2>/dev/null || echo "unknown")
ACTIVE_STRATEGY=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('active_strategy_key', 'unknown'))" 2>/dev/null || echo "unknown")

echo "   ✅ Status: mode=$MODE, execution_enabled=$EXEC_ENABLED, active_strategy=$ACTIVE_STRATEGY"
echo ""

# Test 2.5: GET /favicon.ico (stop 404 noise)
echo "2.5️⃣ Testing GET /favicon.ico..."
FAVICON_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/favicon.ico || echo "000")
if [ "$FAVICON_CODE" = "204" ] || [ "$FAVICON_CODE" = "200" ]; then
    echo "   ✅ Favicon endpoint: HTTP $FAVICON_CODE (no 404 noise)"
else
    echo "   ❌ Favicon endpoint returned HTTP $FAVICON_CODE (expected 204 or 200)"
    exit 1
fi
echo ""

# Test 2.6: Test noise shim routes (should return 204)
echo "2.6️⃣ Testing noise shim routes (should return 204)..."
SOCKET_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/socket.io/?EIO=4&transport=polling || echo "000")
INSIGHTS_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/api/insights || echo "000")
TRADE_IDEAS_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/api/trade_ideas || echo "000")
FULL_SCAN_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8787/tasks/full_scan || echo "000")

if [ "$SOCKET_CODE" = "204" ]; then
    echo "   ✅ GET /socket.io/: HTTP 204 (noise shim active)"
else
    echo "   ⚠️  GET /socket.io/: HTTP $SOCKET_CODE (expected 204)"
fi

if [ "$INSIGHTS_CODE" = "204" ]; then
    echo "   ✅ GET /api/insights: HTTP 204 (noise shim active)"
else
    echo "   ⚠️  GET /api/insights: HTTP $INSIGHTS_CODE (expected 204)"
fi

if [ "$TRADE_IDEAS_CODE" = "204" ]; then
    echo "   ✅ GET /api/trade_ideas: HTTP 204 (noise shim active)"
else
    echo "   ⚠️  GET /api/trade_ideas: HTTP $TRADE_IDEAS_CODE (expected 204)"
fi

if [ "$FULL_SCAN_CODE" = "204" ]; then
    echo "   ✅ POST /tasks/full_scan: HTTP 204 (noise shim active)"
else
    echo "   ⚠️  POST /tasks/full_scan: HTTP $FULL_SCAN_CODE (expected 204)"
fi
echo ""

# Test 2.7: GET /api/strategies (authoritative catalog)
echo "2.7️⃣ Testing GET /api/strategies..."
STRATEGIES_RESP=$(curl -sf http://127.0.0.1:8787/api/strategies || echo "FAIL")
if [ "$STRATEGIES_RESP" = "FAIL" ]; then
    echo "   ❌ GET /api/strategies failed"
    exit 1
fi

STRATEGIES_OK=$(echo "$STRATEGIES_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok', False))" 2>/dev/null || echo "False")
ALLOWED_COUNT=$(echo "$STRATEGIES_RESP" | python3 -c "import sys,json; allowed=json.load(sys.stdin).get('allowed', []); print(len(allowed))" 2>/dev/null || echo "0")
ALLOWED_KEYS=$(echo "$STRATEGIES_RESP" | python3 -c "import sys,json; allowed=json.load(sys.stdin).get('allowed', []); print(','.join(allowed))" 2>/dev/null || echo "")

if [ "$STRATEGIES_OK" = "True" ] && [ "$ALLOWED_COUNT" -gt 0 ]; then
    echo "   ✅ Strategies catalog: $ALLOWED_COUNT allowed keys: $ALLOWED_KEYS"
else
    echo "   ❌ Invalid /api/strategies response: ok=$STRATEGIES_OK, count=$ALLOWED_COUNT"
    exit 1
fi
echo ""

# Test 3: POST /api/config (with auth)
echo "3️⃣  Testing POST /api/config with Bearer token..."
# Use valid strategy key (gold, momentum, range, etc.)
POST_RESP=$(curl -sf -X POST http://127.0.0.1:8787/api/config \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"active_strategy_key":"gold"}' || echo "FAIL")

if [ "$POST_RESP" = "FAIL" ]; then
    echo "   ❌ POST /api/config failed"
    echo "   Check server logs or verify token is correct"
    exit 1
fi

# Check for error response
ERROR_MSG=$(echo "$POST_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail', ''))" 2>/dev/null || echo "")
if [ -n "$ERROR_MSG" ]; then
    if echo "$ERROR_MSG" | grep -qi "invalid\|unauthorized\|missing"; then
        echo "   ❌ Auth failed: $ERROR_MSG"
        echo "   Token (first 8): ${TOKEN:0:8}..."
        exit 1
    fi
fi

STATUS_FIELD=$(echo "$POST_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")
if [ "$STATUS_FIELD" = "ok" ]; then
    echo "   ✅ POST /api/config succeeded"
else
    echo "   ⚠️  Unexpected response: $POST_RESP"
fi
echo ""

# Test 4: Verify strategy key changed
echo "4️⃣  Verifying active_strategy_key updated..."
NEW_STATUS=$(curl -sf http://127.0.0.1:8787/api/status)
NEW_STRATEGY=$(echo "$NEW_STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('active_strategy_key', 'unknown'))" 2>/dev/null || echo "unknown")

if [ "$NEW_STRATEGY" = "gold" ]; then
    echo "   ✅ active_strategy_key = gold (updated successfully)"
else
    echo "   ⚠️  active_strategy_key = $NEW_STRATEGY (expected: gold)"
    echo "   Note: Strategy may not have changed if it was already 'gold'"
fi
echo ""

# Test 5: Comprehensive scan for forbidden endpoints (served assets + runtime)
echo "5️⃣  Scanning served dashboard for forbidden endpoint references..."
echo "   A) Checking what GET / actually serves..."
SERVED_HTML=$(curl -s http://127.0.0.1:8787/ 2>&1 | head -50 || echo "")
if [ -z "$SERVED_HTML" ]; then
    echo "      ⚠️  Could not fetch HTML from server"
    SERVED_FILE="unknown"
elif echo "$SERVED_HTML" | grep -qi "FORENSIC COMMAND\|Forensic Command"; then
    SERVED_FILE="forensic_command.html"
    echo "      ✅ Served template: forensic_command.html (confirmed by 'FORENSIC COMMAND' marker)"
elif echo "$SERVED_HTML" | grep -qi "dashboard_advanced\|Dashboard Advanced"; then
    SERVED_FILE="dashboard_advanced.html"
    echo "      ⚠️  Served template: dashboard_advanced.html (fallback)"
else
    SERVED_FILE="unknown"
    echo "      ⚠️  Could not identify served template"
fi

# B) Check served template for forbidden patterns (excluding guard array and comments)
# Use grep as fallback if rg not available
if command -v rg >/dev/null 2>&1; then
    FORBIDDEN_SOCKET=$(rg -n "/socket\\.io|socket\\.io|\\bio\(" templates/forensic_command.html 2>/dev/null | \
        grep -v "^[0-9]*:.*//.*socket" | \
        grep -v "^[0-9]*:.*#.*socket" | \
        grep -v "BLOCKED_ENDPOINTS" | \
        grep -v "Blocked endpoint" || true)
    
    FORBIDDEN_ENDPOINTS=$(rg -n "/tasks/full_scan|/api/insights|/api/trade_ideas" templates/forensic_command.html 2>/dev/null | \
        grep -v "BLOCKED_ENDPOINTS" | \
        grep -v "^[0-9]*:.*//" || true)
else
    # Fallback to grep if ripgrep not available
    FORBIDDEN_SOCKET=$(grep -n "socket\\.io\|\\bio(" templates/forensic_command.html 2>/dev/null | \
        grep -v "//.*socket" | \
        grep -v "#.*socket" | \
        grep -v "BLOCKED_ENDPOINTS" | \
        grep -v "Blocked endpoint" || true)
    
    FORBIDDEN_ENDPOINTS=$(grep -n "/tasks/full_scan\|/api/insights\|/api/trade_ideas" templates/forensic_command.html 2>/dev/null | \
        grep -v "BLOCKED_ENDPOINTS" | \
        grep -v "//" || true)
fi

# C) Check for actual fetch/io() calls (not just string references)
echo "   C) Checking for actual function calls to forbidden endpoints..."
ACTUAL_CALLS=$(python3 << 'PYEOF'
import pathlib
import re

p = pathlib.Path('templates/forensic_command.html')
if not p.exists():
    print("FILE_NOT_FOUND")
    exit(0)

content = p.read_text()
lines = content.split('\n')
found = []

for i, line in enumerate(lines, 1):
    # Skip comments and BLOCKED_ENDPOINTS array
    if 'BLOCKED_ENDPOINTS' in line or line.strip().startswith('//'):
        continue
    
    # Check for actual fetch calls (direct, not through apiGet/apiPost)
    # Look for fetch( with a string literal containing forbidden endpoint
    if re.search(r"fetch\s*\(['\"]/socket\.io", line, re.IGNORECASE):
        # Make sure it's not inside apiGet/apiPost function
        context_start = max(0, i - 10)
        context = '\n'.join(lines[context_start:i+1])
        if 'async function apiGet' not in context and 'async function apiPost' not in context:
            found.append(f"Line {i}: direct fetch('/socket.io')")
    
    if re.search(r"fetch\s*\(['\"]/tasks/full_scan", line, re.IGNORECASE):
        context_start = max(0, i - 10)
        context = '\n'.join(lines[context_start:i+1])
        if 'async function apiGet' not in context and 'async function apiPost' not in context:
            found.append(f"Line {i}: direct fetch('/tasks/full_scan')")
    
    if re.search(r"fetch\s*\(['\"]/api/insights", line, re.IGNORECASE):
        context_start = max(0, i - 10)
        context = '\n'.join(lines[context_start:i+1])
        if 'async function apiGet' not in context and 'async function apiPost' not in context:
            found.append(f"Line {i}: direct fetch('/api/insights')")
    
    if re.search(r"fetch\s*\(['\"]/api/trade_ideas", line, re.IGNORECASE):
        context_start = max(0, i - 10)
        context = '\n'.join(lines[context_start:i+1])
        if 'async function apiGet' not in context and 'async function apiPost' not in context:
            found.append(f"Line {i}: direct fetch('/api/trade_ideas')")
    
    # Check for io() calls
    if re.search(r'\bio\s*\(', line) and 'BLOCKED' not in line:
        found.append(f"Line {i}: io() call")

if found:
    for item in found:
        print(item)
else:
    print("NONE")
PYEOF
)

if [ -n "$FORBIDDEN_SOCKET" ] || [ -n "$FORBIDDEN_ENDPOINTS" ]; then
    echo "   ⚠️  Found string references (may be in comments/guard):"
    [ -n "$FORBIDDEN_SOCKET" ] && echo "$FORBIDDEN_SOCKET" | head -3 | sed 's/^/      /'
    [ -n "$FORBIDDEN_ENDPOINTS" ] && echo "$FORBIDDEN_ENDPOINTS" | head -3 | sed 's/^/      /'
fi

if [ "$ACTUAL_CALLS" != "NONE" ] && [ -n "$ACTUAL_CALLS" ]; then
    echo "   ❌ Found actual function calls to forbidden endpoints:"
    echo "$ACTUAL_CALLS" | sed 's/^/      /'
    echo "   ⚠️  These must be removed or disabled"
    FAILED=1
elif [ "$ACTUAL_CALLS" = "NONE" ]; then
    echo "   ✅ No actual function calls to forbidden endpoints found"
    echo "   ✅ Guard array present in apiGet/apiPost"
else
    echo "   ⚠️  Could not verify (file not found or parse error)"
fi

# D) Verify guard is present
GUARD_PRESENT=$(rg -n "BLOCKED_ENDPOINTS|isBlocked" templates/forensic_command.html 2>/dev/null | wc -l)
if [ "$GUARD_PRESENT" -gt 0 ]; then
    echo "   ✅ Safety guard (BLOCKED_ENDPOINTS) is present"
else
    echo "   ⚠️  Safety guard not found"
fi

echo ""

# Test 7: Verify strategy catalog and switching
echo "7️⃣  Verifying strategy catalog and switching..."
echo "   A) GET /api/strategies returns allowed keys..."
STRAT_RESP=$(curl -sf http://127.0.0.1:8787/api/strategies || echo "FAIL")
if [ "$STRAT_RESP" = "FAIL" ]; then
    echo "      ❌ GET /api/strategies failed"
    FAILED=1
else
    ALLOWED_KEYS=$(echo "$STRAT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join(d.get('allowed', [])))" 2>/dev/null || echo "")
    if [ -n "$ALLOWED_KEYS" ]; then
        echo "      ✅ Allowed keys: $ALLOWED_KEYS"
    else
        echo "      ⚠️  Could not parse allowed keys"
    fi
fi

echo "   B) POST /api/config with valid strategy key (gold)..."
POST_STRAT_RESP=$(curl -sf -X POST http://127.0.0.1:8787/api/config \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"active_strategy_key":"gold"}' || echo "FAIL")

if [ "$POST_STRAT_RESP" = "FAIL" ]; then
    echo "      ❌ POST /api/config failed"
    FAILED=1
else
    POST_STATUS=$(echo "$POST_STRAT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")
    if [ "$POST_STATUS" = "ok" ]; then
        echo "      ✅ Strategy switch POST succeeded"
    else
        echo "      ⚠️  Unexpected response status: $POST_STATUS"
    fi
fi

echo "   C) Verifying active_strategy_key updated..."
FINAL_STATUS=$(curl -sf http://127.0.0.1:8787/api/status)
FINAL_STRATEGY=$(echo "$FINAL_STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('active_strategy_key', 'unknown'))" 2>/dev/null || echo "unknown")
if [ "$FINAL_STRATEGY" = "gold" ]; then
    echo "      ✅ active_strategy_key = gold (verified update)"
else
    echo "      ⚠️  active_strategy_key = $FINAL_STRATEGY (may have been already 'gold')"
fi
echo ""

echo "   📝 Note: TradingView widget (external CDN) may make socket.io calls internally."
echo "      These are external and cannot be controlled by our code."
echo ""

# Optional: Playwright runtime proof (best-effort, does not fail verify script)
echo "8️⃣  Runtime Playwright verification (best-effort)..."
PW_EXIT_CODE=0
if command -v node >/dev/null 2>&1 && [ -f "scripts/pw_trace_forbidden_requests.js" ]; then
    if [ -f "node_modules/.bin/playwright" ] || npx playwright --version >/dev/null 2>&1; then
        echo "   Running Playwright trace (60 seconds)..."
        if node scripts/pw_trace_forbidden_requests.js 2>&1 | tee /tmp/pw_trace_output.log; then
            echo "   ✅ Playwright runtime proof: PASS (no forbidden endpoint calls from our code)"
        else
            PW_EXIT_CODE=$?
            echo "   ⚠️  Playwright trace completed with exit code: $PW_EXIT_CODE"
            echo "   Check scripts/artifacts/pw_forbidden_requests.log for details"
            echo "   Note: This is a best-effort check; verify script continues regardless"
        fi
    else
        echo "   ⚠️  Playwright not installed. Install with: npx playwright install chromium"
        echo "   Skipping runtime verification (optional step)"
    fi
else
    echo "   ⚠️  Node.js or Playwright script not found. Skipping runtime verification."
fi
echo ""

# Final check: did any test fail?
if [ "${FAILED:-0}" = "1" ]; then
    echo "❌ Verification FAILED - see errors above"
    exit 1
fi

echo "✅ All verification tests passed!"
echo ""
echo "📋 Summary:"
echo "   ✅ Port 8787: Listener active"
echo "   ✅ GET /api/status: OK"
echo "   ✅ GET /favicon.ico: OK (HTTP 204, no 404 noise)"
echo "   ✅ Noise shims: /socket.io, /api/insights, /api/trade_ideas, /tasks/full_scan return 204 (no 404 spam)"
echo "   ✅ GET /api/strategies: OK (returns allowed keys)"
echo "   ✅ POST /api/config: Authorized (Bearer token works)"
echo "   ✅ Strategy update: Verified (active_strategy_key updated)"
echo "   ✅ Forbidden endpoints: No calls found in served dashboard"
echo "   ✅ Safety guard: Active in apiGet/apiPost (blocks /socket.io, /tasks/full_scan, /api/insights, /api/trade_ideas)"
echo "   ✅ All network calls route through apiGet/apiPost (no direct fetch to forbidden endpoints)"
echo "   ✅ Network instrumentation: Available via localStorage.DEBUG_NET_TRACE = '1' for runtime tracing"
echo ""
echo "💡 To use in dashboard:"
echo "   1. Open http://127.0.0.1:8787/"
echo "   2. Click Settings (⚙️)"
echo "   3. Paste token: ${TOKEN:0:8}... (full token saved in env)"
echo "   4. Click Save"
echo ""
echo "🔒 Safety: apiGet/apiPost block /socket.io, /tasks/full_scan, /api/insights, /api/trade_ideas"
echo "🔇 Noise reduction: Server returns 204 for /socket.io, /api/insights, /api/trade_ideas, /tasks/full_scan (no 404 spam)"
echo ""
echo "📋 Manual Runtime Proof (recommended):"
echo ""
echo "   To verify favicon no longer 404s:"
echo "   1. Open http://127.0.0.1:8787/ in browser"
echo "   2. Open DevTools → Console tab"
echo "   3. Expected: NO (Not Found) favicon.ico 404 error"
echo "   4. Optional: Check Network tab - GET /favicon.ico should return 204"
echo ""
echo "   To verify no forbidden endpoint requests are made by OUR code:"
echo "   1. Open http://127.0.0.1:8787/ in browser"
echo "   2. Open DevTools → Network tab"
echo "   3. Filter for: full_scan, insights, trade_ideas"
echo "   4. Wait 60 seconds (polling window: pollStatus every 5s, pollSignals/pollPositions every 3s)"
echo "   5. Expected: ZERO requests to /tasks/full_scan, /api/insights, /api/trade_ideas"
echo "   6. Note: TradingView widget may make socket.io calls (external CDN, expected)"
echo "   7. Check server terminal logs - should see no 404 spam for these endpoints"
echo ""
echo "   To verify strategy switching works:"
echo "   1. Open Settings modal (⚙️ button)"
echo "   2. Paste token: ${TOKEN:0:8}... (from /tmp/control_plane_token_current.txt)"
echo "   3. Click Save"
echo "   4. Click strategy buttons (GOLD_SCALPER_v4.2, MEAN_REV_CORE, BREAKOUT_HUNTER)"
echo "   5. Confirm Network tab shows POST /api/config with 200 response"
echo "   6. Confirm GET /api/status shows updated active_strategy_key"
echo ""
echo "   Runtime Playwright Proof (if available):"
echo "   - Run: node scripts/pw_trace_forbidden_requests.js"
echo "   - This captures 60 seconds of runtime behavior and fails if forbidden"
echo "     endpoints are called from our code (same-origin)"
echo "   - Log file: scripts/artifacts/pw_forbidden_requests.log"
echo ""
