#!/usr/bin/env bash
set -euo pipefail

LOG="${HOME}/onboarding_run.log"
exec > >(tee -a "$LOG") 2>&1

echo "FXG Run All onboarding started: $(date)"

# Step 0: Validate required scripts exist
for script in cloud_move_old_docs.sh copy_to_fxg_trading_folder.sh FXG_ONBOARD_ALL.sh; do
  if [[ ! -f "$script" ]]; then
    echo "Missing required script: $script" >&2
    exit 1
  fi
done

# Step 1: Move old docs
echo "Step 1: Moving old docs..."
bash ./cloud_move_old_docs.sh || { echo "Step 1 failed"; exit 1; }

# Step 2: Copy onboarding/bootstrap files
echo "Step 2: Copy onboarding/bootstrap files..."
bash ./copy_to_fxg_trading_folder.sh || { echo "Step 2 failed"; exit 1; }

# Step 3: Run full onboarding (move + bootstrap + verify)
echo "Step 3: Running full onboarding..."
bash ./FXG_ONBOARD_ALL.sh || { echo "Step 3 failed"; exit 1; }

# Step 4: Final verification
echo "Step 4: Verifying results..."
TARGET_FOLDER="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/FXG AI TRADING"
ls -la "$TARGET_FOLDER" || true
INDEX_FILE="$TARGET_FOLDER/index.txt"
if [[ -f "$INDEX_FILE" ]]; then
  head -n 50 "$INDEX_FILE"
fi

echo "FXG Run All onboarding finished: $(date)"



