#!/bin/bash
# Cloudflare Zero Trust API Automation: IdP + Access Application + Policy
# Idempotent: checks before create; updates if exists; no duplicates
#
# Required env vars:
#   CLOUDFLARE_API_TOKEN (with Access + IdP + DNS permissions)
#   CLOUDFLARE_ACCOUNT_ID
#   CLOUDFLARE_ZONE_ID (zone must be Active)
#   DOMAIN (e.g., "example.com")
#   ALPHA_HOSTNAME (e.g., "alpha.example.com")
#   ALLOWED_GOOGLE_EMAILS_CSV (comma-separated, e.g., "user1@example.com,user2@example.com")
#   GOOGLE_OAUTH_CLIENT_ID
#   GOOGLE_OAUTH_CLIENT_SECRET

set -euo pipefail

# API base
API_BASE="https://api.cloudflare.com/client/v4"
HEADERS=(
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}"
    -H "Content-Type: application/json"
)

# Validate required env vars
REQUIRED_VARS=(
    "CLOUDFLARE_API_TOKEN"
    "CLOUDFLARE_ACCOUNT_ID"
    "CLOUDFLARE_ZONE_ID"
    "DOMAIN"
    "ALPHA_HOSTNAME"
    "ALLOWED_GOOGLE_EMAILS_CSV"
    "GOOGLE_OAUTH_CLIENT_ID"
    "GOOGLE_OAUTH_CLIENT_SECRET"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "❌ ERROR: Required env var '$var' is not set" >&2
        exit 1
    fi
done

echo "=== CLOUDFLARE ZERO TRUST AUTOMATION ==="
echo "Domain: $DOMAIN"
echo "Hostname: $ALPHA_HOSTNAME"
echo "Account ID: $CLOUDFLARE_ACCOUNT_ID"
echo "Zone ID: $CLOUDFLARE_ZONE_ID"
echo ""

# Helper: Make API request and parse JSON response
api_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    
    local cmd="curl -sSf"
    for h in "${HEADERS[@]}"; do
        cmd="$cmd $h"
    done
    
    case "$method" in
        GET)
            cmd="$cmd -X GET"
            ;;
        POST)
            cmd="$cmd -X POST -d '$data'"
            ;;
        PUT)
            cmd="$cmd -X PUT -d '$data'"
            ;;
        PATCH)
            cmd="$cmd -X PATCH -d '$data'"
            ;;
        DELETE)
            cmd="$cmd -X DELETE"
            ;;
    esac
    
    cmd="$cmd '$API_BASE$endpoint'"
    eval "$cmd"
}

# Helper: Check if API response is successful
check_api_success() {
    local response="$1"
    local success
    success=$(echo "$response" | jq -r '.success // false')
    if [[ "$success" != "true" ]]; then
        echo "$response" | jq -r '.errors[]? | "\(.code): \(.message)"' >&2
        return 1
    fi
}

# Step 1: Ensure Google IdP exists
echo "--- Step 1: Google Identity Provider ---"
IDP_NAME="Google"
IDP_LIST_RESPONSE=$(api_request GET "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/identity_providers")
check_api_success "$IDP_LIST_RESPONSE" || exit 1

EXISTING_IDP=$(echo "$IDP_LIST_RESPONSE" | jq -r ".result[] | select(.name == \"$IDP_NAME\" and .type == \"google\") | .id")

if [[ -n "$EXISTING_IDP" && "$EXISTING_IDP" != "null" ]]; then
    echo "✅ Google IdP exists (ID: $EXISTING_IDP), updating..."
    IDP_UPDATE_DATA=$(jq -n \
        --arg client_id "$GOOGLE_OAUTH_CLIENT_ID" \
        --arg client_secret "$GOOGLE_OAUTH_CLIENT_SECRET" \
        '{
            config: {
                client_id: $client_id,
                client_secret: $client_secret
            },
            name: "Google",
            type: "google"
        }')
    
    IDP_UPDATE_RESPONSE=$(api_request PUT "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/identity_providers/${EXISTING_IDP}" "$IDP_UPDATE_DATA")
    check_api_success "$IDP_UPDATE_RESPONSE" || exit 1
    IDP_ID="$EXISTING_IDP"
    echo "✅ Google IdP updated (ID: $IDP_ID)"
else
    echo "Creating Google IdP..."
    IDP_CREATE_DATA=$(jq -n \
        --arg client_id "$GOOGLE_OAUTH_CLIENT_ID" \
        --arg client_secret "$GOOGLE_OAUTH_CLIENT_SECRET" \
        '{
            config: {
                client_id: $client_id,
                client_secret: $client_secret
            },
            name: "Google",
            type: "google"
        }')
    
    IDP_CREATE_RESPONSE=$(api_request POST "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/identity_providers" "$IDP_CREATE_DATA")
    check_api_success "$IDP_CREATE_RESPONSE" || exit 1
    IDP_ID=$(echo "$IDP_CREATE_RESPONSE" | jq -r '.result.id')
    echo "✅ Google IdP created (ID: $IDP_ID)"
fi

# Get IdP UUID (needed for policy)
IDP_DETAIL_RESPONSE=$(api_request GET "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/identity_providers/${IDP_ID}")
check_api_success "$IDP_DETAIL_RESPONSE" || exit 1
IDP_UUID=$(echo "$IDP_DETAIL_RESPONSE" | jq -r '.result.uuid')

echo ""

# Step 2: Ensure Access Application exists
echo "--- Step 2: Access Application ---"
APP_NAME="Alpha Dashboard"
APP_DOMAIN="$ALPHA_HOSTNAME"

APP_LIST_RESPONSE=$(api_request GET "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps")
check_api_success "$APP_LIST_RESPONSE" || exit 1

