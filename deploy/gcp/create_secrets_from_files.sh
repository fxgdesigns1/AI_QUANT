#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"

# Usage:
#   export GCP_PROJECT_ID=...
#   ./deploy/gcp/create_secrets_from_files.sh \
#     --oanda-api-key /path/to/oanda_api_key.txt \
#     --oanda-account-id /path/to/oanda_account_id.txt \
#     --newsapi /path/to/newsapi_key.txt \
#     --alphavantage /path/to/alphavantage_key.txt \
#     --telegram-bot-token /path/to/telegram_bot_token.txt \
#     --telegram-chat-id /path/to/telegram_chat_id.txt
#
# This avoids pasting secrets directly into shell history.

OANDA_API_KEY_FILE=""
OANDA_ACCOUNT_ID_FILE=""
NEWSAPI_FILE=""
ALPHAVANTAGE_FILE=""
TELEGRAM_BOT_TOKEN_FILE=""
TELEGRAM_CHAT_ID_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --oanda-api-key) OANDA_API_KEY_FILE="$2"; shift 2;;
    --oanda-account-id) OANDA_ACCOUNT_ID_FILE="$2"; shift 2;;
    --newsapi) NEWSAPI_FILE="$2"; shift 2;;
    --alphavantage) ALPHAVANTAGE_FILE="$2"; shift 2;;
    --telegram-bot-token) TELEGRAM_BOT_TOKEN_FILE="$2"; shift 2;;
    --telegram-chat-id) TELEGRAM_CHAT_ID_FILE="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

must_file() {
  local p="$1"; local label="$2"
  [[ -n "$p" ]] || { echo "✗ Missing $label file" >&2; exit 2; }
  [[ -f "$p" ]] || { echo "✗ File not found for $label: $p" >&2; exit 2; }
}

must_file "$OANDA_API_KEY_FILE" "--oanda-api-key"
must_file "$OANDA_ACCOUNT_ID_FILE" "--oanda-account-id"
must_file "$NEWSAPI_FILE" "--newsapi"
must_file "$ALPHAVANTAGE_FILE" "--alphavantage"
must_file "$TELEGRAM_BOT_TOKEN_FILE" "--telegram-bot-token"
must_file "$TELEGRAM_CHAT_ID_FILE" "--telegram-chat-id"

create_or_update() {
  local secret_name="$1"; local file_path="$2"
  if gcloud secrets describe "$secret_name" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets versions add "$secret_name" --project "$GCP_PROJECT_ID" --data-file="$file_path" >/dev/null
    echo "✓ updated $secret_name" >&2
  else
    gcloud secrets create "$secret_name" --project "$GCP_PROJECT_ID" --replication-policy="automatic" >/dev/null
    gcloud secrets versions add "$secret_name" --project "$GCP_PROJECT_ID" --data-file="$file_path" >/dev/null
    echo "✓ created $secret_name" >&2
  fi
}

create_or_update ai-quant-oanda-api-key "$OANDA_API_KEY_FILE"
create_or_update ai-quant-oanda-account-id "$OANDA_ACCOUNT_ID_FILE"
create_or_update ai-quant-newsapi-api-key "$NEWSAPI_FILE"
create_or_update ai-quant-alphavantage-api-key "$ALPHAVANTAGE_FILE"
create_or_update ai-quant-telegram-bot-token "$TELEGRAM_BOT_TOKEN_FILE"
create_or_update ai-quant-telegram-chat-id "$TELEGRAM_CHAT_ID_FILE"

echo "✅ Secrets loaded to Secret Manager (values not printed)." >&2
