#!/bin/bash
# Setup environment variables for trading system
# This script should source from .env file or require manual setting
# DO NOT hardcode secrets here

if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo "✅ Environment variables loaded from .env file"
else
    echo "⚠️  WARNING: .env file not found"
    echo "   Please set environment variables manually:"
    echo "   export OANDA_API_KEY='your_key'"
    echo "   export OANDA_ENV='practice'"
    echo "   export TELEGRAM_BOT_TOKEN='your_token'"
    echo "   export TELEGRAM_CHAT_ID='your_chat_id'"
fi

if [ -z "$OANDA_API_KEY" ]; then
    echo "❌ ERROR: OANDA_API_KEY not set"
    exit 1
fi

echo "✅ Environment variables verified:"
echo "   OANDA_API_KEY: ${OANDA_API_KEY:0:10}..."
echo "   OANDA_ENV: ${OANDA_ENV:-practice}"


