#!/usr/bin/env bash
set -euo pipefail

DEST_ROOT="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/FXG AI TRADING"
SOURCE_BASE1="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/cloud_declutter_v2/planned_deployment"
SOURCE_BASE2="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/cloud_declutter_v2/planned_deployment/report_templates"

mkdir -p "$DEST_ROOT"

echo "Moving old deployment skeletons into FXG AI TRADING folder..."
if [ -d "$SOURCE_BASE1" ]; then
  rsync -av --progress "$SOURCE_BASE1/" "$DEST_ROOT/planned_deployment/"
else
  echo "Source not found: $SOURCE_BASE1"
fi

if [ -d "$SOURCE_BASE2" ]; then
  rsync -av --progress "$SOURCE_BASE2/" "$DEST_ROOT/report_templates/"
else
  echo "Source not found: $SOURCE_BASE2"
fi

INDEX_FILE="$DEST_ROOT/index.txt"
ls -1 "$DEST_ROOT" | sed 's/^/- /' > "$INDEX_FILE"
echo "Index created at $INDEX_FILE"



