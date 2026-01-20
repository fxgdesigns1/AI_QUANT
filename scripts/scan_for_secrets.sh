#!/usr/bin/env bash
# Scan for secrets in tracked git files (working tree only)
# 
# This script scans tracked files for high-risk secret patterns.
# It does NOT print secret values - only file paths, line numbers, and pattern names.
#
# Exit codes:
#   0 = PASS (no secrets found)
#   1 = FAIL (secrets found in tracked files)
#   2 = ERROR (script error)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# High-risk patterns (from task spec)
# Note: These are designed to catch real secrets, not placeholders like "your_key_here"
declare -a PATTERNS=(
    # Private keys
    '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
    # OpenAI keys
    'sk-[A-Za-z0-9_-]{20,}'
    # Google API keys
    'AIza[0-9A-Za-z_-]{35,}'
    # Telegram bot tokens (format: NNNNN:...)
    'bot[0-9]{5,}:[A-Za-z0-9_-]{20,}'
    # OANDA keys (in assignment context)
    'OANDA_API_KEY\s*[:=]\s*['\''"]?[A-Za-z0-9_-]{20,}'
    # Telegram tokens (in assignment context)
    'TELEGRAM_BOT_TOKEN\s*[:=]\s*['\''"]?[0-9]{5,}:[A-Za-z0-9_-]{20,}'
)

# Pattern names for reporting
declare -a PATTERN_NAMES=(
    'PRIVATE_KEY'
    'OPENAI_SK_KEY'
    'GOOGLE_API_KEY'
    'TELEGRAM_BOT_TOKEN'
    'OANDA_API_KEY_ASSIGNMENT'
    'TELEGRAM_TOKEN_ASSIGNMENT'
)

# Exclude patterns (placeholders, examples, comments)
declare -a EXCLUDE_PATTERNS=(
    'your.*key.*here'
    'your.*token.*here'
    'your.*api.*key'
    'placeholder'
    'example'
    'REDACTED'
    '\.example'
    '\.template'
    '\.env\.example'
)

# Check if git is available
if ! command -v git >/dev/null 2>&1; then
    echo "❌ ERROR: git command not found" >&2
    exit 2
fi

# Check if we're in a git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "❌ ERROR: Not in a git repository" >&2
    exit 2
fi

echo "🔍 Scanning tracked files for secrets..."
echo ""

# Get list of tracked files (excluding .git directory)
TRACKED_FILES=$(git ls-files 2>/dev/null || echo "")

if [ -z "$TRACKED_FILES" ]; then
    echo "⚠️  No tracked files found"
    exit 0
fi

FOUND_COUNT=0
MATCHES_FILE=$(mktemp)
trap "rm -f '$MATCHES_FILE'" EXIT

# Use ripgrep if available, fallback to grep
if command -v rg >/dev/null 2>&1; then
    GREP_CMD="rg"
    GREP_FLAGS="-n"
else
    GREP_CMD="grep"
    GREP_FLAGS="-nH"
fi

# Scan each pattern
for i in "${!PATTERNS[@]}"; do
    PATTERN="${PATTERNS[$i]}"
    PATTERN_NAME="${PATTERN_NAMES[$i]}"
    
    # Search in tracked files
    while IFS= read -r file; do
        # Skip binary files
        if file "$file" 2>/dev/null | grep -qi "binary"; then
            continue
        fi
        
        # Search for pattern
        if [ "$GREP_CMD" = "rg" ]; then
            MATCHES=$($GREP_CMD $GREP_FLAGS -e "$PATTERN" "$file" 2>/dev/null || true)
        else
            MATCHES=$($GREP_CMD $GREP_FLAGS -E "$PATTERN" "$file" 2>/dev/null || true)
        fi
        
        if [ -n "$MATCHES" ]; then
            # Filter out excluded patterns (placeholders)
            FILTERED=""
            while IFS= read -r line; do
                IS_EXCLUDED=0
                for exclude in "${EXCLUDE_PATTERNS[@]}"; do
                    if echo "$line" | grep -qiE "$exclude"; then
                        IS_EXCLUDED=1
                        break
                    fi
                done
                if [ "$IS_EXCLUDED" -eq 0 ]; then
                    # Check if it's a real secret (not a placeholder)
                    # Real secrets are typically longer and don't contain "your" or "here"
                    if ! echo "$line" | grep -qiE "(your|here|placeholder|example|REDACTED)"; then
                        FILTERED="${FILTERED}${line}"$'\n'
                    fi
                fi
            done <<< "$MATCHES"
            
            if [ -n "$FILTERED" ]; then
                echo "$FILTERED" | while IFS= read -r match_line; do
                    if [ -n "$match_line" ]; then
                        echo "$file|$match_line|$PATTERN_NAME" >> "$MATCHES_FILE"
                        FOUND_COUNT=$((FOUND_COUNT + 1))
                    fi
                done
            fi
        fi
    done <<< "$TRACKED_FILES"
done

# Report results
if [ "$FOUND_COUNT" -eq 0 ]; then
    echo "✅ PASS: No secrets found in tracked files"
    echo ""
    echo "📋 Summary:"
    echo "   Scanned: $(echo "$TRACKED_FILES" | wc -l | tr -d ' ') tracked files"
    echo "   Patterns checked: ${#PATTERNS[@]}"
    echo "   Matches: 0"
    exit 0
else
    echo "❌ FAIL: Found $FOUND_COUNT potential secret(s) in tracked files"
    echo ""
    echo "📋 Matches (file|line|pattern):"
    while IFS='|' read -r file line pattern; do
        if [ -n "$file" ]; then
            # Extract line number if present
            LINE_NUM=$(echo "$line" | grep -oE '^[0-9]+:' | tr -d ':' || echo "?")
            # Extract just the pattern match (truncated, no actual secret)
            MATCH_PREVIEW=$(echo "$line" | sed 's/^[0-9]*://' | head -c 80)
            echo "   $file:$LINE_NUM [$pattern] ${MATCH_PREVIEW}..."
        fi
    done < "$MATCHES_FILE"
    echo ""
    echo "⚠️  Action required:"
    echo "   1. Remove secrets from tracked files"
    echo "   2. Ensure .env is gitignored (check: git check-ignore -v .env)"
    echo "   3. If secrets were in git history, run: bash scripts/purge_secrets_history.sh"
    exit 1
fi
