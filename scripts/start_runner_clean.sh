#!/usr/bin/env bash
# Start Runner (clean) - SECURITY HARDENED
# - Never prints secrets
# - Validates OANDA credentials
# - Single-instance lock
# - Supports background mode

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# --- .ENV LOADING (AUTHORITATIVE SOURCE) ---
# Support ENV_FILE override (default to repo root .env)
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env}"

# Resolve to absolute path if relative
if [[ "$ENV_FILE" != /* ]]; then
    ENV_FILE="$REPO_ROOT/$ENV_FILE"
fi

# Load .env file if it exists (unless SKIP_DOTENV=1)
if [[ "${SKIP_DOTENV:-0}" != "1" ]] && [[ -f "$ENV_FILE" ]]; then
    echo "📄 Loading environment from: $ENV_FILE"
    # Use set -a to export all variables, then source .env, then set +a
    set -a
    if ! source "$ENV_FILE"; then
        echo "❌ Failed to source env file. Check for syntax errors (KEY=VALUE format only)." >&2
        exit 1
    fi
    set +a
    
    # Safe debug: report presence/length only (never print secret values)
    if [[ -n "${OANDA_API_KEY:-}" ]]; then
        echo "   ✓ OANDA_API_KEY: present (length=${#OANDA_API_KEY})"
    else
        echo "   ⚠️  OANDA_API_KEY: not set"
    fi
    if [[ -n "${OANDA_ACCOUNT_ID:-}" ]]; then
        echo "   ✓ OANDA_ACCOUNT_ID: present (length=${#OANDA_ACCOUNT_ID})"
    else
        echo "   ⚠️  OANDA_ACCOUNT_ID: not set"
    fi
    if [[ -n "${OANDA_BASE_URL:-}" ]]; then
        echo "   ✓ OANDA_BASE_URL: present (length=${#OANDA_BASE_URL})"
    fi
elif [[ "${SKIP_DOTENV:-0}" = "1" ]]; then
    echo "⏭️  Skipping env file load (SKIP_DOTENV=1)"
elif [[ ! -f "$ENV_FILE" ]]; then
    echo "ℹ️  Env file not found: $ENV_FILE (will use environment variables only)"
    echo "   Set ENV_FILE=/path/to/your/env to specify a different file"
fi

# Environment defaults
TRADING_MODE="${TRADING_MODE:-paper}"
PAPER_EXECUTION_ENABLED="${PAPER_EXECUTION_ENABLED:-false}"

# Validate OANDA credentials if account ID is set
if [[ -n "${OANDA_ACCOUNT_ID:-}" ]]; then
    if [[ -z "${OANDA_API_KEY:-}" ]]; then
        echo "❌ OANDA_ACCOUNT_ID is set but OANDA_API_KEY is missing" >&2
        echo "   Set OANDA_API_KEY in .env file or export in your shell environment." >&2
        exit 1
    fi
    echo "   ✅ OANDA credentials validated (presence only)"
else
    echo "   ⚠️  OANDA_ACCOUNT_ID not set - runner will run in signals-only mode (no accounts loaded)"
fi

# Check for existing runner lock
LOCK_FILE="/tmp/ai_quant_runner.lock"
if [[ -f "$LOCK_FILE" ]]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [[ -n "$LOCK_PID" ]] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "❌ Runner is already running (PID: $LOCK_PID)" >&2
        echo "   Stop it first: pkill -f 'runner_src.runner.main'" >&2
        exit 1
    else
        # Stale lock file, remove it
        rm -f "$LOCK_FILE"
    fi
fi

# Step 1: Ensure directories exist
mkdir -p runtime logs

# Step 2: Check dependencies
if ! python3 -c "import requests" 2>/dev/null; then
    echo "❌ requests not installed"
    echo "   Install with: pip install requests"
    exit 1
fi

# Step 3: Start runner (foreground by default, background if RUNNER_BG=1)
BG_MODE="${RUNNER_BG:-0}"

if [ "$BG_MODE" = "1" ] || [ "$BG_MODE" = "true" ]; then
    echo "🚀 Starting Runner in background mode..."
    echo "   Trading mode: $TRADING_MODE"
    echo "   Paper execution: $PAPER_EXECUTION_ENABLED"
    echo "   PID file: /tmp/runner_pid"
    echo "   Log file: logs/runner.log"
    echo ""
    
    # Ensure logs directory exists
    mkdir -p logs
    
    # Start in background, redirect output to logs/runner.log, store PID
    nohup python3 -m runner_src.runner.main > logs/runner.log 2>&1 &
    RUNNER_PID=$!
    echo "$RUNNER_PID" > /tmp/runner_pid
    echo "   ✅ Runner started with PID: $RUNNER_PID"
    
    # Wait a moment for startup
    sleep 2
    
    # Check if process is still running
    if ! kill -0 "$RUNNER_PID" 2>/dev/null; then
        echo "   ❌ Runner process died (check logs/runner.log for errors)"
        exit 1
    fi
    
    echo "   ✅ Runner is running"
    echo ""
    echo "📋 Background runner info:"
    echo "   PID: $RUNNER_PID (stored in /tmp/runner_pid)"
    echo "   Logs: tail -f logs/runner.log"
    echo "   Stop: pkill -f 'runner_src.runner.main'"
    echo ""
    exit 0
else
    echo "🚀 Starting Runner (foreground mode)..."
    echo "   Trading mode: $TRADING_MODE"
    echo "   Paper execution: $PAPER_EXECUTION_ENABLED"
    echo "   (Press Ctrl+C to stop)"
    echo ""
    echo "   💡 To run in background: RUNNER_BG=1 bash scripts/start_runner_clean.sh"
    echo ""
    
    # Run in foreground (user can Ctrl+C or background with &)
    python3 -m runner_src.runner.main
fi
