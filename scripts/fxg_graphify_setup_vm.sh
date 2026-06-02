#!/usr/bin/env bash
# Idempotent Graphify setup for Linux VMs (ALPHA /opt/ai-quant) and Git Bash on Windows
# when this repository is a full git checkout.
#
# Usage (on VM, as the repo owner user, e.g. aiquant):
#   cd /opt/ai-quant   # or your clone root
#   bash scripts/fxg_graphify_setup_vm.sh
#
# Optional: first-time graph build (can take many minutes on large trees):
#   FXG_GRAPHIFY_INITIAL_UPDATE=1 bash scripts/fxg_graphify_setup_vm.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== FXG Graphify VM setup ==="
echo "Repo: $ROOT"

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "[ERROR] python3/python not found. Install Python 3.10+ first." >&2
  exit 1
fi
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

VENV="$ROOT/.venv"
PIP=""
GRAPHIFY_CLI=""
if [ -x "$VENV/bin/pip" ]; then
  PIP="$VENV/bin/pip"
  GRAPHIFY_CLI="$VENV/bin/graphify"
elif [ -x "$VENV/Scripts/pip.exe" ]; then
  PIP="$VENV/Scripts/pip.exe"
  GRAPHIFY_CLI="$VENV/Scripts/graphify.exe"
elif [ -x "$VENV/Scripts/pip" ]; then
  PIP="$VENV/Scripts/pip"
  GRAPHIFY_CLI="$VENV/Scripts/graphify"
fi

if [ -n "$PIP" ]; then
  echo "--- Installing graphifyy into .venv ---"
  "$PIP" install -q -U pip wheel >/dev/null 2>&1 || true
  "$PIP" install -q graphifyy
  echo "[OK] graphifyy in .venv"
elif [ -d "$VENV" ]; then
  echo "[WARN] .venv exists but pip not found under bin/ or Scripts/; skip pip install"
else
  echo "[WARN] No .venv at $VENV — create venv and re-run, or: pip install --user graphifyy"
fi

echo "--- Installing git hooks (pre-commit + graphify post-commit/post-checkout) ---"
bash "$ROOT/scripts/install_git_hooks.sh"

if [ "${FXG_GRAPHIFY_INITIAL_UPDATE:-0}" = "1" ]; then
  if [ -n "$GRAPHIFY_CLI" ] && [ -x "$GRAPHIFY_CLI" ]; then
    echo "--- graphify update . (AST-only; may take several minutes) ---"
    "$GRAPHIFY_CLI" update .
  else
    echo "[WARN] FXG_GRAPHIFY_INITIAL_UPDATE=1 but venv graphify CLI missing (expected next to pip under .venv)"
  fi
else
  echo "[SKIP] Initial graph build (set FXG_GRAPHIFY_INITIAL_UPDATE=1 to run 'graphify update .')"
fi

echo "=== Done ==="
echo "Codex/claude/cursor IDE hooks live in committed files; on servers you usually only need:"
echo "  - graphify in PATH or .venv, and git hooks above."
echo "See: docs/runbooks/GRAPHIFY_ALPHA_AND_WINDOWS_VM.md"
