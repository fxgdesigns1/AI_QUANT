#!/usr/bin/env bash
# One-click bootstrap for WSL2 Ubuntu: deps, venv, research dirs (research-only; not an executor).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESEARCH_ROOT="${FXG_RESEARCH_ROOT:-${HOME}/fxg-research}"
VENV="${FXG_LOCAL_RESEARCH_VENV:-${RESEARCH_ROOT}/venv}"

echo "======================================================================"
echo "FXG local research stack install"
echo "REPO_ROOT=${REPO_ROOT}"
echo "RESEARCH_ROOT=${RESEARCH_ROOT}"
echo "VENV=${VENV}"
echo "======================================================================"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get not found — run this script inside WSL2 Ubuntu."
  exit 1
fi

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  APT_PREFIX=()
else
  APT_PREFIX=(sudo)
fi

"${APT_PREFIX[@]}" apt-get update -y
"${APT_PREFIX[@]}" apt-get install -y \
  python3 python3-venv python3-dev build-essential \
  git jq ripgrep curl unzip gzip pkg-config libssl-dev libffi-dev

mkdir -p "${RESEARCH_ROOT}/"{src,configs,runtime,ARTIFACTS/backtests,ARTIFACTS/monte_carlo,ARTIFACTS/exports,data/cache,data/datasets,scripts/local_research,docs/runbooks}

if [ ! -d "${VENV}" ]; then
  python3 -m venv "${VENV}"
fi
# shellcheck source=/dev/null
source "${VENV}/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "${REPO_ROOT}/requirements.txt"
python -m pip install scipy orjson matplotlib joblib

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
else
  echo "nvidia-smi not found (optional GPU check skipped)"
fi

ENV_EX="${REPO_ROOT}/.env.local_research.example"
ENV_OUT="${REPO_ROOT}/.env.local_research"
if [ ! -f "${ENV_OUT}" ] && [ -f "${ENV_EX}" ]; then
  cp "${ENV_EX}" "${ENV_OUT}"
  echo "Created ${ENV_OUT} from example — edit FXG_RESEARCH_ROOT if needed."
fi

echo ""
echo "LOCAL_RESEARCH_STACK_READY"
echo "Next: export FXG_RESEARCH_ROOT=${RESEARCH_ROOT}"
echo "Verify: bash ${REPO_ROOT}/scripts/local_research/verify_local_research_stack.sh"
