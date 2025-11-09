#!/usr/bin/env python3
import requests

TOKEN = "${TELEGRAM_TOKEN}"
CHAT_ID = "${TELEGRAM_CHAT_ID}"

message = """📊 PROFIT LAYERING SYSTEM

🎯 HOW MANY LAYERS? 5 LAYERS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LAYER 1: Breakeven (+10 pips)
  Action: Move stop to entry +3 pips
  Position: 100% running
  Purpose: Can't lose!

LAYER 2: First Partial (+15 pips)
  Action: Close 30%
  Position: 70% running
  Secured: $150-450
  Purpose: Lock in early

LAYER 3: Second Partial (+30 pips)
  Action: Close 30% more
  Position: 40% running  
  Secured: $300-900 more
  Purpose: Secure majority

LAYER 4: Third Partial (+50 pips)
  Action: Close 20% more
  Position: 20% running
  Secured: $500-1,000 more
  Purpose: Big wins locked

LAYER 5: Tight Trailing
  Action: Trail last 20% (8-12 pips)
  Position: Final 20%
  Purpose: Capture mega moves

BONUS: Big Win Alert (>$1,000)
  Action: Close 70% immediately!
  Purpose: Prevent +$9K → loss!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 100 PIP WINNER EXAMPLE:

+10 pips: Breakeven set ✅
+15 pips: 30% out = $450 ✅
+30 pips: 30% out = $900 ✅
+50 pips: 20% out = $1,000 ✅
+100 pips: Last 20% trails out = $1,760 ✅

TOTAL: $4,110 secured!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 WHY 5 LAYERS?

Not 2: Too aggressive, miss upside
Not 10: Over-complicated

5 = OPTIMAL:
  • Secures 80% early
  • Lets 20% capture mega
  • Simple to track
  • Proven effective

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ACTIVE on all accounts now!

Check tonight 9:30 PM to see which layers triggered today!
"""

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
response = requests.post(url, data={'chat_id': CHAT_ID, 'text': message}, timeout=10)

if response.status_code == 200:
    print("✅ Layering explanation sent to Telegram!")
else:
    print(f"❌ Failed: {response.status_code}")


