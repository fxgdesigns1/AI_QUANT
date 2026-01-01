#!/usr/bin/env python3
"""
Send brutal honest verification to Telegram
"""
import os
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
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
    message = f"""🔴 **BRUTAL HONEST VERIFICATION**

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)

---

## ❌ **THE HARSH REALITY**

### **Strategies Are NOT Working**

**Evidence:**
• **ZERO** success messages: `✅ Strategy 'X' generated N signals`
• Only 1 strategy even attempts to run (EUR Calendar)
• That 1 strategy fails immediately (signature mismatch)
• Other 2 "working" strategies show no evidence of being called

---

## 📊 **ACTUAL STATUS**

### **0 out of 9 strategies successfully using their own logic**

**Breakdown:**
• **6 strategies:** Can't load (missing `src.core.order_manager`)
• **1 strategy:** Tries to run but fails (EUR Calendar - signature issue)
• **2 strategies:** No evidence they're being called (Dynamic Multi-Pair, ORB)

---

## ✅ **WHAT'S WORKING**

• Code deployed ✅
• Service running ✅
• Strategies load ✅
• Code path reaches strategy calls ✅ (EUR Calendar error proves this)

---

## ❌ **WHAT'S BROKEN**

### **1. Strategy Execution**
• EUR Calendar: Tries `generate_signals()` but fails (wrong signature)
• Dynamic Multi-Pair: No evidence it's being called
• Trade With Pat ORB: No evidence it's being called
• **Result:** All fall back to default EMA/ATR logic

### **2. Missing Success Logs**
• No `✅ Strategy 'X' generated N signals` messages
• Can't tell if strategies:
  - Aren't being called
  - Are returning empty/None
  - Are failing silently

### **3. Only Error Seen**
• `generate_signals() failed: missing 1 required positional argument: 'pair'`
• Proves code IS trying to call strategies
• But 2-parameter signature handling is broken

---

## 🔍 **ROOT CAUSES**

1. **EUR Calendar:** Code tries 2-parameter signature but fails
2. **Other strategies:** Either not called OR return empty silently
3. **No logging:** Can't verify what's happening
4. **Missing dependencies:** 6 strategies can't load

---

## 🎯 **WHAT NEEDS TO HAPPEN**

1. **Add detailed logging:**
   • Log when `generate_signals()` is called
   • Log what it returns
   • Log when it returns empty

2. **Fix EUR Calendar signature:**
   • 2-parameter code exists but isn't working
   • Debug DataFrame conversion

3. **Verify other strategies:**
   • Add logging to confirm calls
   • Check if they return empty vs not called

4. **Fix missing dependencies:**
   • Install `src.core.order_manager` module
   • Enable 6 blocked strategies

---

## 📋 **BRUTAL SUMMARY**

**Deployment:** ✅ Code deployed
**Integration:** ❌ **BROKEN**
**Success Rate:** **0/9 (0%)**

**The code was deployed, but strategies still aren't working.**

**Only 1 strategy even attempts to run, and it fails immediately.**

**All accounts are using default logic, not strategy-specific logic.**

---

**Next:** Add logging, fix signature handling, verify strategy calls
"""

    send_telegram_message(message)
    print("✅ Brutal verification sent to Telegram")

if __name__ == "__main__":
    main()





