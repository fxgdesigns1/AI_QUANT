#!/usr/bin/env bash
set -euo pipefail

# Usage: ./dashboard/deploy_cloud_run.sh <project-id> <region>
# Requires: gcloud auth login && gcloud config set project <project-id>

PROJECT_ID=${1:?"Project ID required"}
REGION=${2:-us-central1}

DASH_SVC=ai-dashboard
SUGG_SVC=trade-suggestions

DASH_IMAGE=gcr.io/$PROJECT_ID/$DASH_SVC
SUGG_IMAGE=gcr.io/$PROJECT_ID/$SUGG_SVC

# Build images
gcloud builds submit --project "$PROJECT_ID" --tag "$DASH_IMAGE" . \
  --config <(cat <<'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build','-t','$DASH_IMAGE','-f','dashboard/Dockerfile','.']
images: ['$DASH_IMAGE']
EOF
)

gcloud builds submit --project "$PROJECT_ID" --tag "$SUGG_IMAGE" . \
  --config <(cat <<'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build','-t','$SUGG_IMAGE','-f','dashboard/Dockerfile.suggestions','.']
images: ['$SUGG_IMAGE']
EOF
)

# Deploy dashboard
gcloud run deploy "$DASH_SVC" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$DASH_IMAGE" \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 2 \
  --timeout 30s \
  --set-env-vars "FLASK_SECRET_KEY=${FLASK_SECRET_KEY:-change-me}" \
  --set-env-vars "OANDA_API_KEY=${OANDA_API_KEY:-}" \
  --set-env-vars "OANDA_ACCOUNT_ID=${OANDA_ACCOUNT_ID:-}" \
  --set-env-vars "OANDA_ENVIRONMENT=${OANDA_ENVIRONMENT:-practice}"

# Deploy trade suggestions API
gcloud run deploy "$SUGG_SVC" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$SUGG_IMAGE" \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 2 \
  --timeout 30s \
  --set-env-vars "FLASK_SECRET_KEY=${FLASK_SECRET_KEY:-change-me}" \
  --set-env-vars "OANDA_API_KEY=${OANDA_API_KEY:-}" \
  --set-env-vars "OANDA_ACCOUNT_ID=${OANDA_ACCOUNT_ID:-}" \
  --set-env-vars "OANDA_ENVIRONMENT=${OANDA_ENVIRONMENT:-practice}"

# Output service URLs
DASH_URL=$(gcloud run services describe "$DASH_SVC" --platform managed --region "$REGION" --format 'value(status.url)')
SUGG_URL=$(gcloud run services describe "$SUGG_SVC" --platform managed --region "$REGION" --format 'value(status.url)')

echo "Dashboard URL: $DASH_URL"
if [[ -n "$DASH_URL" ]]; then
  echo "Test: curl -s $DASH_URL/api/overview | jq ."
fi

echo "Trade Suggestions URL: $SUGG_URL"
if [[ -n "$SUGG_URL" ]]; then
  echo "Health: curl -s $SUGG_URL/health | jq ."
fi