EXISTING_APP=$(echo "$APP_LIST_RESPONSE" | jq -r ".result[] | select(.domain == \"$APP_DOMAIN\") | .id")

if [[ -n "$EXISTING_APP" && "$EXISTING_APP" != "null" ]]; then
    echo "✅ Access Application exists (ID: $EXISTING_APP) for $APP_DOMAIN"
    APP_ID="$EXISTING_APP"
else
    echo "Creating Access Application for $APP_DOMAIN..."
    APP_CREATE_DATA=$(jq -n \
        --arg name "$APP_NAME" \
        --arg domain "$APP_DOMAIN" \
        '{
            name: $name,
            domain: $domain,
            type: "self_hosted",
            session_duration: "24h"
        }')
    
    APP_CREATE_RESPONSE=$(api_request POST "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps" "$APP_CREATE_DATA")
    check_api_success "$APP_CREATE_RESPONSE" || exit 1
    APP_ID=$(echo "$APP_CREATE_RESPONSE" | jq -r '.result.id')
    echo "✅ Access Application created (ID: $APP_ID)"
fi

echo ""

# Step 3: Ensure Access Policy exists (email allowlist)
echo "--- Step 3: Access Policy ---"
POLICY_NAME="Allow Listed Emails"

# Parse CSV emails into JSON array using jq
IFS=',' read -ra EMAIL_ARRAY <<< "$ALLOWED_GOOGLE_EMAILS_CSV"
EMAIL_JSON_ARRAY=$(printf '%s\n' "${EMAIL_ARRAY[@]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | jq -R . | jq -s .)

POLICY_LIST_RESPONSE=$(api_request GET "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps/${APP_ID}/policies")
check_api_success "$POLICY_LIST_RESPONSE" || exit 1

EXISTING_POLICY=$(echo "$POLICY_LIST_RESPONSE" | jq -r ".result[] | select(.name == \"$POLICY_NAME\") | .id")

# Build policy include rule (email allowlist)
POLICY_INCLUDE_RULE=$(jq -n \
    --argjson emails "$EMAIL_JSON_ARRAY" \
    '{
        email: $emails
    }')

if [[ -n "$EXISTING_POLICY" && "$EXISTING_POLICY" != "null" ]]; then
    echo "✅ Access Policy exists (ID: $EXISTING_POLICY), updating..."
    POLICY_UPDATE_DATA=$(jq -n \
        --arg name "$POLICY_NAME" \
        --argjson include "$POLICY_INCLUDE_RULE" \
        '{
            name: $name,
            decision: "allow",
            include: [$include]
        }')
    
    POLICY_UPDATE_RESPONSE=$(api_request PUT "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps/${APP_ID}/policies/${EXISTING_POLICY}" "$POLICY_UPDATE_DATA")
    check_api_success "$POLICY_UPDATE_RESPONSE" || exit 1
    echo "✅ Access Policy updated (ID: $EXISTING_POLICY)"
else
    echo "Creating Access Policy..."
    POLICY_CREATE_DATA=$(jq -n \
        --arg name "$POLICY_NAME" \
        --argjson include "$POLICY_INCLUDE_RULE" \
        '{
            name: $name,
            decision: "allow",
            include: [$include]
        }')
    
    POLICY_CREATE_RESPONSE=$(api_request POST "/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps/${APP_ID}/policies" "$POLICY_CREATE_DATA")
    check_api_success "$POLICY_CREATE_RESPONSE" || exit 1
    POLICY_ID=$(echo "$POLICY_CREATE_RESPONSE" | jq -r '.result.id')
    echo "✅ Access Policy created (ID: $POLICY_ID)"
fi

echo ""

# Step 4: Optional DNS record (CNAME to tunnel)
echo "--- Step 4: DNS Record (Optional) ---"
DNS_NAME=$(echo "$ALPHA_HOSTNAME" | sed "s/\.$DOMAIN\$//")
if [[ -z "$DNS_NAME" ]]; then
    DNS_NAME="@"
fi

DNS_LIST_RESPONSE=$(api_request GET "/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=CNAME&name=${ALPHA_HOSTNAME}")
check_api_success "$DNS_LIST_RESPONSE" || exit 1

EXISTING_DNS=$(echo "$DNS_LIST_RESPONSE" | jq -r '.result[0].id // empty')

if [[ -n "$EXISTING_DNS" ]]; then
    echo "✅ DNS CNAME record exists (ID: $EXISTING_DNS) for $ALPHA_HOSTNAME"
    echo "   (If tunnel is active, verify target in Cloudflare Tunnel UI)"
else
    echo "⚠️  DNS CNAME record not found for $ALPHA_HOSTNAME"
    echo "   (Create manually in Cloudflare Tunnel UI or via API after tunnel is active)"
    echo "   Target should point to your tunnel's route (e.g., <tunnel-id>.cfargotunnel.com)"
fi

echo ""
echo "=== COMPLETE ==="
echo "✅ Google IdP: $IDP_ID"
echo "✅ Access Application: $APP_ID ($APP_DOMAIN)"
echo "✅ Access Policy: Allow emails: $ALLOWED_GOOGLE_EMAILS_CSV"
echo ""
echo "Next steps:"
echo "1. Create Cloudflare Tunnel in Zero Trust UI (name: ai-quant-alpha)"
echo "2. Get tunnel token and install on VM: sudo cloudflared service install <TOKEN>"
echo "3. Route $APP_DOMAIN -> http://127.0.0.1:8787 in Tunnel UI"
echo "4. Verify DNS record if not auto-created by tunnel"
echo "5. Test: https://$APP_DOMAIN (should show Google sign-in)"
