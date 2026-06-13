#!/usr/bin/env bash
# Research-only pipeline: tournament (+ optional Monte Carlo). No execution.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESEARCH_ROOT="${FXG_RESEARCH_ROOT:-${HOME}/fxg-research}"
VENV="${FXG_LOCAL_RESEARCH_VENV:-${RESEARCH_ROOT}/venv}"
export PYTHONPATH="${REPO_ROOT}"

RUN_MC="${RUN_MONTE_CARLO:-1}"
CONFIG_JSON="${TOURNAMENT_CONFIG_JSON:-}"

# shellcheck source=/dev/null
source "${VENV}/bin/activate"

if [ -z "${CONFIG_JSON}" ] || [ ! -f "${CONFIG_JSON}" ]; then
  echo "Set TOURNAMENT_CONFIG_JSON to an existing tournament JSON (with cache_path)."
  echo "Example: TOURNAMENT_CONFIG_JSON=~/mydata/tournament.json"
  exit 1
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${RESEARCH_ROOT}/ARTIFACTS/backtests/run_${TS}"
mkdir -p "${OUT}"

python "${REPO_ROOT}/scripts/run_strategy_tournament.py" \
  --config "${CONFIG_JSON}" \
  --output "${OUT}"

if [ "${RUN_MC}" = "1" ]; then
  MC_OUT="${RESEARCH_ROOT}/ARTIFACTS/monte_carlo/mc_${TS}"
  mkdir -p "${MC_OUT}"
  WORKERS="${MC_WORKERS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 4)}"
  ITERS="${MC_ITERATIONS:-200}"
  SEED="${MC_SEED:-42}"
  python "${REPO_ROOT}/scripts/run_monte_carlo.py" \
    --input-tournament "${OUT}/tournament_results.json" \
    --output "${MC_OUT}" \
    --iterations "${ITERS}" \
    --workers "${WORKERS}" \
    --seed "${SEED}" \
    --mode reshuffle
  echo "MONTE_CARLO_DIR=${MC_OUT}"
else
  echo "MONTE_CARLO_SKIPPED"
fi

echo "TOURNAMENT_DIR=${OUT}"
