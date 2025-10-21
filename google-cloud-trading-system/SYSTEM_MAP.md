# SYSTEM MAP - WHAT EACH FILE DOES

**System is NOW clean, modular, and working with ALL 6 accounts.**

---

## 📁 CORE STRUCTURE (What Each File Does):

### **1. CONFIGURATION (Single Source of Truth)**

```
accounts.yaml ← EDIT THIS to change accounts/strategies/risk
```

**Purpose:** Defines ALL accounts, strategies, risk settings  
**Edit frequency:** Often (when adjusting trading)  
**Affects:** Whatever you change (modular)  
**Safe to edit:** ✅ YES

---

### **2. ACCOUNT LOADING (ONE FILE ONLY)**

```
src/core/dynamic_account_manager.py ← Reads accounts.yaml
```

**Purpose:** Loads ALL accounts from accounts.yaml  
**Edit frequency:** Never (just loads YAML)  
**Affects:** Account loading only  
**Safe to edit:** ❌ NO (leave it alone)

**What it does:**
- Reads accounts.yaml
- Creates OANDA client for each account
- Maps strategies to accounts
- **No hardcoded accounts!**

---

### **3. STRATEGY ORCHESTRATOR**

```
src/core/candle_based_scanner.py ← Runs all strategies
```

**Purpose:** Loads strategies, runs them on new candles  
**Edit frequency:** Rarely (only for new features)  
**Affects:** How strategies are executed  
**Safe to edit:** ⚠️ SOMETIMES (if you know what you're doing)

**What it does:**
- Imports strategy functions
- Maps accounts to strategies
- Triggers strategy analysis on new candles
- Sends trade signals to order manager

---

### **4. STRATEGIES (Fully Independent)**

```
src/strategies/
├── gold_scalping.py ← Gold trading logic
├── gbp_usd_optimized.py ← GBP Ranks 1, 2, 3
├── ultra_strict_forex.py ← Strict forex trading
├── momentum_trading.py ← Momentum-based
└── [other strategies]
```

**Purpose:** Individual trading algorithms  
**Edit frequency:** Often (to optimize trading)  
**Affects:** ONLY that strategy  
**Safe to edit:** ✅ YES (fully modular)

**What they do:**
- Analyze market data
- Generate BUY/SELL signals
- Calculate entry/exit points
- Independent of each other

---

### **5. VERIFICATION SCRIPTS**

```
verify_scanner_config.py ← Pre-deploy check
pre_deployment_checklist.py ← Mandatory before deploy
post_deployment_verify.py ← Verify after deploy
```

**Purpose:** Catch errors before they cost money  
**Edit frequency:** Rarely (to add new checks)  
**Affects:** Deployment safety  
**Safe to edit:** ✅ YES (to improve)

---

## 🎯 CLEAN FILE HIERARCHY:

```
google-cloud-trading-system/
│
├── accounts.yaml ← CONFIGURATION (Edit this often)
├── main.py ← Entry point (Rarely edit)
├── app.yaml ← Google Cloud config (Rarely edit)
├── requirements.txt ← Python deps (Rarely edit)
│
├── src/
│   ├── core/ ← SYSTEM COMPONENTS
│   │   ├── dynamic_account_manager.py ← Loads accounts (Never edit)
│   │   ├── candle_based_scanner.py ← Runs strategies (Rarely edit)
│   │   ├── oanda_client.py ← OANDA API (Never edit)
│   │   ├── config_loader.py ← YAML parser (Never edit)
│   │   ├── order_manager.py ← Places orders (Never edit)
│   │   └── [other core files]
│   │
│   ├── strategies/ ← TRADING LOGIC (Edit anytime)
│   │   ├── gold_scalping.py
│   │   ├── gbp_usd_optimized.py
│   │   ├── ultra_strict_forex.py
│   │   ├── momentum_trading.py
│   │   └── [add your own strategies]
│   │
│   └── dashboard/ ← UI (Rarely edit)
│       ├── advanced_dashboard.py
│       └── [dashboard files]
│
├── verification/ ← SAFETY CHECKS
│   ├── verify_scanner_config.py
│   ├── pre_deployment_checklist.py
│   └── post_deployment_verify.py
│
└── docs/ ← DOCUMENTATION
    ├── SYSTEM_MAP.md ← This file
    ├── HOW_TO_CHANGE_THINGS.md ← Modular guide
    ├── DEPLOYMENT_WORKFLOW.md ← How to deploy
    └── SYSTEM_ARCHITECTURE.md ← Architecture overview
```

---

## ✅ WHAT WAS CLEANED UP:

**Deleted (Causing confusion):**
- ❌ `src/core/account_manager.py` - Old hardcoded version
- ❌ `clean_deploy/` - Old backup directory
- ❌ `cloud_run_deploy/` - Old backup directory
- ❌ `minimal_deploy/` - Old backup directory

**Kept (Essential):**
- ✅ `src/core/dynamic_account_manager.py` - ONLY account manager
- ✅ `src/strategies/*.py` - All active strategies
- ✅ `accounts.yaml` - Configuration file

**Result:** ONE clear path, no confusion

---

## 🚀 CURRENT DEPLOYMENT STATUS:

**Version:** oct14-direct-yaml  
**Status:** ✅ ONLINE  
**Accounts:** ✅ 6/6 loaded  
**Scanner:** ✅ Running  
**Data:** ✅ Live OANDA  

**Accounts loaded:**
- 006: TOP_STRATEGY_3_CONSERVATIVE (GBP Rank #3)
- 007: TOP_STRATEGY_2_EXCELLENT (GBP Rank #2)
- 008: TOP_STRATEGY_1_CHAMPION (GBP Rank #1)
- 009: Gold Primary 5M (Gold Scalping)
- 010: Forex Scalper 15M (Ultra Strict)
- 011: Combined Portfolio (Momentum)

---

## 📋 TO VERIFY MODULARITY YOURSELF:

**Test 1: Change one strategy's threshold**
```bash
# Edit src/strategies/gold_scalping.py line X
# Change one parameter
# Deploy
# Check: Only Gold strategy affected
```

**Test 2: Change one account's risk**
```bash
# Edit accounts.yaml Account 009 risk settings
# Change max_risk_per_trade
# Deploy
# Check: Only Account 009 affected
```

**Both tests should affect ONLY the component you changed.**

---

## ✅ SYSTEM IS NOW:

- **Clean:** No duplicate files
- **Modular:** Change components independently
- **Working:** All 6 accounts loaded
- **Documented:** Clear guides for everything

**No more confusion. No more lies. System is correct.**

---

**Last updated:** October 13, 2025 16:11 BST  
**Status:** CLEANED & VERIFIED ✅


