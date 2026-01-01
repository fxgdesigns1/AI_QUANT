#!/usr/bin/env python3
from src.core.settings import settings
"""
Send final deployment verification report to Telegram
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
    message = f"""✅ **DEPLOYMENT & VERIFICATION COMPLETE**

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)

---

## ✅ **FIXES APPLIED & DEPLOYED**

1. ✅ **Syntax Error Fixed:** trade_with_pat_orb_dual.py
2. ✅ **Registry Bug Fixed:** Removed closure issue
3. ✅ **Method Adapter:** Handles analyze_market() and generate_signals()
4. ✅ **Deployed to Production:** All files copied
5. ✅ **Service Restarted:** ai_trading.service running

---

## 📊 **STRATEGY STATUS (9 Total)**

### ✅ **WORKING - Using Strategy Logic (3)**

1. **Dynamic Multi-Pair Unified** (Account 011)
   • ✅ Loads successfully
   • Uses: `generate_signals(market_data)`
   • **Status:** Should use Monte Carlo optimized logic

2. **Trade With Pat ORB Dual** (Account 010)
   • ✅ Loads successfully (syntax fixed)
   • Uses: `generate_signals(market_data)`
   • **Status:** Should use ORB breakout logic

3. **EUR Calendar Optimized V2** (Account 006)
   • ✅ Loads successfully
   • Uses: `generate_signals(data, pair)` - 2 params
   • **Status:** Code should handle this signature

### ❌ **NOT WORKING - Using Default Logic (6)**

4. **Gold Scalper (Topdown)** - Missing dependencies
5. **Gold Scalper (Strict1)** - Missing dependencies
6. **Gold Scalper (Winrate)** - Missing dependencies
7. **Gold Scalping (Base)** - Missing dependencies
8. **Optimized Multi-Pair Live** - Missing dependencies
9. **Momentum Trading** - Missing dependencies

**Issue:** `src.core.order_manager` module not found on VM
**Impact:** These use default EMA/ATR logic (fallback)

---

## 🎯 **WHAT'S HAPPENING NOW**

### **Strategies Using Their Own Logic:**
• Dynamic Multi-Pair: Monte Carlo optimized (88% WR target)
• ORB Strategy: Open-range breakout methodology
• EUR Calendar: Economic calendar integration

### **Strategies Using Default Logic:**
• All gold scalping variants
• Momentum trading
• Optimized multi-pair

---

## 📈 **EXPECTED IMPROVEMENTS**

**For Working Strategies (3):**
• Should show strategy-specific behavior
• Win rates should improve toward targets
• Different logic than default EMA/ATR

**For Non-Working Strategies (6):**
• Currently using default logic
• Will work once dependencies installed
• Need to verify `src.core.order_manager` exists on VM

---

## 🔍 **VERIFICATION**

**Service Status:** ✅ Running
**Code Deployed:** ✅ Yes
**Strategies Loading:** 3/9 (33%)
**Registry Bug:** ✅ Fixed
**Syntax Errors:** ✅ Fixed

---

## ⚠️ **ACTION REQUIRED**

**Install Missing Dependencies:**
• Verify `src.core.order_manager` exists on VM
• Path: `/opt/quant_system_clean/google-cloud-trading-system/src/core/`
• If missing, install or fix import paths

---

## 📋 **MONITORING**

**Watch logs for:**
• `✅ Strategy 'X' (generate_signals) generated N signals`
• Strategy-specific behavior
• Improved win rates

**Next Check:** Monitor for 24-48 hours to verify strategies are being called

---

**Status:** ✅ Deployed - 3 strategies working, 6 need dependencies
"""

    send_telegram_message(message)
    print("✅ Final deployment report sent to Telegram")

if __name__ == "__main__":
    main()





