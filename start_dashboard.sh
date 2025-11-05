#!/bin/bash
# Start dashboard with proper environment

export OANDA_API_KEY="REMOVED_SECRET"
export OANDA_ACCOUNT_ID="101-004-30719775-008"
export OANDA_ENVIRONMENT="practice"
export TELEGRAM_TOKEN="7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs"
export TELEGRAM_CHAT_ID="6100678501"
export PYTHONPATH="/workspace"

cd /workspace
python3 dashboard/advanced_dashboard.py > /tmp/dashboard.log 2>&1 &

echo "Dashboard starting on port 8080..."
echo "Check logs: tail -f /tmp/dashboard.log"
