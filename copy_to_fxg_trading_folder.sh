#!/usr/bin/env bash
set -euo pipefail

DEST="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/FXG AI TRADING"
SRC_FILES=(
  "FXG_AI_TRADING_ONBOARDING.md"
  "FXG_ONBOARD_ALL.sh"
  "cloud_bootstrap_all.sh"
  "cloud_move_old_docs.sh"
)

echo "Copying onboarding & bootstrap files to FXG AI TRADING folder: ${DEST}"
mkdir -p "$DEST"

for f in "${SRC_FILES[@]}"; do
  if [ -f "$f" ]; then
    cp -v "$f" "$DEST/"
  else
    echo "Source not found: $f" >&2
  fi
done

INDEX_FILE="$DEST/index.txt"
ls -1 "$DEST" | sed 's/^/- /' > "$INDEX_FILE" 2>/dev/null || true
echo "Index created at $INDEX_FILE"


