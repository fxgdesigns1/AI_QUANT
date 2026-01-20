#!/bin/bash
# verify_repo_no_secrets.sh — Fast redacted scanner for repository secrets
#
# WHAT IT DOES:
# - Scans repo for high-risk secret patterns
# - EXCLUDES: QUARANTINE/**, ARTIFACTS/**, node_modules/**, .git/**
# - Prints REDACTED matches only (never full secrets)
# - Exits non-zero if HIGH-RISK patterns found outside allowed paths
#
# USAGE:
#   bash scripts/security/verify_repo_no_secrets.sh
#   VERBOSE=1 bash scripts/security/verify_repo_no_secrets.sh  # show all matches

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

VERBOSE="${VERBOSE:-0}"
EXIT_CODE=0

echo "=== FXG AI-QUANT — Repository Secrets Verification ==="
echo "Repo root: $REPO_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Temp file for raw hits
RAW_HITS=$(mktemp)
trap "rm -f $RAW_HITS" EXIT

# === HIGH-RISK PATTERNS ===
# These MUST NOT appear outside QUARANTINE/ARTIFACTS

echo "--- Scanning for HIGH-RISK patterns ---"

# Pattern 1: OpenAI API keys
rg -n --no-ignore-vcs "sk-[A-Za-z0-9]{20,}" \
    --glob '!QUARANTINE/**' \
    --glob '!ARTIFACTS/**' \
    --glob '!node_modules/**' \
    --glob '!.git/**' \
    --glob '!*.log' \
    . 2>/dev/null >> "$RAW_HITS" || true

# Pattern 2: Google API keys (AIza...)
rg -n --no-ignore-vcs "AIza[0-9A-Za-z\-_]{30,}" \
    --glob '!QUARANTINE/**' \
    --glob '!ARTIFACTS/**' \
    --glob '!node_modules/**' \
    --glob '!.git/**' \
    --glob '!*.log' \
    . 2>/dev/null >> "$RAW_HITS" || true

# Pattern 3: Private keys
rg -n --no-ignore-vcs "-----BEGIN (RSA|EC|OPENSSH|PRIVATE) PRIVATE KEY-----" \
    --glob '!QUARANTINE/**' \
    --glob '!ARTIFACTS/**' \
    --glob '!node_modules/**' \
    --glob '!.git/**' \
    --glob '!*.log' \
    . 2>/dev/null >> "$RAW_HITS" || true

# Pattern 4: Hardcoded OANDA API key assignments (not just getenv references)
rg -n --no-ignore-vcs "OANDA_API_KEY\s*=\s*['\"][a-zA-Z0-9\-]{20,}['\"]" \
    --glob '!QUARANTINE/**' \
    --glob '!ARTIFACTS/**' \
    --glob '!node_modules/**' \
    --glob '!.git/**' \
    --glob '!*.log' \
    --glob '!*.md' \
    . 2>/dev/null >> "$RAW_HITS" || true

# Pattern 5: Hardcoded Telegram bot tokens
rg -n --no-ignore-vcs "TELEGRAM_BOT_TOKEN\s*=\s*['\"][0-9]{9,}:[A-Za-z0-9_\-]{30,}['\"]" \
    --glob '!QUARANTINE/**' \
    --glob '!ARTIFACTS/**' \
    --glob '!node_modules/**' \
    --glob '!.git/**' \
    --glob '!*.log' \
    --glob '!*.md' \
    . 2>/dev/null >> "$RAW_HITS" || true

# Pattern 6: Systemd Environment= directives with hardcoded secrets (literal values only)
rg -n --no-ignore-vcs "Environment=(OANDA_API_KEY|TELEGRAM_BOT_TOKEN|OPENAI_API_KEY|GEMINI_API_KEY|GOOGLE_API_KEY|MARKETAUX_KEY|MARKETAUX_KEYS)=\S+" \
    --glob '!QUARANTINE/**' \
    --glob '!ARTIFACTS/**' \
    --glob '!node_modules/**' \
    --glob '!.git/**' \
    --glob '!*.log' \
    --glob '!*.md' \
    --type-add 'service:*.service' \
    . 2>/dev/null >> "$RAW_HITS" || true

