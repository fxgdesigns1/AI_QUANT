#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESEARCH_ROOT="${FXG_RESEARCH_ROOT:-${HOME}/fxg-research}"
VENV="${FXG_LOCAL_RESEARCH_VENV:-${RESEARCH_ROOT}/venv}"
CONTRACT="${REPO_ROOT}/configs/local_research/export_contract.json"

echo "=== verify_local_research_stack ==="

if [ ! -d "${VENV}" ]; then
  echo "FAIL: venv missing at ${VENV}"
  exit 1
fi
# shellcheck source=/dev/null
source "${VENV}/bin/activate"

python - <<'PY' || exit 1
import importlib
for m in ("yaml", "fastapi", "uvicorn", "numpy", "pandas", "scipy"):
    importlib.import_module(m)
print("PYTHON_IMPORTS_OK")
PY

jq empty "${CONTRACT}"

mkdir -p "${RESEARCH_ROOT}/ARTIFACTS/exports"
python "${REPO_ROOT}/scripts/local_research/build_alpha_pack.py" --help >/dev/null

echo "ARTIFACT_EXPORT_OK"
echo "LOCAL_RESEARCH_STACK_READY"
