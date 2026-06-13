#!/bin/bash
set -e

# Configuration
PROJECT_ROOT="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
FRONTEND_DIR="$PROJECT_ROOT/frontend/fxg-dashboard"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/playwright"
TELEGRAM_SCRIPT="$PROJECT_ROOT/scripts/send_telegram_message.py"
DATA_SOURCE="vm_logs" # Enforce VM Logs

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

echo "========================================================"
echo "   VM LOG TRUTH - DASHBOARD VERIFICATION PROTOCOL"
echo "========================================================"

# 1. Run VM Log Parser
echo "1. Parsing VM Execution Logs..."
cd "$PROJECT_ROOT"
python3 src/analytics/vm_trade_log_parser.py || {
    echo "❌ VM Log Parsing Failed!"
    python3 "$TELEGRAM_SCRIPT" "❌ Dashboard Verification FAILED: VM Log Parser crashed."
    exit 1
}

# 2. Run Stats Engine (re-compute stats from VM logs)
echo "2. Computing Authoritative Stats..."
python3 src/analytics/stats_engine.py || {
    echo "❌ Stats Engine Failed!"
    python3 "$TELEGRAM_SCRIPT" "❌ Dashboard Verification FAILED: Stats Engine crashed."
    exit 1
}

# 3. Start API Server (with VM Logs source)
echo "3. Starting Local API Server (Source: $DATA_SOURCE)..."
export DASHBOARD_DATA_SOURCE="$DATA_SOURCE"
python3 dashboard/api_local.py > "$ARTIFACTS_DIR/api_vm.log" 2>&1 &
API_PID=$!
echo "   API Server PID: $API_PID"

# 4. Start Frontend
echo "4. Starting Frontend..."
cd "$FRONTEND_DIR"
npm run dev -- --port 5173 > "$ARTIFACTS_DIR/frontend_vm.log" 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Wait for services to spin up
echo "   Waiting 10s for services..."
sleep 10

# 5. Run Playwright Verification
echo "5. Executing Playwright Hard Gate (VM LOGS)..."
cd "$PROJECT_ROOT"
# Ensure playwright is installed
if ! npx playwright --version > /dev/null 2>&1; then
    echo "   Installing Playwright..."
    npm install -D @playwright/test
    npx playwright install chromium
fi

# Run the specific test
set +e # Allow fail to capture exit code
npx playwright test tests/playwright/local_dashboard_vm_logs.spec.ts --config=tests/playwright/playwright.config.ts --project=chromium --reporter=list
TEST_EXIT_CODE=$?
set -e

# 6. Enforce Gate
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Playwright Verification PASSED."
    
    echo "   Sending Telegram SUCCESS..."
    python3 "$TELEGRAM_SCRIPT" "✅ VM LOG ANALYTICS VERIFIED.
    
    The local dashboard is now serving authoritative data from VM execution logs.
    - Source: VM Execution Logs (vm_trades_flat.json)
    - Parser: Verified
    - UI: Verified via Playwright
    
    Screenshots saved to artifacts/playwright/"
    
    echo "========================================================"
    echo "   VERIFICATION COMPLETE: SUCCESS"
    echo "========================================================"
    
    # Cleanup
    kill $API_PID
    kill $FRONTEND_PID
    exit 0

else
    echo "❌ Playwright Verification FAILED."
    
    echo "   Sending Telegram FAILURE..."
    python3 "$TELEGRAM_SCRIPT" "❌ FAILED – DASHBOARD REJECTED VM DATA.
    
    The local dashboard failed visual verification against VM logs.
    - Check artifacts/playwright/ for failure screenshots.
    - Check api_vm.log for data loading errors."
    
    echo "========================================================"
    echo "   VERIFICATION COMPLETE: FAILED"
    echo "========================================================"
    
    # Cleanup
    kill $API_PID
    kill $FRONTEND_PID
    exit 1
fi