# Count high-risk hits
HIGH_RISK_COUNT=$(wc -l < "$RAW_HITS" | tr -d ' ')

if [ "$HIGH_RISK_COUNT" -gt 0 ]; then
    echo "[FAIL] Found $HIGH_RISK_COUNT HIGH-RISK pattern matches outside QUARANTINE/ARTIFACTS"
    echo ""
    echo "--- Redacted matches (first 8 chars of sensitive values) ---"
    
    # Redact and display
    while IFS= read -r line; do
        # Redact API keys (show first 8 chars only)
        redacted=$(echo "$line" | sed -E '
            s/(sk-[A-Za-z0-9]{8})[A-Za-z0-9]+/\1…REDACTED/g
            s/(AIza[0-9A-Za-z\-_]{6})[0-9A-Za-z\-_]+/\1…REDACTED/g
            s/(API_KEY\s*=\s*['\''"]?[A-Za-z0-9\-]{8})[A-Za-z0-9\-]+/\1…REDACTED/gi
            s/(BOT_TOKEN\s*=\s*['\''"]?[0-9]{8})[0-9:A-Za-z_\-]+/\1…REDACTED/gi
            s/(-----BEGIN )[A-Z ]+( PRIVATE KEY-----)/\1REDACTED\2/g
        ')
        echo "  $redacted"
    done < "$RAW_HITS"
    
    EXIT_CODE=1
else
    echo "[PASS] No HIGH-RISK patterns found outside QUARANTINE/ARTIFACTS"
fi

echo ""

# === MEDIUM-RISK PATTERNS ===
# These are warnings but don't fail the check

MEDIUM_HITS=$(mktemp)
trap "rm -f $RAW_HITS $MEDIUM_HITS" EXIT

echo "--- Scanning for MEDIUM-RISK patterns (warnings) ---"

# Service files with Environment= directives
rg -l --no-ignore-vcs "Environment=.*(_KEY|_TOKEN|_SECRET)=" \
    --glob '!QUARANTINE/**' \
    --glob '!ARTIFACTS/**' \
    --glob '!*.md' \
    --glob '!.git/**' \
    --type-add 'service:*.service' \
    . 2>/dev/null >> "$MEDIUM_HITS" || true

# .env files outside gitignore
find . -maxdepth 4 -name "*.env" -type f 2>/dev/null | \
    grep -v QUARANTINE | grep -v ARTIFACTS | grep -v node_modules >> "$MEDIUM_HITS" || true

MEDIUM_COUNT=$(wc -l < "$MEDIUM_HITS" | tr -d ' ')

if [ "$MEDIUM_COUNT" -gt 0 ]; then
    echo "[WARN] Found $MEDIUM_COUNT MEDIUM-RISK files (should be gitignored or quarantined)"
    if [ "$VERBOSE" = "1" ]; then
        cat "$MEDIUM_HITS" | head -20 | sed 's/^/  /'
    else
        echo "  (Run with VERBOSE=1 to see file list)"
    fi
else
    echo "[OK] No MEDIUM-RISK patterns found"
fi

echo ""

# === SUMMARY ===

echo "=== Verification Summary ==="
echo "HIGH-RISK matches: $HIGH_RISK_COUNT"
echo "MEDIUM-RISK files: $MEDIUM_COUNT"
echo ""

if [ "$EXIT_CODE" = "0" ]; then
    echo "✅ PASS — Repository is clean of high-risk secrets outside quarantine paths"
else
    echo "❌ FAIL — High-risk patterns detected. Review and quarantine before deployment."
    echo ""
    echo "Remediation:"
    echo "  1. Run: bash scripts/security/quarantine_sensitive_artifacts.sh"
    echo "  2. Verify .gitignore covers sensitive paths"
    echo "  3. Re-run this script to confirm"
fi

exit $EXIT_CODE
