#!/usr/bin/env python3
import requests

TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
CHAT_ID = "6100678501"

message = """TRADE ENTRY NOTIFICATIONS - ACTIVE!

YES - YOU'LL GET NOTIFIED IMMEDIATELY!

When any account executes a confirmed signal:

INSTANT ALERT:

SNIPER ENTRY EXECUTED!

Account: Gold Scalping (009)
Instrument: XAU_USD
Direction: BUY
Entry: 3,982.50
Confidence: 87.3%
Signal: 85%+ (Gold DNA quality)

Stops/Targets:
  SL: 3,976.50 (6 pips)
  Target 1: +15 pips (30% partial)
  Target 2: +30 pips (30% partial)
  Target 3: +50 pips (20% partial)

Time: 2:47 PM London

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THEN YOU'LL GET:

+15 pips: PARTIAL 1 secured! ($450)
+30 pips: PARTIAL 2 secured! ($900)
+50 pips: PARTIAL 3 secured! ($1,000)
>$1,000: BIG WIN secured! (70%)
Trail: Updates when major moves
Exit: Final result

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOU'LL GET NOTIFICATIONS FOR:

✅ Signal confirmed (85%+ quality)
✅ Trade executed (entry price)
✅ Breakeven set (+10 pips)
✅ Each partial taken (Layers 2, 3, 4)
✅ Big win protection (>$1,000)
✅ Trailing updates (big moves)
✅ Trade exit (final P&L)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHEN TO EXPECT THEM:

Morning (9 AM-2 PM): 1-3 signals
PRIME TIME (2-5 PM): 3-8 signals!
Evening (5-9 PM): 1-3 signals

Peak activity: 2-5 PM London

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURED:

Token: Active
Chat ID: 6100678501
Trade alerts: ENABLED
Partial alerts: ENABLED
Real-time: YES

You'll know IMMEDIATELY when:
• 85%+ signal confirmed
• Trade entered
• Profits secured
• Big wins protected

No delay - instant notifications!
"""

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
response = requests.post(url, data={'chat_id': CHAT_ID, 'text': message}, timeout=10)

if response.status_code == 200:
    print("✅ Trade notification info sent to Telegram!")
else:
    print(f"❌ Failed: {response.status_code}")


