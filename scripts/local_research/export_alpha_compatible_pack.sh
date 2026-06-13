#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESEARCH_ROOT="${FXG_RESEARCH_ROOT:-${HOME}/fxg-research}"
VENV="${FXG_LOCAL_RESEARCH_VENV:-${RESEARCH_ROOT}/venv}"
export PYTHONPATH="${REPO_ROOT}"

TOURNAMENT_DIR="${TOURNAMENT_DIR:-}"
MC_SUMMARY="${MONTE_CARLO_SUMMARY:-}"
PACK_ID="${PACK_ID:-pack_$(date -u +%Y%m%dT%H%M%SZ)}"
IMPORT_INTENT="${IMPORT_INTENT:-review_only}"

if [ -z "${TOURNAMENT_DIR}" ] || [ ! -d "${TOURNAMENT_DIR}" ]; then
  echo "Set TOURNAMENT_DIR to a tournament output directory containing report.json."
  exit 1
fi

# shellcheck source=/dev/null
source "${VENV}/bin/activate"

MC_ARG=()
if [ -n "${MC_SUMMARY}" ] && [ -f "${MC_SUMMARY}" ]; then
  MC_ARG=(--monte-carlo-summary "${MC_SUMMARY}")
fi

python "${REPO_ROOT}/scripts/local_research/build_alpha_pack.py" \
  --pack-id "${PACK_ID}" \
  --tournament-dir "${TOURNAMENT_DIR}" \
  --output-root "${RESEARCH_ROOT}/ARTIFACTS/exports" \
  --import-intent "${IMPORT_INTENT}" \
  "${MC_ARG[@]}"

echo "ARTIFACT_EXPORT_OK pack_id=${PACK_ID}"
