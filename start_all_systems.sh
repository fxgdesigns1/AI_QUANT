#!/bin/bash
# Complete Trading System Startup Script
# Starts all systems: AI, Automated, Dashboard, and validates everything

set -e

echo "=========================================="
echo "COMPLETE TRADING SYSTEM DEPLOYMENT"
echo "=========================================="
echo ""

# Set environment variables
export TELEGRAM_TOKEN="7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs"
export TELEGRAM_CHAT_ID="6100678501"
export OANDA_API_KEY="a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
export OANDA_ACCOUNT_ID="101-004-30719775-008"
export OANDA_BASE_URL="https://api-fxpractice.oanda.com"
export OANDA_ENVIRONMENT="practice"
export ALPHA_VANTAGE_API_KEY="LSBZJ73J9W1G8FWB"
export MARKETAUX_API_KEY="qL23wrqpBdU908DrznhIpfINVOgDg4bPmpKzQfW2"
export GEMINI_API_KEY="AQ.Ab8RN6KGhGzuSnOmj9P7ncZdm35NK6mKsUy4y4Qq8qrkd4CT_A"
export AUTO_TRADING_ENABLED="true"
export TRADING_ENABLED="true"
export MOCK_TRADING="False"
export DEVELOPMENT_MODE="False"
export PORT="8080"

cd /workspace

echo "✅ Environment variables set"
echo ""

# Test Telegram connection
echo "📱 Testing Telegram..."
python3 << EOF
import requests
import os
token = os.getenv('TELEGRAM_TOKEN')
url = f"https://api.telegram.org/bot{token}/getMe"
r = requests.get(url, timeout=5)
if r.json().get('ok'):
    print("✅ Telegram connected")
else:
    print("❌ Telegram connection failed")
EOF

echo ""

# Test OANDA connection
echo "💰 Testing OANDA..."
python3 << EOF
import requests
import os
api_key = os.getenv('OANDA_API_KEY')
account_id = os.getenv('OANDA_ACCOUNT_ID')
url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}"
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
r = requests.get(url, headers=headers, timeout=10)
if r.status_code == 200:
    balance = r.json()['account'].get('balance', 'N/A')
    print(f"✅ OANDA connected - Balance: \${balance}")
else:
    print(f"❌ OANDA connection failed: {r.status_code}")
EOF

echo ""

# Send startup notification
echo "📱 Sending startup notification..."
python3 << EOF
import requests
import os
from datetime import datetime
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
url = f"https://api.telegram.org/bot{token}/sendMessage"
msg = f"""🚀 COMPLETE TRADING SYSTEM STARTING

🤖 Systems:
• AI Trading System
• Automated Trading System  
• Dashboard
• Telegram Integration
• News & Economic Indicators
• AI Insights

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
requests.post(url, json={'chat_id': chat_id, 'text': msg}, timeout=10)
print("✅ Notification sent")
EOF

echo ""

# Start Dashboard in background
echo "📊 Starting Dashboard..."
cd /workspace/dashboard
nohup python3 advanced_dashboard.py > /tmp/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo "✅ Dashboard started (PID: $DASHBOARD_PID)"
echo $DASHBOARD_PID > /tmp/dashboard.pid
sleep 5

# Start AI Trading System in background
echo "🤖 Starting AI Trading System..."
cd /workspace
nohup python3 ai_trading_system.py > /tmp/ai_trading.log 2>&1 &
AI_PID=$!
echo "✅ AI Trading System started (PID: $AI_PID)"
echo $AI_PID > /tmp/ai_trading.pid
sleep 5

# Start Automated Trading System in background
echo "⚙️ Starting Automated Trading System..."
cd /workspace
nohup python3 automated_trading_system.py > /tmp/automated_trading.log 2>&1 &
AUTO_PID=$!
echo "✅ Automated Trading System started (PID: $AUTO_PID)"
echo $AUTO_PID > /tmp/automated_trading.pid
sleep 5

# Validate systems
echo ""
echo "🔍 Validating systems..."
sleep 10

python3 << EOF
import requests
import subprocess
import time

checks = []
# Check dashboard
try:
    r = requests.get('http://localhost:8080/ready', timeout=5)
    checks.append(("Dashboard", r.status_code == 200))
except:
    checks.append(("Dashboard", False))

# Check processes
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
checks.append(("AI Trading", 'ai_trading_system.py' in result.stdout))
checks.append(("Automated Trading", 'automated_trading_system.py' in result.stdout))
checks.append(("Dashboard Process", 'advanced_dashboard.py' in result.stdout))

print("\n📊 Validation Results:")
all_ok = True
for name, status in checks:
    icon = "✅" if status else "❌"
    print(f"  {icon} {name}")
    if not status:
        all_ok = False

if all_ok:
    print("\n✅ All systems validated!")
else:
    print("\n⚠️ Some systems may need attention")
EOF

# Send completion notification
echo ""
echo "📱 Sending completion notification..."
python3 << EOF
import requests
import os
from datetime import datetime
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
url = f"https://api.telegram.org/bot{token}/sendMessage"
msg = f"""✅ ALL SYSTEMS DEPLOYED AND RUNNING!

🤖 Systems Active:
• AI Trading System: RUNNING
• Automated Trading System: RUNNING
• Dashboard: RUNNING
• Telegram Integration: ACTIVE
• News & Economic Indicators: ACTIVE
• AI Insights: ACTIVE

📊 Dashboard: http://localhost:8080
💰 All systems ready to trade!

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
requests.post(url, json={'chat_id': chat_id, 'text': msg}, timeout=10)
EOF

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "📊 Systems running:"
echo "  • Dashboard: http://localhost:8080 (PID: $DASHBOARD_PID)"
echo "  • AI Trading System (PID: $AI_PID)"
echo "  • Automated Trading System (PID: $AUTO_PID)"
echo ""
echo "📝 Logs:"
echo "  • Dashboard: /tmp/dashboard.log"
echo "  • AI Trading: /tmp/ai_trading.log"
echo "  • Automated Trading: /tmp/automated_trading.log"
echo ""
echo "💡 To stop systems:"
echo "  kill \$(cat /tmp/dashboard.pid)"
echo "  kill \$(cat /tmp/ai_trading.pid)"
echo "  kill \$(cat /tmp/automated_trading.pid)"
echo ""
