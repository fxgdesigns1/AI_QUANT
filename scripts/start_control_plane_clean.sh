#!/bin/bash
# Start Control Plane server with clean state and fresh token

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Step 1: Stop any existing listeners
echo "🛑 Stopping any existing listeners on port 8787..."
bash "$SCRIPT_DIR/stop_control_plane.sh"

# Step 2: Generate or use existing token
if [ -z "${CONTROL_PLANE_TOKEN:-}" ]; then
    echo "🔑 Generating new CONTROL_PLANE_TOKEN..."
    export CONTROL_PLANE_TOKEN="$(openssl rand -hex 32)"
    echo "   Token generated (first 8 chars: ${CONTROL_PLANE_TOKEN:0:8}...)"
    echo ""
    echo "⚠️  IMPORTANT: Save this token for dashboard Settings:"
    echo "   Full token: $CONTROL_PLANE_TOKEN"
    echo "   Or export: export CONTROL_PLANE_TOKEN=\"$CONTROL_PLANE_TOKEN\""
    echo ""
    # Write token to temp file for verification script (user can delete)
    echo "$CONTROL_PLANE_TOKEN" > /tmp/control_plane_token_current.txt 2>/dev/null || true
else
    echo "🔑 Using existing CONTROL_PLANE_TOKEN (first 8 chars: ${CONTROL_PLANE_TOKEN:0:8}...)"
    # Write token to temp file for verification script
    echo "$CONTROL_PLANE_TOKEN" > /tmp/control_plane_token_current.txt 2>/dev/null || true
fi

# Step 3: Ensure directories exist
mkdir -p runtime logs

# Step 4: Check dependencies
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI not installed"
    echo "   Install with: pip install fastapi uvicorn pydantic pyyaml"
    exit 1
fi

# Step 5: Start server (foreground by default, background if CONTROL_PLANE_BG=1)
BG_MODE="${CONTROL_PLANE_BG:-0}"

if [ "$BG_MODE" = "1" ] || [ "$BG_MODE" = "true" ]; then
    echo "🚀 Starting Control Plane server in background mode..."
    echo "   Listening on: http://127.0.0.1:8787"
    echo "   Token (first 8): ${CONTROL_PLANE_TOKEN:0:8}..."
    echo "   PID file: /tmp/control_plane_pid"
    echo "   Log file: /tmp/control_plane.out"
    echo ""
    
    # Start in background, redirect output, store PID
    nohup python3 -m src.control_plane.api > /tmp/control_plane.out 2>&1 &
    SERVER_PID=$!
    echo "$SERVER_PID" > /tmp/control_plane_pid
    echo "   ✅ Server started with PID: $SERVER_PID"
    
    # Poll /api/status until healthy or timeout (30 seconds)
    echo "   Waiting for server to be ready..."
    MAX_WAIT=30
    WAIT_COUNT=0
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
        
        # Check if process is still running
        if ! kill -0 "$SERVER_PID" 2>/dev/null; then
            echo "   ❌ Server process died (check /tmp/control_plane.out for errors)"
            exit 1
        fi
        
        # Try to reach /api/status
        if curl -sf http://127.0.0.1:8787/api/status > /dev/null 2>&1; then
            echo "   ✅ Server is ready (took ${WAIT_COUNT}s)"
            
            # Runtime guard: Verify deployed_version endpoint
            echo "   🔍 Verifying deployed version..."
            VERSION_RESPONSE=$(curl -sf http://127.0.0.1:8787/api/system/deployed_version 2>&1)
            if [ $? -eq 0 ]; then
                GIT_HASH=$(echo "$VERSION_RESPONSE" | grep -o '"git_hash":"[^"]*"' | cut -d'"' -f4 || echo "UNKNOWN")
                MODE=$(echo "$VERSION_RESPONSE" | grep -o '"mode":"[^"]*"' | cut -d'"' -f4 || echo "UNKNOWN")
                echo "   ✅ Version check passed (git_hash: ${GIT_HASH:0:8}..., mode: $MODE)"
                
                # Optional: Check against expected hash if EXPECTED_GIT_HASH is set
                if [ -n "${EXPECTED_GIT_HASH:-}" ]; then
                    if [ "$GIT_HASH" != "$EXPECTED_GIT_HASH" ]; then
                        echo "   ❌ VERSION MISMATCH: Expected $EXPECTED_GIT_HASH, got $GIT_HASH" >&2
                        echo "   ❌ Deployment verification FAILED - exiting" >&2
                        kill "$SERVER_PID" 2>/dev/null || true
                        exit 1
                    else
                        echo "   ✅ Git hash matches expected: ${GIT_HASH:0:8}..."
                    fi
                fi
            else
                echo "   ⚠️  Could not verify deployed version (endpoint may not be available yet)"
            fi
            
            echo ""
            echo "📋 Background server info:"
            echo "   PID: $SERVER_PID (stored in /tmp/control_plane_pid)"
            echo "   Logs: tail -f /tmp/control_plane.out"
            echo "   Stop: bash scripts/stop_control_plane.sh"
            echo ""
            exit 0
        fi
    done
    
    echo "   ⚠️  Server started but did not become ready within ${MAX_WAIT}s"
    echo "   Check logs: tail -f /tmp/control_plane.out"
    echo "   PID: $SERVER_PID"
    exit 1
else
    echo "🚀 Starting Control Plane server (foreground mode)..."
    echo "   Listening on: http://127.0.0.1:8787"
    echo "   Token (first 8): ${CONTROL_PLANE_TOKEN:0:8}..."
    echo "   (Press Ctrl+C to stop)"
    echo ""
    echo "   💡 To run in background: CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh"
    echo ""
    
    # Run in foreground (user can Ctrl+C or background with &)
    python3 -m src.control_plane.api
fi
