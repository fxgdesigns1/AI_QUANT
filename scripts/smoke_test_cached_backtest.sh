#!/usr/bin/env bash
# Smoke Test: Cached Candle Backtest
# Verifies deterministic backtest runs without OANDA env vars

set -euo pipefail

LOCAL_ROOT="${HOME}/fxg-ai-quant-local"
REPO_ROOT="${LOCAL_ROOT}/repo"
VENV="${LOCAL_ROOT}/venv"

echo "======================================================================"
echo "=== CACHED BACKTEST SMOKE TEST ==="
echo "======================================================================"
echo ""

# Activate venv if it exists
if [ -d "${VENV}" ]; then
    source "${VENV}/bin/activate"
    echo "✅ Activated Python venv"
else
    echo "⚠️  Venv not found at ${VENV}, using system Python"
fi

# Verify OANDA env vars are NOT set (for cached mode)
if [ -n "${OANDA_API_KEY:-}" ]; then
    echo "⚠️  OANDA_API_KEY is set (will be ignored in cached mode)"
else
    echo "✅ OANDA_API_KEY not set (correct for cached mode)"
fi

# Check for cached candles
CANDLE_CACHE="${LOCAL_ROOT}/artifacts/candles/tournament_dataset_20260307T222011Z_recent30_enriched"
if [ ! -d "${CANDLE_CACHE}" ]; then
    echo "❌ Candle cache not found: ${CANDLE_CACHE}"
    echo "   Run: bash ${REPO_ROOT}/scripts/sync_vm_artifacts.sh"
    exit 1
fi
echo "✅ Candle cache found: ${CANDLE_CACHE}"

# Check for tournament config
TOURNAMENT_CONFIG="${LOCAL_ROOT}/artifacts/backtests/tournament_dataset_20260307T222011Z_recent30_enriched_wave2_v1/tournament_config_resolved.json"
if [ ! -f "${TOURNAMENT_CONFIG}" ]; then
    echo "⚠️  Tournament config not found: ${TOURNAMENT_CONFIG}"
    echo "   Will create minimal test config"
    mkdir -p "$(dirname "${TOURNAMENT_CONFIG}")"
    cat > "${TOURNAMENT_CONFIG}" << 'EOF'
{
  "cache_path": "~/fxg-ai-quant-local/artifacts/candles/tournament_dataset_20260307T222011Z_recent30_enriched",
  "instruments": ["EUR_USD", "GBP_USD"],
  "variants": [
    {
      "variant_id": "test_variant_1",
      "strategy": "momentum_trading"
    }
  ]
}
EOF
    echo "   Created minimal test config"
else
    echo "✅ Tournament config found: ${TOURNAMENT_CONFIG}"
fi

# Run tournament
echo ""
echo "Running cached tournament..."
cd "${REPO_ROOT}"

OUTPUT_DIR="${LOCAL_ROOT}/artifacts/backtests/smoke_test_$(date +%Y%m%dT%H%M%SZ)"
mkdir -p "${OUTPUT_DIR}"

python3 scripts/run_strategy_tournament.py \
    --config "${TOURNAMENT_CONFIG}" \
    --output "${OUTPUT_DIR}" \
    --use-cached-candles

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Smoke test PASSED"
    echo "   Results: ${OUTPUT_DIR}/tournament_results.json"
    exit 0
else
    echo ""
    echo "❌ Smoke test FAILED"
    exit 1
fi
