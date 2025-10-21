# SYSTEM ARCHITECTURE - MODULAR DESIGN

## YES - SYSTEM IS MODULAR

You can change components independently:

### ✅ MODULAR COMPONENTS:

**1. STRATEGIES (100% Independent)**
- **Files:** `src/strategies/*.py`
- **Change:** Add/modify/remove strategies
- **Affects:** ONLY that strategy's trading logic
- **Safe to edit:** YES
- **Examples:**
  - `gold_scalping.py` - Gold trading logic
  - `gbp_usd_optimized.py` - GBP strategies (Rank 1, 2, 3)
  - `ultra_strict_forex.py` - Multi-timeframe forex
  - `momentum_trading.py` - Momentum-based trading

**2. CONFIGURATION (Centralized)**
- **File:** `accounts.yaml` (SINGLE SOURCE OF TRUTH)
- **Change:** Account settings, strategy assignments, risk limits
- **Affects:** Which strategies run on which accounts
- **Safe to edit:** YES
- **No code changes needed**

**3. SCANNER (Orchestration)**
- **File:** `src/core/candle_based_scanner.py`
- **Role:** Loads strategies from accounts.yaml and runs them
- **Change:** RARELY (only to add new strategy types)
- **Affects:** How strategies are loaded
- **Safe to edit:** Usually NO (unless adding features)

**4. ACCOUNT MANAGER (Account Loading)**
- **File:** `src/core/dynamic_account_manager.py` (SHOULD BE ONLY ONE)
- **Role:** Loads accounts from accounts.yaml
- **Change:** NEVER (just loads from YAML)
- **Affects:** Which accounts are active
- **Safe to edit:** NO (let it read YAML)

---

## ❌ CURRENT PROBLEM: MULTIPLE ACCOUNT MANAGERS

**Found these files (CAUSING CONFUSION):**
1. `src/core/account_manager.py` - Old hardcoded version
2. `src/core/dynamic_account_manager.py` - YAML loader (correct one)
3. Multiple backup/duplicate managers

**Result:** System doesn't know which to use!

---

## 🎯 SOLUTION: ONE ACCOUNT MANAGER

**Keep:** `dynamic_account_manager.py` (reads from accounts.yaml)
**Delete:** All other account manager files
**Rename:** `dynamic_account_manager.py` → `account_manager.py`
**Result:** ONE clear system

---

## 📋 HOW TO CHANGE THINGS (MODULAR GUIDE):

### To Add/Change Strategy:
1. Edit: `src/strategies/your_strategy.py`
2. Deploy
3. Done - affects ONLY that strategy

### To Change Which Strategy an Account Uses:
1. Edit: `accounts.yaml` line for that account
2. Change `strategy: "old_strategy"` to `strategy: "new_strategy"`
3. Deploy
4. Done - affects ONLY that account

### To Change Risk Settings:
1. Edit: `accounts.yaml` risk_settings for account
2. Deploy
3. Done - affects ONLY that account

### To Add New Account:
1. Add to: `accounts.yaml` (copy existing block)
2. Deploy
3. Done - doesn't affect existing accounts

### To Disable Account:
1. Edit: `accounts.yaml` set `active: false`
2. Deploy
3. Done - other accounts keep running

---

## ✅ PERFECT MODULAR WORKFLOW:

```
accounts.yaml (config)
    ↓
dynamic_account_manager.py (loads config)
    ↓
candle_based_scanner.py (runs strategies)
    ↓
strategies/*.py (trading logic)
```

**ONE account manager**
**ONE config file**
**Multiple independent strategies**

---

## 🚫 NEVER EDIT THESE (Unless you know exactly what you're doing):

- `dynamic_account_manager.py` - Just loads YAML
- `candle_based_scanner.py` - Just orchestrates
- `oanda_client.py` - OANDA API wrapper
- `main.py` - Entry point

---

## ✅ SAFE TO EDIT:

- `accounts.yaml` - Change anytime
- `src/strategies/*.py` - Change anytime
- Strategy parameters within strategy files
- Risk settings in accounts.yaml

---

**Next:** I'll clean up duplicate account managers and make ONE clear system.


