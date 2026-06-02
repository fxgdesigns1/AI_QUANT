#!/bin/bash
# Resume full paper operation with fixes applied
# Sets up environment for PAPER execution and runs the runner

# Ensure we are in the repo root
cd "$(dirname "$0")/.."

echo "🚀 Resuming Full Paper Operation..."

# Set Safety & Execution Environment Variables
export TRADING_MODE=paper
export PAPER_EXECUTION_ENABLED=true
export LIVE_TRADING_ENABLED=false
export OANDA_ENV=practice
export AI_INSIGHTS_ENABLED=true
export SYSTEM_LABEL="PAPER-RESUME-FIX"

echo "   Mode: PAPER"
echo "   Execution: ENABLED (Paper)"
echo "   Live Trading: DISABLED (Safety)"
echo "   AI Insights: ENABLED"

# Run the standard runner script
./scripts/start_runner_clean.sh
