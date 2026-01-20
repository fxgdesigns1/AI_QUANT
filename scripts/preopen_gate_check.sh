#!/bin/bash
# Pre-open gate checker script
# Checks DNS, health, and status freshness gates

set -euo pipefail

ERRORS=()

# Gate 1: DNS resolution
if ! getent hosts api-fxpractice.oanda.com >/dev/null 2>&1; then
    ERRORS+=("DNS_RESOLUTION_FAIL")
fi

# Gate 2: DNS connectivity (HTTPS)
if ! curl -I https://api-fxpractice.oanda.com/v3/accounts --max-time 10 --silent --output /dev/null 2>&1; then
    ERRORS+=("DNS_CONNECTIVITY_FAIL")
fi

# Gate 3: Health endpoint
if ! curl -sS http://127.0.0.1:8787/health --max-time 5 | grep -q "ok"; then
    ERRORS+=("HEALTH_FAIL")
fi

# Gate 4: Status freshness (last_scan_at not null and not older than 120s)
STATUS=$(curl -sS http://127.0.0.1:8787/api/status --max-time 5 || echo "{}")
LAST_SCAN=$(echo "$STATUS" | jq -r ".last_scan_at // empty" 2>/dev/null || echo "")

if [ -z "$LAST_SCAN" ] || [ "$LAST_SCAN" = "null" ]; then
    ERRORS+=("STATUS_FRESHNESS_FAIL:last_scan_at_null")
else
    # Parse ISO timestamp and check age
    SCAN_TS=$(date -d "$LAST_SCAN" +%s 2>/dev/null || echo "0")
    NOW_TS=$(date +%s)
    AGE=$((NOW_TS - SCAN_TS))
    
    if [ "$AGE" -gt 120 ]; then
        ERRORS+=("STATUS_FRESHNESS_FAIL:last_scan_at_stale_${AGE}s")
    fi
fi

# Report result
if [ ${#ERRORS[@]} -gt 0 ]; then
    echo "PREOPEN_GATE_FAIL reason=$(IFS=,; echo "${ERRORS[*]}")" >&2
    exit 1
else
    echo "PREOPEN_GATE_PASS: DNS, health, and status freshness verified"
    exit 0
fi
