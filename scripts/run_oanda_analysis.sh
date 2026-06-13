#!/usr/bin/env bash
# Local OANDA Analysis Pipeline Runner
# READ-ONLY, LOCAL-ONLY - No VM interaction, no order placement
# Single authoritative entry point for local analysis

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Ensure logs directory exists
mkdir -p logs

echo "======================================================================"
echo "=== RUNNING LOCAL OANDA ANALYSIS PIPELINE ==="
echo "======================================================================"
echo "Mode: LOCAL-ONLY / READ-ONLY"
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Stage 1: Pull OANDA Transactions
echo "📥 Stage 1: Pulling OANDA transactions..."
python3 scripts/local_oanda_trade_pull.py 2>&1 | tee logs/oanda_pull_latest.log
STAGE1_EXIT=${PIPESTATUS[0]}
if [ $STAGE1_EXIT -ne 0 ]; then
    echo "❌ Stage 1 failed with exit code $STAGE1_EXIT"
    exit $STAGE1_EXIT
fi
echo "✅ Stage 1 complete"
echo ""

# Stage 2: Reconstruct Trades
echo "🔧 Stage 2: Reconstructing trades..."
python3 -m src.analytics.trade_rebuilder 2>&1 | tee logs/trade_rebuild_latest.log
STAGE2_EXIT=${PIPESTATUS[0]}
if [ $STAGE2_EXIT -ne 0 ]; then
    echo "❌ Stage 2 failed with exit code $STAGE2_EXIT"
    exit $STAGE2_EXIT
fi
echo "✅ Stage 2 complete"
echo ""

# Stage 3: Compute Statistics
echo "📊 Stage 3: Computing statistics..."
python3 -m src.analytics.stats_engine 2>&1 | tee logs/stats_engine_latest.log
STAGE3_EXIT=${PIPESTATUS[0]}
if [ $STAGE3_EXIT -ne 0 ]; then
    echo "❌ Stage 3 failed with exit code $STAGE3_EXIT"
    exit $STAGE3_EXIT
fi
echo "✅ Stage 3 complete"
echo ""

# Verification
echo "======================================================================"
echo "=== PIPELINE COMPLETE ==="
echo "======================================================================"
echo ""
echo "📁 Output Files:"
echo "   - data/processed/trades_flat.json"
echo "   - data/processed/stats.json"
echo ""
echo "📝 Log Files:"
echo "   - logs/oanda_pull_latest.log"
echo "   - logs/trade_rebuild_latest.log"
echo "   - logs/stats_engine_latest.log"
echo ""
echo "✅ All stages completed successfully"
echo ""
echo "To start the local dashboard:"
echo "  Terminal 1: python3 dashboard/api_local.py"
echo "  Terminal 2: cd frontend/fxg-dashboard && npm run dev"
echo ""
