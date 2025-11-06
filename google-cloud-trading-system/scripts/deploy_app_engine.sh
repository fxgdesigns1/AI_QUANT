#!/bin/bash
set -euo pipefail

# One-command deploy with validation
# Usage: ./scripts/deploy_app_engine.sh

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"/.. && pwd)
cd "$ROOT_DIR"

# 1) Validate config
python3 scripts/predeploy_validate.py

# 2) Deploy to App Engine (requires gcloud auth and project configured)
if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ gcloud not found. Install Google Cloud SDK."
  exit 3
fi

APP_YAML="app.yaml"
if [ ! -f "$APP_YAML" ]; then
  echo "❌ $APP_YAML not found in $(pwd)"
  exit 4
fi

echo "🚀 Deploying to App Engine..."
gcloud app deploy "$APP_YAML" --quiet

echo "✅ Deployment triggered. Tail logs with:"
echo "gcloud app logs tail -s default"
