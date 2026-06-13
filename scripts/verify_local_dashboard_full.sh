#!/bin/bash
set -e

# Configuration
PROJECT_ROOT="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
FRONTEND_DIR="$PROJECT_ROOT/frontend/fxg-dashboard"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/playwright"
TELEGRAM_SCRIPT="$PROJECT_ROOT/scripts/send_telegram_message.py"

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

echo "========================================================"
echo "   HARD-GATED DASHBOARD VERIFICATION PROTOCOL"
echo "========================================================"
echo "1. Wiring Data Pipeline..."

# 1. Run Data Sync (ensure we have latest data)
# Using local_oanda_trade_pull.py as it seems to be the one recently viewed/used
echo "   Running local_oanda_trade_pull.py..."
cd "$PROJECT_ROOT"
python3 scripts/local_oanda_trade_pull.py || {
    echo "❌ Data Sync Failed!"
    python3 "$TELEGRAM_SCRIPT" "❌ Dashboard Verification FAILED: Data sync pipeline crashed."
    exit 1
}

# 2. Start API Server
echo "2. Starting Local API Server..."
# Using dashboard/api_local.py based on file list
python3 dashboard/api_local.py > "$ARTIFACTS_DIR/api.log" 2>&1 &
API_PID=$!
echo "   API Server PID: $API_PID"

# 3. Start Frontend
echo "3. Starting Frontend..."
cd "$FRONTEND_DIR"
npm run dev -- --port 5173 > "$ARTIFACTS_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Wait for services to spin up
echo "   Waiting 10s for services..."
sleep 10

# 4. Run Playwright Verification
echo "4. Executing Playwright Hard Gate..."
cd "$PROJECT_ROOT"
# Ensure playwright is installed
if ! npx playwright --version > /dev/null 2>&1; then
    echo "   Installing Playwright..."
    npm install -D @playwright/test
    npx playwright install chromium
fi

# Run the specific test
# We need to run from root but point to the config correctly or just rely on default behavior
# The error "No tests found" often happens when the path provided doesn't match testDir logic.
# Let's try specifying the config explicitly.
set +e # Allow fail to capture exit code
npx playwright test tests/playwright/local_dashboard.spec.ts --config=tests/playwright/playwright.config.ts --project=chromium --reporter=list
TEST_EXIT_CODE=$?
set -e

# 5. Enforce Gate
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Playwright Verification PASSED."
    
    # Gather stats for telegram
    # We can try to grep them from the log or just send the success message with screenshots
    echo "   Sending Telegram SUCCESS..."
    
    # We'll attach the screenshot if possible, or just text.
    # The python script might not support attachments easily, so we'll send text.
    # If the python script supports image path as second arg, we use it.
    
    python3 "$TELEGRAM_SCRIPT" "✅ VERIFIED – PLAYWRIGHT CONFIRMED DATA RENDERED.
    
    The local dashboard has been verified with visual proof.
    - API connection: OK
    - Data rendering: OK
    - Empty states/Stats: OK
    
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
    python3 "$TELEGRAM_SCRIPT" "❌ FAILED – PLAYWRIGHT DID NOT SEE DATA.
    
    The local dashboard failed visual verification.
    - Check artifacts/playwright/ for failure screenshots (if any).
    - Check api.log and frontend.log for errors."
    
    echo "========================================================"
    echo "   VERIFICATION COMPLETE: FAILED"
    echo "========================================================"
    
    # Cleanup
    kill $API_PID
    kill $FRONTEND_PID
    exit 1
fi
