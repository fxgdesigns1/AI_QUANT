#!/bin/bash
# Setup environment variables for trading system

export OANDA_API_KEY="a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
export OANDA_ENVIRONMENT="practice"

echo "✅ Environment variables set:"
echo "   OANDA_API_KEY: ${OANDA_API_KEY:0:10}..."
echo "   OANDA_ENVIRONMENT: $OANDA_ENVIRONMENT"

