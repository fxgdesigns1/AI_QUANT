#!/usr/bin/env bash
set -euo pipefail

# FXG onboarding bootstrap script

PROJECT_ID="${PROJECT_ID:-fxg-ai-trading}"
BUCKET_PATH="${BUCKET_PATH:-gs://ai-trading-configs}"
REGION="${REGION:-us-central1}"

# Local skeleton paths (update if different)
PLANNED_DEPLOYMENT_PATH="${PLANNED_DEPLOYMENT_PATH:-/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/cloud_declutter_v2/planned_deployment}"
REPORT_TEMPLATES_PATH="${REPORT_TEMPLATES_PATH:-/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/cloud_declutter_v2/report_templates}"

SA="cursor-trading@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== FXG Onboarding Bootstrap: ${PROJECT_ID} ==="

# 1) Create bucket if missing
if gsutil ls "$BUCKET_PATH" >/dev/null 2>&1; then
  echo "Bucket exists: $BUCKET_PATH"
else
  gsutil mb -l "$REGION" "$BUCKET_PATH"
fi

# 2) Upload skeletons (idempotent)
gsutil -m cp -r "$PLANNED_DEPLOYMENT_PATH" "$BUCKET_PATH/cloud_declutter_v2/planned_deployment/"
gsutil -m cp -r "$REPORT_TEMPLATES_PATH" "$BUCKET_PATH/cloud_declutter_v2/report_templates/"

# 3) Enable APIs
gcloud config set project "$PROJECT_ID"
APIS=(compute.googleapis.com storage.googleapis.com firestore.googleapis.com secretmanager.googleapis.com pubsub.googleapis.com run.googleapis.com redis.googleapis.com logging.googleapis.com monitoring.googleapis.com iam.googleapis.com)
for api in "${APIS[@]}"; do
  if gcloud services list --enabled | grep -q "$api"; then
    echo "API already enabled: $api"
  else
    echo "Enabling $api"
    gcloud services enable "$api"
  fi
done

# 4) Create Cursor service account and bind roles
if gcloud iam service-accounts list | grep -q "$SA"; then
  echo "Service account exists: $SA"
else
  gcloud iam service-accounts create cursor-trading --display-name "Cursor Trading Service Account"
fi

gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role="roles/storage.admin" || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role="roles/datastore.user" || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role="roles/pubsub.publisher" || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role="roles/run.admin" || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor" || true

# 5) Non-interactive credentials
mkdir -p "$HOME/credentials"
KEY_PATH="$HOME/credentials/cursor-trading-key.json"
if [ -f "$KEY_PATH" ]; then
  echo "Credentials exist at $KEY_PATH"
else
  gcloud iam service-accounts keys create "$KEY_PATH" --iam-account "$SA" >/dev/null 2>&1
  echo "Created credentials at $KEY_PATH"
fi
export GOOGLE_APPLICATION_CREDENTIALS="$KEY_PATH"

# 6) Connectivity checks
echo "Connectivity checks..."
gsutil ls "$BUCKET_PATH" >/dev/null 2>&1 && echo "Cloud Storage OK" || echo "Cloud Storage NOT OK"
gcloud pubsub topics list >/dev/null 2>&1 && echo "Pub/Sub OK" || echo "Pub/Sub may be empty"

echo "Bootstrap complete. Review and run any follow-up steps as needed."

# 7) Copy relevant old docs into FXG AI TRADING onboarding folder (if present)
OLD_DOCS_ROOT="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
DEST_ONBOARDING_ROOT="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/FXG AI TRADING"

mkdir -p "$DEST_ONBOARDING_ROOT"

docs_to_copy=(
  COMPLETE_STRATEGY_OVERVIEW.md
  COMPLETE_SYSTEM_BREAKDOWN.md
  DEPLOYMENT_SUMMARY.md
  DEPLOYMENT_VERIFICATION_FINAL.md
  DEPLOYMENT_VERIFICATION_INTELLIGENT_CACHING.md
  STRATEGY_CONFIG_GUIDE.md
  STRATEGY_STATUS_REPORT.md
  BRUTAL_VERIFICATION.md
  BRUTAL_FINAL_VERIFICATION.md
  BRIEFINGS_DASHBOARD_INTEGRATION.md
)

for f in "${docs_to_copy[@]}"; do
  src="$OLD_DOCS_ROOT/$f"
  if [ -f "$src" ]; then
    cp -v "$src" "$DEST_ONBOARDING_ROOT/"
  else
    echo "Warning: missing doc $src"
  fi
done

ls -1 "$DEST_ONBOARDING_ROOT" >/dev/null 2>&1 || true
echo "Indexing onboarding folder..."
ls -1 "$DEST_ONBOARDING_ROOT" | sed -e 's/^/ - /' > "$DEST_ONBOARDING_ROOT/index.txt" 2>/dev/null || true


