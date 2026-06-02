#!/usr/bin/env bash
# Verify Telegram bot is working
#
# Loads .env and runs telegram_health_check.py
# Never prints secrets; only prints status and hints

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Support ENV_FILE override (default to repo root .env)
ENV_FILE="${ENV_FILE:-.env}"

# Resolve to absolute path if relative
if [[ "$ENV_FILE" != /* ]]; then
    ENV_FILE="$REPO_ROOT/$ENV_FILE"
fi

# Load .env file if it exists (handle permission issues)
if [[ -f "$ENV_FILE" ]]; then
    echo "📄 Loading environment from: $ENV_FILE"
    if [[ -r "$ENV_FILE" ]]; then
        set -a
        # shellcheck disable=SC1091
        source "$ENV_FILE"
        set +a
    elif command -v sudo >/dev/null 2>&1; then
        # Try to export via sudo if not readable (for /etc/ai-quant/.env)
        eval "$(sudo bash -c "set -a && source $ENV_FILE && env | sed 's/^/export /'")"
    else
        echo "⚠️  Cannot read $ENV_FILE (permission denied) and sudo not available"
    fi
else
    echo "⚠️  Env file not found: $ENV_FILE (using system environment only)"
fi

# Check if Telegram credentials are set
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] || [[ -z "${TELEGRAM_CHAT_ID:-}" ]]; then
    echo "❌ FAIL: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"
    echo "   Set them in .env file:"
    echo "     TELEGRAM_BOT_TOKEN=your-bot-token-here"
    echo "     TELEGRAM_CHAT_ID=your-chat-id-here"
    exit 1
fi

# Run health check (never prints secrets)
echo "🔍 Verifying Telegram bot..."
echo ""

python3 scripts/telegram_health_check.py
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    echo "✅ Telegram verification PASSED"
    exit 0
else
    echo ""
    echo "❌ Telegram verification FAILED (exit code: $EXIT_CODE)"
    exit $EXIT_CODE
fi
