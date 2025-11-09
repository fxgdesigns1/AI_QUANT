#!/bin/bash
# Upload all credentials to Google Cloud Secret Manager
# Run this script to securely store all credentials

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "🔐 UPLOADING CREDENTIALS TO GOOGLE CLOUD SECRET MANAGER"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install from:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "Enter your Google Cloud Project ID:"
    read -r PROJECT_ID
    export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
else
    PROJECT_ID=$GOOGLE_CLOUD_PROJECT
    echo "Using project: $PROJECT_ID"
fi

echo ""
echo "Authenticating..."
gcloud auth application-default login --quiet || true

echo ""
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID --quiet

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Creating/Updating Secrets..."
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    # Check if secret exists
    if gcloud secrets describe "$secret_name" --project=$PROJECT_ID &>/dev/null; then
        echo "Updating: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
            --project=$PROJECT_ID \
            --data-file=-
    else
        echo "Creating: $secret_name"
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --project=$PROJECT_ID \
            --replication-policy="automatic" \
            --data-file=-
    fi
}

# OANDA Credentials
create_or_update_secret "oanda-api-key" "${OANDA_API_KEY}"
create_or_update_secret "oanda-environment" "practice"
create_or_update_secret "oanda-primary-account" "101-004-30719775-008"
create_or_update_secret "oanda-gold-scalp-account" "101-004-30719775-007"
create_or_update_secret "oanda-strategy-alpha-account" "101-004-30719775-006"

# Telegram
create_or_update_secret "telegram-bot-token" "${TELEGRAM_TOKEN}"
create_or_update_secret "telegram-chat-id" "${TELEGRAM_CHAT_ID}"

# News APIs
create_or_update_secret "alpha-vantage-api-key" "${ALPHA_VANTAGE_API_KEY}"
create_or_update_secret "marketaux-api-key" "${MARKETAUX_API_KEY}"

# Flask
create_or_update_secret "flask-secret-key" "your-secret-key-here"

# Complete JSON (backup)
cat ALL_CREDENTIALS_FOR_SECRET_MANAGER.json | \
    gcloud secrets create "trading-system-all-credentials" \
    --project=$PROJECT_ID \
    --replication-policy="automatic" \
    --data-file=- 2>/dev/null || \
cat ALL_CREDENTIALS_FOR_SECRET_MANAGER.json | \
    gcloud secrets versions add "trading-system-all-credentials" \
    --project=$PROJECT_ID \
    --data-file=-

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ UPLOAD COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Secrets created/updated:"
echo "  • oanda-api-key"
echo "  • oanda-environment"
echo "  • oanda-primary-account"
echo "  • oanda-gold-scalp-account"
echo "  • oanda-strategy-alpha-account"
echo "  • telegram-bot-token"
echo "  • telegram-chat-id"
echo "  • alpha-vantage-api-key"
echo "  • marketaux-api-key"
echo "  • flask-secret-key"
echo "  • trading-system-all-credentials (complete JSON)"
echo ""
echo "View your secrets:"
echo "  gcloud secrets list --project=$PROJECT_ID"
echo ""
echo "Access a secret:"
echo "  gcloud secrets versions access latest --secret=oanda-api-key --project=$PROJECT_ID"
echo ""
echo "Web console:"
echo "  https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "🔒 SECURITY REMINDER"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  DELETE local credential files now:"
echo "   rm ALL_CREDENTIALS_FOR_SECRET_MANAGER.json"
echo "   rm ALL_CREDENTIALS_READABLE.txt"
echo ""
echo "✅ Your credentials are now safely stored in Google Cloud"
echo "✅ Access from anywhere with proper authentication"
echo "✅ Use the secret_manager.py we created earlier to retrieve them"
echo ""


