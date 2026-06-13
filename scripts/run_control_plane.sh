#!/bin/bash
# Run Control Plane API Server

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Environment configuration (customize as needed)
export CONTROL_PLANE_HOST="${CONTROL_PLANE_HOST:-127.0.0.1}"
export CONTROL_PLANE_PORT="${CONTROL_PLANE_PORT:-8787}"
export RUNTIME_CONFIG_PATH="${RUNTIME_CONFIG_PATH:-runtime/config.yaml}"
export LOG_FILE_PATH="${LOG_FILE_PATH:-logs/ai_quant.log}"

# Token (REQUIRED in production)
if [ -z "$CONTROL_PLANE_TOKEN" ]; then
    echo "⚠️  Warning: CONTROL_PLANE_TOKEN not set"
    echo "   For production, set a secure token:"
    echo "   export CONTROL_PLANE_TOKEN=your-secure-token-here"
    echo ""
fi

# Ensure directories exist
mkdir -p runtime logs

# Check if config exists, if not copy example
if [ ! -f "$RUNTIME_CONFIG_PATH" ]; then
    echo "📝 Creating default runtime config from example..."
    cp runtime/config.example.yaml "$RUNTIME_CONFIG_PATH"
fi

# Check for dependencies
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI not installed"
    echo "   Install with: pip install fastapi uvicorn pydantic pyyaml"
    exit 1
fi

echo "🚀 Starting AI_QUANT Control Plane..."
echo "   Listening on: http://$CONTROL_PLANE_HOST:$CONTROL_PLANE_PORT"
echo "   Config: $RUNTIME_CONFIG_PATH"
echo "   Logs: $LOG_FILE_PATH"
echo ""

# Run the API server
python3 -m src.control_plane.api
