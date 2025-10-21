# HOW TO CHANGE THINGS - MODULAR SYSTEM GUIDE

**YES - System is fully modular!**  
**You can change strategies independently without affecting anything else.**

---

## ✅ SAFE TO CHANGE (Won't break system):

### **1. MODIFY A STRATEGY** (100% Independent)

**File:** `src/strategies/your_strategy.py`

**What it affects:** ONLY that strategy's trading logic

**Example - Make Gold less strict:**
```python
# Edit: src/strategies/gold_scalping.py

class GoldScalpingStrategy:
    def __init__(self):
        self.max_spread = 1.5  # Change from 1.0 to 1.5
        self.min_signal_strength = 0.65  # Change from 0.70 to 0.65
```

**Deploy:**
```bash
gcloud app deploy --version=gold-less-strict --quiet
gcloud app services set-traffic default --splits=gold-less-strict=1 --quiet
```

**Result:** Only Gold strategy affected, all other strategies unchanged

---

### **2. CHANGE WHICH STRATEGY AN ACCOUNT USES**

**File:** `accounts.yaml`

**What it affects:** ONLY that specific account

**Example - Switch Account 008 from GBP Rank #1 to Gold Scalping:**
```yaml
# Edit: accounts.yaml line 117

  - id: "101-004-30719775-008"
    strategy: "gold_scalping"  # Changed from gbp_usd_5m_strategy_rank_1
```

**Deploy:**
```bash
gcloud app deploy --version=008-to-gold --quiet
gcloud app services set-traffic default --splits=008-to-gold=1 --quiet
```

**Result:** Account 008 now runs Gold strategy, accounts 006,007,009,010,011 unchanged

---

### **3. CHANGE RISK SETTINGS**

**File:** `accounts.yaml`

**What it affects:** ONLY that account's risk parameters

**Example - Make Account 009 more aggressive:**
```yaml
# Edit: accounts.yaml line 33-37

    risk_settings:
      max_risk_per_trade: 0.03      # Changed from 0.02
      max_portfolio_risk: 0.85       # Changed from 0.75
      max_positions: 5               # Changed from 3
      daily_trade_limit: 150         # Changed from 100
```

**Deploy and done - only Account 009 affected**

---

### **4. ENABLE/DISABLE ACCOUNT**

**File:** `accounts.yaml`

**What it affects:** ONLY that account

**Example - Temporarily disable Account 011:**
```yaml
# Edit: accounts.yaml line 104

    active: false  # Changed from true
```

**Result:** Account 011 stops trading, all others continue

---

### **5. CHANGE INSTRUMENTS AN ACCOUNT TRADES**

**File:** `accounts.yaml`

**What it affects:** ONLY that account's tradeable instruments

**Example - Add EUR/USD to Account 009:**
```yaml
# Edit: accounts.yaml line 29-31

    instruments:
      - XAU_USD
      - EUR_USD  # Added
```

**Result:** Account 009 can now trade EUR/USD and Gold

---

## ⚠️ RARELY CHANGE (System-level):

### **candle_based_scanner.py**
- **Only change when:** Adding support for NEW strategy type
- **Example:** If you create totally new strategy class structure
- **99% of time:** Leave it alone, it auto-loads from accounts.yaml

### **dynamic_account_manager.py**
- **Only change when:** Fixing bugs in YAML loading
- **Example:** Never, it just reads YAML
- **100% of time:** Leave it alone

---

## 🚫 NEVER EDIT (Unless emergency):

### **oanda_client.py**
- OANDA API wrapper
- Only change if OANDA API changes

### **main.py**
- System entry point
- Only change for new features

### **config_loader.py**
- YAML parser
- Only change if YAML structure changes

---

## 📋 TYPICAL WORKFLOW EXAMPLES:

### **Scenario 1: Gold strategy too strict, missing trades**

**Steps:**
1. Edit: `src/strategies/gold_scalping.py`
2. Change: `self.max_spread = 1.5` (from 1.0)
3. Deploy: `gcloud app deploy --version=gold-relaxed --quiet`
4. Route: `gcloud app services set-traffic default --splits=gold-relaxed=1 --quiet`

**Affected:** Only Gold strategy on Account 009  
**Unaffected:** All other 5 accounts

---

### **Scenario 2: Want GBP Rank #2 on Account 009 instead of Gold**

**Steps:**
1. Edit: `accounts.yaml` line 25
2. Change: `strategy: "gbp_usd_5m_strategy_rank_2"` (from gold_scalping)
3. Deploy: `gcloud app deploy --version=009-to-gbp --quiet`
4. Route: `gcloud app services set-traffic default --splits=009-to-gbp=1 --quiet`

**Affected:** Only Account 009 strategy assignment  
**Unaffected:** All other 5 accounts, Gold strategy still available

---

### **Scenario 3: Test new strategy on Account 011 only**

**Steps:**
1. Create: `src/strategies/my_new_strategy.py`
2. Add to: `accounts.yaml` strategies section
3. Edit: Account 011 in `accounts.yaml`: `strategy: "my_new_strategy"`
4. Deploy

**Affected:** Only Account 011  
**Unaffected:** All other 5 accounts continue with existing strategies

---

## ✅ MODULAR BENEFITS:

**Independence:**
- Change one strategy → others unaffected
- Disable one account → others keep running
- Test new strategy on one account → others unchanged

**Safety:**
- Bug in one strategy → doesn't crash system
- One account fails → others continue trading
- Bad configuration → only affects that component

**Flexibility:**
- Run different strategies on different accounts
- Different risk settings per account
- Different instruments per account
- Enable/disable accounts independently

---

## 🎯 GOLDEN RULES:

1. **accounts.yaml = Configuration Hub**
   - All account settings
   - All strategy assignments
   - All risk parameters

2. **Strategies = Independent Trading Logic**
   - Each strategy file is standalone
   - No dependencies between strategies
   - Change one, others unaffected

3. **One Account Manager**
   - `dynamic_account_manager.py` only
   - Just reads accounts.yaml
   - No hardcoded accounts

4. **Test Before Production**
   - Run `pre_deployment_checklist.py`
   - Deploy
   - Run `post_deployment_verify.py`

---

## 📝 QUICK REFERENCE:

| What to Change | File to Edit | Affects | Safe? |
|----------------|--------------|---------|-------|
| Strategy logic | `src/strategies/*.py` | That strategy only | ✅ YES |
| Account config | `accounts.yaml` | That account only | ✅ YES |
| Risk settings | `accounts.yaml` | That account only | ✅ YES |
| Enable/disable account | `accounts.yaml` | That account only | ✅ YES |
| Add new account | `accounts.yaml` | New account only | ✅ YES |
| Scanner logic | `candle_based_scanner.py` | Whole system | ⚠️ RARELY |
| Account manager | `dynamic_account_manager.py` | Whole system | ❌ NO |

---

**System IS modular. Change safely. Just follow the guide.**


