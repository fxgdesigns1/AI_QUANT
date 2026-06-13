#!/bin/bash
# verify_live_prices.sh — Verify live prices endpoint returns non-empty prices
#
# USAGE:
#   ENV_FILE=.env bash scripts/verify_live_prices.sh
#   ENV_FILE=/etc/ai-quant/.env bash scripts/verify_live_prices.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env}"
CP_BASE="${CP_BASE:-http://127.0.0.1:8787}"

# Load env if provided
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

echo "=== Verifying Live Prices Endpoint ==="
echo "Control plane: $CP_BASE"
echo ""

MAX_WAIT=60
WAIT_COUNT=0
SUCCESS=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # Check if control plane is running
    if ! curl -sf "${CP_BASE}/health" > /dev/null 2>&1; then
        echo "[WAIT] Control plane not responding (${WAIT_COUNT}s)..."
        sleep 2
        WAIT_COUNT=$((WAIT_COUNT + 2))
        continue
    fi
    
    # Check live prices endpoint
    RESPONSE=$(curl -sf "${CP_BASE}/api/sidebar/live-prices" 2>/dev/null || echo "{}")
    
    if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "{}" ]; then
        echo "[WAIT] Waiting for prices (${WAIT_COUNT}s)..."
        sleep 2
        WAIT_COUNT=$((WAIT_COUNT + 2))
        continue
    fi
    
    # Parse response (basic check)
    PRICES_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('prices', {})))" 2>/dev/null || echo "0")
    
    if [ "$PRICES_COUNT" -gt 0 ]; then
        echo "[SUCCESS] Live prices available: $PRICES_COUNT instruments"
        echo ""
        echo "Sample response:"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$RESPONSE"
        SUCCESS=1
        break
    else
        WARNING=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('warning', 'none'))" 2>/dev/null || echo "unknown")
        REASON=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('reason', 'none'))" 2>/dev/null || echo "unknown")
        echo "[WAIT] Prices empty (warning: $WARNING, reason: $REASON) (${WAIT_COUNT}s)..."
        sleep 2
        WAIT_COUNT=$((WAIT_COUNT + 2))
    fi
done

if [ $SUCCESS -eq 0 ]; then
    echo ""
    echo "[FAIL] Live prices not available after ${MAX_WAIT}s"
    echo ""
    echo "Diagnostics:"
    echo "  Control plane health:"
    curl -sf "${CP_BASE}/health" && echo "" || echo "  ❌ Control plane not responding"
    
    echo "  Status snapshot:"
    if [ -f "$REPO_ROOT/runtime/status.json" ]; then
        echo "  Snapshot exists, contents:"
        python3 -c "
import json, sys
try:
    with open('$REPO_ROOT/runtime/status.json') as f:
        d = json.load(f)
        print(f\"  accounts_loaded: {d.get('accounts_loaded', 'missing')}\")
        print(f\"  accounts_total: {d.get('accounts_total', 'missing')}\")
        print(f\"  live_prices count: {len(d.get('live_prices', {}))}\")
        print(f\"  last_scan_iso: {d.get('last_scan_iso', 'missing')}\")
        print(f\"  timestamp_iso: {d.get('timestamp_iso', 'missing')}\")
except Exception as e:
    print(f\"  Error reading snapshot: {e}\")
" || echo "  ❌ Failed to read snapshot"
    else
        echo "  ❌ Snapshot file not found: $REPO_ROOT/runtime/status.json"
    fi
    
    echo ""
    echo "  Live prices endpoint response:"
    curl -sf "${CP_BASE}/api/sidebar/live-prices" | python3 -m json.tool 2>/dev/null || curl -sf "${CP_BASE}/api/sidebar/live-prices"
    
    exit 1
fi

echo ""
echo "✅ PASS: Live prices verification successful"
