#!/usr/bin/env bash
# Starts optional read-only research API (never starts trading runner).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESEARCH_ROOT="${FXG_RESEARCH_ROOT:-${HOME}/fxg-research}"
VENV="${FXG_LOCAL_RESEARCH_VENV:-${RESEARCH_ROOT}/venv}"
export FXG_RESEARCH_ROOT="${RESEARCH_ROOT}"
export PYTHONPATH="${REPO_ROOT}"

if [ ! -d "${VENV}" ]; then
  echo "venv not found — run install_local_research_stack.sh first"
  exit 1
fi
# shellcheck source=/dev/null
source "${VENV}/bin/activate"

ENABLED="${RESEARCH_API_ENABLED:-0}"
HOST="${RESEARCH_API_HOST:-127.0.0.1}"
PORT="${RESEARCH_API_PORT:-8790}"

if [ "${ENABLED}" != "1" ]; then
  echo "RESEARCH_API_DISABLED (set RESEARCH_API_ENABLED=1 to start uvicorn)"
  echo "research_root=${RESEARCH_ROOT}"
  echo "RESEARCH_PANEL_SKIPPED"
  exit 0
fi

cd "${REPO_ROOT}"
exec uvicorn src.research.research_api:app --host "${HOST}" --port "${PORT}"
