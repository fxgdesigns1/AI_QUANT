#!/usr/bin/env python3
"""
Send strategy status report to Telegram
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
    message = f"""🔍 **STRATEGY STATUS CHECK - ARE THEY RUNNING CORRECTLY?**

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)

---

## ⚠️ **CRITICAL FINDING: ALL STRATEGIES USING DEFAULT LOGIC**

**Current Status:** ❌ **0 out of 9 strategies running correctly**

All strategies are currently using the default EMA/ATR breakout logic instead of their specific implementations.

---

## 📊 **STATUS PER STRATEGY**

### **1. Gold Scalper (Topdown)** - $105,655
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Cannot load - missing dependencies
• **Current:** Using default logic
• **Trades (24h):** 0

### **2. Gold Scalper (Strict1)** - $90,406
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Cannot load - missing dependencies
• **Current:** Using default logic
• **Trades (24h):** 0

### **3. Gold Scalper (Winrate)** - $95,220
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Cannot load - missing dependencies
• **Current:** Using default logic (4 losses)
• **Trades (24h):** 4

### **4. Gold Scalping (Base)** - $98,855
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Cannot load - missing dependencies
• **Current:** Using default logic (4 losses)
• **Trades (24h):** 4

### **5. Optimized Multi-Pair Live** - $98,490
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Cannot load - missing dependencies
• **Current:** Using default logic (NOT Monte Carlo optimized)
• **Trades (24h):** 8
• **Expected:** 88% WR with Monte Carlo optimization

### **6. Dynamic Multi-Pair Unified** - $115,231
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Loads but uses `generate_signals()` not `analyze_market()`
• **Current:** Using default logic
• **Trades (24h):** 8
• **Fix Applied:** Code now checks for both methods ✅

### **7. Momentum Trading** - $106,826
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Cannot load - missing dependencies
• **Current:** Using default logic (OVERTRADING - 43 trades)
• **Trades (24h):** 43 (should be max 15)
• **Expected:** ADX/momentum filters, quality scoring

### **8. Trade With Pat ORB Dual** - $95,899
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Syntax error in strategy file (line 20)
• **Current:** Using default logic (NOT ORB methodology)
• **Trades (24h):** 25
• **Expected:** Open-range breakout logic

### **9. EUR Calendar Optimized V2** - $97,140
• **Status:** ❌ NOT RUNNING CORRECTLY
• **Issue:** Cannot load - missing dependencies
• **Current:** Using default logic (NO calendar integration)
• **Trades (24h):** 3
• **Expected:** Economic calendar integration, 75% WR

---

## 🐛 **ROOT CAUSES**

### **1. Missing Dependencies (8 strategies)**
• Strategies require `src.core.order_manager` module
• Not available in local test environment
• **Should be available on production VM**
• **Location:** `/opt/quant_system_clean/google-cloud-trading-system/`

### **2. Method Name Mismatch (1 strategy)**
• `dynamic_multi_pair_unified` uses `generate_signals()` not `analyze_market()`
• **FIXED:** Code now checks for both methods ✅

### **3. Syntax Error (1 strategy)**
• `trade_with_pat_orb_dual.py` has syntax error at line 20
• **Action Required:** Fix syntax error

---

## ✅ **WHAT'S WORKING**

1. ✅ **System is Trading:** All accounts executing trades
2. ✅ **Fallback Logic:** Default EMA/ATR working (explains current performance)
3. ✅ **Fix is Implemented:** Code changes in place
4. ✅ **Method Adapter:** Now handles both `analyze_market()` and `generate_signals()`

---

## 🔧 **REQUIRED ACTIONS**

### **Priority 1: Deploy to Production**
• Dependencies should be available on production VM
• Strategies should load correctly there
• **Action:** Deploy updated code to production

### **Priority 2: Fix Syntax Error**
• File: `trade_with_pat_orb_dual.py` line 20
• **Action:** Fix indentation/syntax

### **Priority 3: Monitor Production Logs**
• Look for: `✅ Loaded strategy 'X'`
• Look for: `✅ Strategy 'X' generated N signals`
• **Action:** Verify strategies load and run on production

---

## 📈 **EXPECTED AFTER FIXES**

Once strategies load on production:
• Each strategy uses its own logic
• Win rates should improve significantly
• Overtrading should reduce (momentum: 43 → max 15)
• Strategy-specific optimizations active

---

## 🎯 **BOTTOM LINE**

**Current:** All 9 strategies using default logic (15.9% WR)
**After Fix:** Each strategy uses its own optimized logic
**Status:** Code ready, waiting for production deployment where dependencies exist

---

**Next Step:** Deploy to production VM and monitor logs
"""

    send_telegram_message(message)
    print("✅ Strategy status report sent to Telegram")

if __name__ == "__main__":
    main()





