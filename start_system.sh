#!/bin/bash
# Start Trading System

cd "$(dirname "$0")/google-cloud-trading-system" || exit 1

echo "🚀 Starting Trading System..."
echo ""

# Ensure credentials are loaded
export OANDA_ENVIRONMENT=practice

# Start the system
python3 main.py
