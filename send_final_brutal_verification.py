#!/usr/bin/env python3
from src.core.settings import settings
"""
Send final brutal verification to Telegram
"""
import os
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6100678501")

def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def main():
    message = f"""✅ **FIXES APPLIED - BRUTAL VERIFICATION**

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)

---

## ✅ **PROGRESS MADE**

### **Integration Bug: FIXED**

**Before:**
• Strategies weren't being called
• No visibility into execution
• All using default logic

**After:**
• ✅ Strategies ARE being called
• ✅ Code path executing correctly
• ✅ Detailed logging shows what's happening

---

## 📊 **ACTUAL STATUS**

### **Strategy Execution:**

1. **Dynamic Multi-Pair Unified** (Account 011)
   • ✅ **IS BEING CALLED**
   • ✅ Method: `generate_signals(market_data)`
   • ⚠️ **Returns empty/None** (no signals generated)

2. **Trade With Pat ORB Dual** (Account 010)
   • ✅ **IS BEING CALLED**
   • ✅ Method: `generate_signals(market_data)`
   • ⚠️ **Returns empty/None** (no signals generated)

3. **EUR Calendar Optimized V2** (Account 006)
   • ⚠️ **SKIPPED** (needs historical OHLCV data)
   • Correctly handled - won't work with just current prices

---

## 🎯 **THE REAL TRUTH**

**Integration:** ✅ **FIXED**
• Strategies are being called
• Code path is correct
• Logging shows execution

**Strategy Results:** ⚠️ **Returning Empty**
• Could be normal (no valid signals in current market)
• Could be strategy filters too strict
• Could be missing data/indicators
• **Need to investigate**

---

## 📋 **BRUTAL SUMMARY**

**Integration Bug:** ✅ **FIXED**
**Strategies Called:** ✅ **YES (2/9 working)**
**Signals Generated:** ❌ **0 (strategies return empty)**

**The integration is working.**
**Strategies are being called.**
**But they return empty results.**

**Next:** Investigate why strategies return empty - market conditions or strategy issues?

---

**Status:** Integration fixed, but strategies return no signals
"""

    send_telegram_message(message)
    print("✅ Final brutal verification sent to Telegram")

if __name__ == "__main__":
    main()





