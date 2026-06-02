#!/bin/bash
# Stop Control Plane server on port 8787

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "🔍 Checking for listeners on port 8787..."

PIDS=$(lsof -t -iTCP:8787 -sTCP:LISTEN 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    echo "✅ No process listening on port 8787"
    exit 0
fi

echo "📋 Found process(es) on port 8787: $PIDS"

# Try SIGTERM first (graceful shutdown)
for PID in $PIDS; do
    echo "   Sending SIGTERM to PID $PID..."
    kill -TERM "$PID" 2>/dev/null || true
done

# Wait up to 5 seconds for graceful shutdown
for i in {1..5}; do
    sleep 1
    REMAINING=$(lsof -t -iTCP:8787 -sTCP:LISTEN 2>/dev/null || true)
    if [ -z "$REMAINING" ]; then
        echo "✅ Process(es) stopped gracefully"
        exit 0
    fi
done

# If still running, force kill
REMAINING=$(lsof -t -iTCP:8787 -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$REMAINING" ]; then
    echo "⚠️  Process(es) still running, sending SIGKILL..."
    for PID in $REMAINING; do
        kill -9 "$PID" 2>/dev/null || true
    done
    sleep 1
fi

# Final check
FINAL=$(lsof -t -iTCP:8787 -sTCP:LISTEN 2>/dev/null || true)
if [ -z "$FINAL" ]; then
    echo "✅ Port 8787 is now free"
else
    echo "❌ Failed to stop process(es): $FINAL"
    exit 1
fi
