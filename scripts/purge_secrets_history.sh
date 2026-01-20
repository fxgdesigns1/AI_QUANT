#!/usr/bin/env bash
# Purge secrets from git history using git-filter-repo
#
# This script:
#   1. Scans git history for high-risk secret patterns
#   2. If matches found, runs git-filter-repo to redact them
#   3. Verifies history is clean after rewrite
#
# WARNING: This rewrites git history. Only run on a clean working tree.
#          Make a backup or work on a separate branch first.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Check if git is available
if ! command -v git >/dev/null 2>&1; then
    echo "❌ ERROR: git command not found" >&2
    exit 1
fi

# Check if we're in a git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "❌ ERROR: Not in a git repository" >&2
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠️  WARNING: Uncommitted changes detected" >&2
    echo "   This script rewrites git history. Commit or stash changes first." >&2
    echo "" >&2
    echo "   To proceed anyway (DANGEROUS), set FORCE=1" >&2
    if [ "${FORCE:-0}" != "1" ]; then
        exit 1
    fi
fi

# Check if git-filter-repo is available
GIT_FILTER_REPO=""
if command -v git-filter-repo >/dev/null 2>&1; then
    GIT_FILTER_REPO="git-filter-repo"
elif [ -f "$HOME/.local/bin/git-filter-repo" ]; then
    GIT_FILTER_REPO="$HOME/.local/bin/git-filter-repo"
else
    echo "❌ ERROR: git-filter-repo not found" >&2
    echo "   Install it first: bash scripts/install_git_filter_repo.sh" >&2
    exit 1
fi

echo "🔍 Scanning git history for secrets..."
echo ""

# High-risk patterns (same as scan_for_secrets.sh)
declare -a PATTERNS=(
    '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
    'sk-[A-Za-z0-9_-]{20,}'
    'AIza[0-9A-Za-z_-]{35,}'
    'bot[0-9]{5,}:[A-Za-z0-9_-]{20,}'
    'OANDA_API_KEY\s*[:=]\s*['\''"]?[A-Za-z0-9_-]{20,}'
    'TELEGRAM_BOT_TOKEN\s*[:=]\s*['\''"]?[0-9]{5,}:[A-Za-z0-9_-]{20,}'
)

declare -a PATTERN_NAMES=(
    'PRIVATE_KEY'
    'OPENAI_SK_KEY'
    'GOOGLE_API_KEY'
    'TELEGRAM_BOT_TOKEN'
    'OANDA_API_KEY_ASSIGNMENT'
    'TELEGRAM_TOKEN_ASSIGNMENT'
)

# Scan history for matches
FOUND_IN_HISTORY=0
MATCHES_FILE=$(mktemp)
trap "rm -f '$MATCHES_FILE'" EXIT

# Use git log to search history
for i in "${!PATTERNS[@]}"; do
    PATTERN="${PATTERNS[$i]}"
    PATTERN_NAME="${PATTERN_NAMES[$i]}"
    
    # Search in commit messages and file contents
    # Exclude placeholders
    MATCHES=$(git log --all --source --full-history -S "$PATTERN" --format="%H" 2>/dev/null | head -20 || true)
    
    if [ -n "$MATCHES" ]; then
        # Verify these aren't just placeholders
        for commit in $MATCHES; do
            # Check commit diff for actual secret (not placeholder)
            DIFF=$(git show "$commit" 2>/dev/null | grep -E "$PATTERN" | grep -vE "(your|here|placeholder|example|REDACTED)" || true)
            if [ -n "$DIFF" ]; then
                echo "$commit|$PATTERN_NAME" >> "$MATCHES_FILE"
                FOUND_IN_HISTORY=$((FOUND_IN_HISTORY + 1))
            fi
        done
    fi
done

# Report initial scan
if [ "$FOUND_IN_HISTORY" -eq 0 ]; then
    echo "✅ CLEAN: No secrets found in git history"
    echo ""
    echo "📋 Summary:"
    echo "   History scan: PASS"
    echo "   Matches: 0"
    echo "   Action: No rewrite needed"
    exit 0
fi

echo "⚠️  Found $FOUND_IN_HISTORY potential secret(s) in git history"
echo ""
echo "📋 Affected commits (sample):"
head -10 "$MATCHES_FILE" | while IFS='|' read -r commit pattern; do
    if [ -n "$commit" ]; then
        COMMIT_MSG=$(git log -1 --format="%s" "$commit" 2>/dev/null | head -c 60 || echo "?")
        echo "   $commit [$pattern] $COMMIT_MSG..."
    fi
