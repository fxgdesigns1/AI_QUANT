#!/usr/bin/env bash
set -euo pipefail

echo "Starting FXG onboarding master script..."

# Step 1: Move old docs into FXG AI TRADING folder
if [[ -x "./cloud_move_old_docs.sh" ]]; then
  echo "Step 1: Moving old docs..."
  bash ./cloud_move_old_docs.sh
else
  echo "Warning: cloud_move_old_docs.sh not found or not executable"
fi

# Step 2: Bootstrap cloud (bucket, APIs, SA, creds, skeletons)
if [[ -x "./cloud_bootstrap_all.sh" ]]; then
  echo "Step 2: Running cloud bootstrap..."
  bash ./cloud_bootstrap_all.sh
else
  echo "Warning: cloud_bootstrap_all.sh not found or not executable"
fi

# Step 3: Final verification (basic connectivity)
echo "Step 3: Basic connectivity checks (post-boot)"
gsutil ls gs://ai-trading-configs || true
gcloud pubsub topics list || true

echo "FXG onboarding master script complete."


