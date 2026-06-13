#!/usr/bin/env bash
# Install git-filter-repo tool
#
# This script installs git-filter-repo via pip (user install or venv).
# It verifies the installation and reports the executable path.

set -euo pipefail

echo "📦 Installing git-filter-repo..."

# Check if already installed
if command -v git-filter-repo >/dev/null 2>&1; then
    EXEC_PATH=$(command -v git-filter-repo)
    echo "✅ git-filter-repo already installed at: $EXEC_PATH"
    echo ""
    echo "📋 Version info:"
    git-filter-repo --version 2>&1 || echo "   (version check not available)"
    exit 0
fi

# Detect if we're in a virtual environment
IN_VENV=0
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    IN_VENV=1
elif python3 -c 'import sys; exit(0 if sys.prefix != sys.base_prefix else 1)' 2>/dev/null; then
    IN_VENV=1
fi

# Try to install
INSTALL_METHOD=""
if command -v python3 >/dev/null 2>&1; then
    if [[ "$IN_VENV" = "1" ]]; then
        # In venv: install directly (no --user)
        echo "   Detected virtual environment, installing directly..."
        if python3 -m pip install git-filter-repo 2>&1; then
            INSTALL_METHOD="venv"
        fi
    else
        # Not in venv: try user install first (doesn't require sudo)
        echo "   Attempting user install (python3 -m pip install --user git-filter-repo)..."
        if python3 -m pip install --user git-filter-repo 2>&1; then
            INSTALL_METHOD="user"
        else
            # Try with --break-system-packages if needed (Python 3.11+)
            echo "   Retrying with --break-system-packages..."
            if python3 -m pip install --user --break-system-packages git-filter-repo 2>&1; then
                INSTALL_METHOD="user"
            fi
        fi
    fi
fi

# Verify installation
if command -v git-filter-repo >/dev/null 2>&1; then
    EXEC_PATH=$(command -v git-filter-repo)
    echo "✅ git-filter-repo installed successfully"
    echo "   Executable: $EXEC_PATH"
    echo ""
    echo "📋 Version info:"
    git-filter-repo --version 2>&1 || echo "   (version check not available)"
    exit 0
fi

# If still not found, check if it's in user's local bin
if [ -f "$HOME/.local/bin/git-filter-repo" ]; then
    echo "✅ git-filter-repo found at: $HOME/.local/bin/git-filter-repo"
    echo ""
    echo "⚠️  Note: $HOME/.local/bin may not be in PATH"
    echo "   Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "   Or use full path: $HOME/.local/bin/git-filter-repo"
    exit 0
fi

echo "❌ ERROR: git-filter-repo installation failed" >&2
echo "" >&2
echo "📋 Troubleshooting:" >&2
if [[ "$IN_VENV" = "1" ]]; then
    echo "   (Running in virtual environment)" >&2
    echo "   1. Try manual install: python3 -m pip install git-filter-repo" >&2
else
    echo "   1. Try manual install: python3 -m pip install --user git-filter-repo" >&2
fi
echo "   2. Or use system package manager: sudo apt install git-filter-repo" >&2
if command -v brew >/dev/null 2>&1; then
    echo "   3. Or install via Homebrew (macOS): brew install git-filter-repo" >&2
fi
exit 1