done
if [ "$FOUND_IN_HISTORY" -gt 10 ]; then
    echo "   ... and $((FOUND_IN_HISTORY - 10)) more"
fi
echo ""

# Confirm before rewrite
echo "⚠️  WARNING: This will rewrite git history"
echo "   - All commit hashes will change"
echo "   - You'll need to force-push to update remote"
echo "   - Collaborators will need to re-clone"
echo ""
read -p "Continue with history rewrite? (type 'yes' to confirm): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Aborted by user"
    exit 1
fi

echo ""
echo "🔧 Running git-filter-repo to redact secrets..."

# Build replace-text commands for each pattern
# Note: We replace with [REDACTED] to preserve structure but remove secrets
REPLACE_ARGS=()
for i in "${!PATTERNS[@]}"; do
    PATTERN="${PATTERNS[$i]}"
    # Escape for git-filter-repo
    ESCAPED_PATTERN=$(echo "$PATTERN" | sed 's/\\/\\\\/g')
    REPLACE_ARGS+=("--replace-text" "-")
    # Create replacement pattern file inline
    echo "regex:$ESCAPED_PATTERN==>[REDACTED_SECRET]" >> "$MATCHES_FILE.replace"
done

# Run git-filter-repo with replace-text
# Use a temporary file for replacement patterns
REPLACE_FILE=$(mktemp)
cat > "$REPLACE_FILE" <<EOF
# Replace secret patterns with [REDACTED_SECRET]
regex:-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----==>[REDACTED_PRIVATE_KEY]
regex:sk-[A-Za-z0-9_-]{20,}==>[REDACTED_OPENAI_KEY]
regex:AIza[0-9A-Za-z_-]{35,}==>[REDACTED_GOOGLE_KEY]
regex:bot[0-9]{5,}:[A-Za-z0-9_-]{20,}==>[REDACTED_TELEGRAM_TOKEN]
regex:OANDA_API_KEY\s*[:=]\s*['\''"]?[A-Za-z0-9_-]{20,}==>OANDA_API_KEY=[REDACTED]
regex:TELEGRAM_BOT_TOKEN\s*[:=]\s*['\''"]?[0-9]{5,}:[A-Za-z0-9_-]{20,}==>TELEGRAM_BOT_TOKEN=[REDACTED]
EOF

# Run git-filter-repo
if $GIT_FILTER_REPO --replace-text "$REPLACE_FILE" --force 2>&1; then
    echo "✅ History rewrite completed"
else
    echo "❌ ERROR: git-filter-repo failed" >&2
    rm -f "$REPLACE_FILE"
    exit 1
fi

rm -f "$REPLACE_FILE"

echo ""
echo "🔍 Verifying history is clean..."

# Rescan history
FOUND_AFTER=0
for i in "${!PATTERNS[@]}"; do
    PATTERN="${PATTERNS[$i]}"
    # Exclude our redaction markers
    MATCHES=$(git log --all --source --full-history -S "$PATTERN" --format="%H" 2>/dev/null | head -5 || true)
    if [ -n "$MATCHES" ]; then
        # Check if matches are just our redaction markers
        for commit in $MATCHES; do
            DIFF=$(git show "$commit" 2>/dev/null | grep -E "$PATTERN" | grep -vE "REDACTED" || true)
            if [ -n "$DIFF" ]; then
                FOUND_AFTER=$((FOUND_AFTER + 1))
            fi
        done
    fi
done

if [ "$FOUND_AFTER" -eq 0 ]; then
    echo "✅ CLEAN: History verification passed"
    echo ""
    echo "📋 Summary:"
    echo "   Initial scan: $FOUND_IN_HISTORY matches"
    echo "   After rewrite: 0 matches"
    echo "   Status: CLEAN"
    echo ""
    echo "⚠️  Next steps:"
    echo "   1. Verify locally: git log --all"
    echo "   2. Force-push to remote: git push --force --all"
    echo "   3. Notify collaborators to re-clone"
    exit 0
else
    echo "❌ WARNING: Still found $FOUND_AFTER potential secret(s) after rewrite"
    echo "   Manual review required"
    exit 1
fi
