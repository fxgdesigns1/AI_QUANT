#!/bin/bash
# Upload ALL credentials to Google Cloud Secret Manager
# Includes OANDA, Telegram, News APIs, SSH info

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "🔐 UPLOADING ALL CREDENTIALS TO GOOGLE CLOUD SECRET MANAGER"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found${NC}"
    echo "Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "Enter your Google Cloud Project ID:"
    read -r PROJECT_ID
    export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
else
    PROJECT_ID=$GOOGLE_CLOUD_PROJECT
fi

echo -e "${GREEN}Using project: $PROJECT_ID${NC}"
echo ""

# Authenticate
echo "Authenticating with Google Cloud..."
gcloud auth application-default login --quiet

echo ""
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID --quiet

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Creating/Updating Secrets..."
echo "═══════════════════════════════════════════════════════════════"

# Helper function
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if gcloud secrets describe "$secret_name" --project=$PROJECT_ID &>/dev/null; then
        echo -e "${YELLOW}Updating${NC}: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
            --project=$PROJECT_ID \
            --data-file=- 2>&1 | grep -v "Created version"
    else
        echo -e "${GREEN}Creating${NC}: $secret_name"
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --project=$PROJECT_ID \
            --replication-policy="automatic" \
            --data-file=- 2>&1 | grep -v "Created version"
    fi
}

echo ""
echo "━━━ OANDA Trading ━━━"
create_or_update_secret "oanda-api-key" "${OANDA_API_KEY}"
create_or_update_secret "oanda-environment" "practice"
create_or_update_secret "oanda-primary-account" "101-004-30719775-001"
create_or_update_secret "oanda-gold-scalp-account" "101-004-30719775-002"
create_or_update_secret "oanda-strategy-alpha-account" "101-004-30719775-003"

echo ""
echo "━━━ Telegram ━━━"
create_or_update_secret "telegram-bot-token" "${TELEGRAM_TOKEN}"
create_or_update_secret "telegram-chat-id" "${TELEGRAM_CHAT_ID}"

echo ""
echo "━━━ SSH Access ━━━"
create_or_update_secret "ssh-host" "13.50.52.91"
create_or_update_secret "ssh-user" "ubuntu"
create_or_update_secret "ssh-key-path" "/Users/mac/Desktop/n8n-key.pem"
create_or_update_secret "ssh-connection-string" "ssh -i /Users/mac/Desktop/n8n-key.pem ubuntu@13.50.52.91"

# Read and upload SSH private key if exists
if [ -f "/Users/mac/Desktop/n8n-key.pem" ]; then
    echo -e "${GREEN}Uploading${NC}: ssh-private-key (from file)"
    cat "/Users/mac/Desktop/n8n-key.pem" | gcloud secrets create "ssh-private-key" \
        --project=$PROJECT_ID \
        --replication-policy="automatic" \
        --data-file=- 2>/dev/null || \
    cat "/Users/mac/Desktop/n8n-key.pem" | gcloud secrets versions add "ssh-private-key" \
        --project=$PROJECT_ID \
        --data-file=- 2>&1 | grep -v "Created version"
else
    echo -e "${YELLOW}⚠️  SSH key file not found at /Users/mac/Desktop/n8n-key.pem${NC}"
fi

echo ""
echo "━━━ Alpha Vantage (3 keys) ━━━"
create_or_update_secret "alpha-vantage-key-1" "${ALPHA_VANTAGE_API_KEY}"
create_or_update_secret "alpha-vantage-key-2" "LB36ODU7500OUAHP"
create_or_update_secret "alpha-vantage-key-3" "YXDNYDZ55K1248AR"

echo ""
echo "━━━ Marketaux (3 tokens) ━━━"
create_or_update_secret "marketaux-token-1" "${MARKETAUX_API_KEY}"
create_or_update_secret "marketaux-token-2" "39Ss2ny2bfHy2XNZLGRCof1011G3LT7gyRFC4Vct"
create_or_update_secret "marketaux-token-3" "MwHMtJge9xsol0Q2NKC731fZz2XIoM23220ukx6C"

