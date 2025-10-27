#!/bin/bash
# Setup environment variables for trading system

export OANDA_API_KEY="REMOVED_SECRET"
export OANDA_ENVIRONMENT="practice"

echo "✅ Environment variables set:"
echo "   OANDA_API_KEY: ${OANDA_API_KEY:0:10}..."
echo "   OANDA_ENVIRONMENT: $OANDA_ENVIRONMENT"

