#!/usr/bin/env bash
# Setup Local Research Environment for 5950X
# Creates ~/fxg-ai-quant-local directory structure

set -euo pipefail

LOCAL_ROOT="${HOME}/fxg-ai-quant-local"
REPO_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "======================================================================"
echo "=== SETTING UP LOCAL FXG RESEARCH ENVIRONMENT ==="
echo "======================================================================"
echo "Local root: ${LOCAL_ROOT}"
echo "Repo source: ${REPO_SOURCE}"
echo ""

# Create directory structure
echo "Creating directory structure..."
mkdir -p "${LOCAL_ROOT}"/{repo,runtime,artifacts/{datasets,backtests,monte_carlo,candles},logs,exports,quarantine}

# Create symlink to repo (or copy if on different filesystem)
echo "Setting up repo link..."
if [ -d "${LOCAL_ROOT}/repo" ] && [ ! -L "${LOCAL_ROOT}/repo" ]; then
    echo "  repo/ already exists as directory"
else
    if [ "$(readlink -f "${REPO_SOURCE}")" = "$(readlink -f "${LOCAL_ROOT}/repo")" ]; then
        echo "  Repo already linked"
    else
        # Try symlink first
        if ln -sfn "${REPO_SOURCE}" "${LOCAL_ROOT}/repo" 2>/dev/null; then
            echo "  Created symlink: ${LOCAL_ROOT}/repo -> ${REPO_SOURCE}"
        else
            echo "  Symlink failed (cross-filesystem?), creating reference file instead"
            echo "${REPO_SOURCE}" > "${LOCAL_ROOT}/repo/.repo_source_path"
        fi
    fi
fi

# Create runtime config directory
mkdir -p "${LOCAL_ROOT}/runtime"
if [ ! -f "${LOCAL_ROOT}/runtime/config.yaml" ]; then
    if [ -f "${REPO_SOURCE}/runtime/config.yaml" ]; then
        cp "${REPO_SOURCE}/runtime/config.yaml" "${LOCAL_ROOT}/runtime/config.yaml"
        echo "  Copied runtime config"
    fi
fi

# Create .env.research.example
cat > "${LOCAL_ROOT}/.env.research.example" << 'EOF'
# FXG Research Environment Configuration
# Copy this to .env.research and customize

# Research Mode (no live OANDA required for cached backtests)
RESEARCH_MODE=true
USE_CACHED_CANDLES=true

# Local Paths (user-owned, no root permissions needed)
LOCAL_ARTIFACTS_ROOT=~/fxg-ai-quant-local/artifacts
LOCAL_RUNTIME_ROOT=~/fxg-ai-quant-local/runtime
LOCAL_LOGS_ROOT=~/fxg-ai-quant-local/logs

# Optional: OANDA credentials (only needed for live data fetching, not cached research)
# OANDA_API_KEY=
# OANDA_ACCOUNT_ID=
# OANDA_ENV=practice

# Monte Carlo Settings
MC_WORKERS=16
MC_DEFAULT_ITERATIONS=1000
MC_DEFAULT_SEED=42

# Python Environment
PYTHON_VENV=~/fxg-ai-quant-local/venv
EOF

echo ""
echo "✅ Local research environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.research.example to .env.research and customize"
echo "  2. Create Python venv: python3 -m venv ${LOCAL_ROOT}/venv"
echo "  3. Install dependencies: source ${LOCAL_ROOT}/venv/bin/activate && pip install -r ${LOCAL_ROOT}/repo/requirements.txt"
echo "  4. Sync artifacts from VM using scripts/sync_vm_artifacts.sh"