echo ""
echo "━━━ Polygon.io (3 keys) ━━━"
create_or_update_secret "polygon-key-1" "eiRSVY6NjFnh5dG9iHkXzKBdLLp8C39q"
create_or_update_secret "polygon-key-2" "aU2fVci7svp3GXJA4PCyqtykSsa8V2iN"
create_or_update_secret "polygon-key-3" "RGEL1p4sDdghdpORGzglkmLWDK1cj2Eh"

echo ""
echo "━━━ FMP (2 keys) ━━━"
create_or_update_secret "fmp-key-1" "XaZrx5fB6UEM5xoSHPjPEO6crJ1zDe6J"
create_or_update_secret "fmp-key-2" "6sksRLjThlEZIILXuya2mxTtcqzQHrDv"

echo ""
echo "━━━ FRED (2 keys) ━━━"
create_or_update_secret "fred-key-1" "a9ef244d7466e388cde64cca30d225db"
create_or_update_secret "fred-key-2" "3910b5fb49b1519a75782b57cd749341"

echo ""
echo "━━━ Application ━━━"
create_or_update_secret "flask-secret-key" "your-secret-key-here"

echo ""
echo "━━━ Complete JSON Backup ━━━"
if [ -f "COMPLETE_CREDENTIALS_ALL.json" ]; then
    cat COMPLETE_CREDENTIALS_ALL.json | \
        gcloud secrets create "trading-system-complete-credentials" \
        --project=$PROJECT_ID \
        --replication-policy="automatic" \
        --data-file=- 2>/dev/null || \
    cat COMPLETE_CREDENTIALS_ALL.json | \
        gcloud secrets versions add "trading-system-complete-credentials" \
        --project=$PROJECT_ID \
        --data-file=- 2>&1 | grep -v "Created version"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ UPLOAD COMPLETE${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Secrets created/updated (28 total):"
echo ""
echo "OANDA (5 secrets):"
echo "  • oanda-api-key"
echo "  • oanda-environment"
echo "  • oanda-primary-account"
echo "  • oanda-gold-scalp-account"
echo "  • oanda-strategy-alpha-account"
echo ""
echo "Telegram (2 secrets):"
echo "  • telegram-bot-token"
echo "  • telegram-chat-id"
echo ""
echo "SSH Access (5 secrets):"
echo "  • ssh-host"
echo "  • ssh-user"
echo "  • ssh-key-path"
echo "  • ssh-connection-string"
echo "  • ssh-private-key"
echo ""
echo "News APIs (14 secrets):"
echo "  • alpha-vantage-key-1, key-2, key-3"
echo "  • marketaux-token-1, token-2, token-3"
echo "  • polygon-key-1, key-2, key-3"
echo "  • fmp-key-1, key-2"
echo "  • fred-key-1, key-2"
echo ""
echo "Application (1 secret):"
echo "  • flask-secret-key"
echo ""
echo "Backup (1 secret):"
echo "  • trading-system-complete-credentials (JSON)"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "📋 QUICK COMMANDS"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "List all secrets:"
echo "  gcloud secrets list --project=$PROJECT_ID"
echo ""
echo "View a secret:"
echo "  gcloud secrets versions access latest --secret=oanda-api-key --project=$PROJECT_ID"
echo ""
echo "Web console:"
echo "  https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${YELLOW}🔒 SECURITY - DELETE LOCAL FILES${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Now that secrets are uploaded, DELETE these files:"
echo ""
echo "  rm COMPLETE_CREDENTIALS_ALL.json"
echo "  rm COMPLETE_CREDENTIALS_READABLE.txt"
echo "  rm ALL_CREDENTIALS_FOR_SECRET_MANAGER.json"
echo "  rm ALL_CREDENTIALS_READABLE.txt"
echo ""
echo "Keep these files:"
echo "  • API_KEY_LOCATION.txt (reference)"
echo "  • UPLOAD_ALL_SECRETS.sh (this script)"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Your credentials are now secure in Google Cloud!${NC}"
echo "═══════════════════════════════════════════════════════════════"


