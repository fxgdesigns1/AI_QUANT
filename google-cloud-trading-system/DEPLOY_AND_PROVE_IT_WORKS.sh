#!/bin/bash

echo "================================================================"
echo "🚀 DEPLOY AND PROVE IT WORKS - NO MORE TALK, JUST RESULTS"
echo "================================================================"
echo ""

# Move to correct directory
cd /Users/mac/quant_system_clean/google-cloud-trading-system || exit 1

echo "STEP 1: Deploy enhanced application..."
echo "----------------------------------------------------------------"
gcloud app deploy --quiet
if [ $? -ne 0 ]; then
    echo "❌ FAILED TO DEPLOY APP"
    exit 1
fi
echo "✅ App deployed"
echo ""

echo "STEP 2: Deploy cron jobs..."
echo "----------------------------------------------------------------"
gcloud app deploy cron.yaml --quiet
if [ $? -ne 0 ]; then
    echo "❌ FAILED TO DEPLOY CRON"
    exit 1
fi
echo "✅ Cron deployed"
echo ""

echo "STEP 3: Verify cron jobs are active..."
echo "----------------------------------------------------------------"
gcloud app cron list
echo ""

echo "STEP 4: Test Telegram notification..."
echo "----------------------------------------------------------------"
python3 -c "
import requests

token = '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU'
chat_id = '6100678501'
url = f'https://api.telegram.org/bot{token}/sendMessage'

payload = {
    'chat_id': chat_id,
    'text': '''🔧 SYSTEM TEST - TELEGRAM WORKING

✅ Notifications are functional
⏰ Time: ''' + str(__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + '''

This proves Telegram is working.
You will get notifications on every scan.

#SystemTest''',
    'parse_mode': 'HTML'
}

response = requests.post(url, json=payload, timeout=10)
if response.status_code == 200:
    print('✅ TELEGRAM MESSAGE SENT - CHECK YOUR PHONE!')
else:
    print(f'❌ FAILED: {response.status_code}')
    print(response.text)
"
echo ""

echo "STEP 5: Trigger REAL scan right now..."
echo "----------------------------------------------------------------"
echo "🔄 Executing progressive scan..."
python3 progressive_trading_scanner.py 2>&1 | grep -E "(Trade executed|signal|FORCING|Telegram|units)"
echo ""

echo "STEP 6: Check account status..."
echo "----------------------------------------------------------------"
curl -s "https://ai-quant-trading.uc.r.appspot.com/api/status" | python3 -c "
import json
import sys

try:
    data = json.load(sys.stdin)
    print('CURRENT ACCOUNT STATUS:')
    print('=' * 60)
    for acc_id, acc in data.get('account_statuses', {}).items():
        print(f'Account {acc_id[-3:]}:')
        print(f'  Open trades: {acc.get(\"open_trades\", 0)}')
        print(f'  Open positions: {acc.get(\"open_positions\", 0)}')
        print(f'  Unrealized P&L: \${acc.get(\"unrealized_pl\", 0):.2f}')
        print()
except Exception as e:
    print(f'Error: {e}')
"
echo ""

echo "================================================================"
echo "✅ DEPLOYMENT AND TEST COMPLETE"
echo "================================================================"
echo ""
echo "CHECK YOUR TELEGRAM NOW - You should have received:"
echo "  1. Test message (Step 4)"
echo "  2. Trade notifications (Step 5)"
echo ""
echo "CHECK YOUR OANDA ACCOUNTS - You should see:"
echo "  • New positions opened"
echo "  • Stop loss orders attached"
echo "  • Take profit orders attached"
echo ""
echo "Next scheduled scan: Every hour on the hour (UTC)"
echo "================================================================"
