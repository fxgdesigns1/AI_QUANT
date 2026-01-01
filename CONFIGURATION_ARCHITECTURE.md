# 🏗️ CONFIGURATION ARCHITECTURE
**System:** AI Trading System (GCloud Deployment)  
**Last Updated:** November 16, 2025

---

## 📋 OVERVIEW: GLOBAL vs PER-STRATEGY CONFIG

### Configuration Model: **HYBRID**

The system uses a **hierarchical configuration model** with both global settings and per-strategy overrides:

```
Global Settings (LIVE_TRADING_CONFIG_UNIFIED.yaml)
    ↓
Account Mapping (accounts.yaml)
    ↓
Strategy Registry (registry.py)
    ↓
Individual Strategy Files (*.py)
```

---

## 🌍 GLOBAL CONFIGURATION

### File: `LIVE_TRADING_CONFIG_UNIFIED.yaml`

**Purpose:** Define system-wide settings, risk limits, and trading "lanes"

**Location:** `/opt/quant_system_clean/google-cloud-trading-system/LIVE_TRADING_CONFIG_UNIFIED.yaml`

### What's Global?

```yaml
trading_mode: "LIVE"                    # System mode
max_total_exposure: 0.10                # 10% portfolio cap
max_concurrent_positions: 5             # System-wide position limit
enable_news_filtering: true             # News-based filters
telegram_enabled: true                  # Telegram alerts
data_sync_mode: "real_time"             # Data refresh mode
```

### Lane Definitions (Strategy-Level Config in Global File)

```yaml
lanes:
  - id: "lane_gold_winrate_demo"
    name: "Gold Scalper (Winrate) DEMO"
    strategy: "gold_scalping_winrate"   # Links to registry
    active: true                         # Enable/disable lane
    instruments: ["XAU_USD"]            # Trading pairs
    
  - id: "lane_backtest_parity"
    strategy: "optimized_multi_pair_live"
    active: false                        # Backtesting only
    account_ref: "101-004-30719775-002"
```

**Lane = Strategy Configuration Container**
- Each lane defines one strategy's global parameters
- Lanes are the "blueprint" for how a strategy operates
- Lanes can be active (trading) or inactive (reference only)

---

## 🎯 ACCOUNT-SPECIFIC CONFIGURATION

### File: `accounts.yaml`

**Purpose:** Map OANDA accounts to strategies with risk settings

**Location:** `/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml`

### What's Per-Account?

```yaml
accounts:
  gold_scalp_winrate:
    account_id: "101-004-30719775-004"   # OANDA account
    name: "Gold Scalper (Winrate) DEMO"
    strategy: "gold_scalping_winrate"    # Strategy key
    trading_pairs: ["XAU_USD"]           # Pairs for this account
    risk_settings:                       # Account-specific risk
      max_risk_per_trade: 0.012          # 1.2% per trade
      max_daily_risk: 0.03               # 3% daily
      max_positions: 1                   # Max 1 position
    active: true                         # Enable trading
    credentials_ref: "OANDA_API_KEY"
```

### Account-Level Override

**Accounts inherit from lanes but can override:**
- Risk parameters (max_risk_per_trade, max_daily_risk)
- Position limits (max_positions, max_daily_trades)
- Trading pairs (can subset the lane's instruments)
- Position sizing multipliers

---

## 📦 STRATEGY REGISTRY

### File: `registry.py`

**Purpose:** Map strategy keys to factory functions

**Location:** `/opt/quant_system_clean/google-cloud-trading-system/src/strategies/registry.py`

### What's in the Registry?

```python
STRATEGY_REGISTRY = {
    "gold_scalping_winrate": StrategyDefinition(
        key="gold_scalping_winrate",
        display_name="Gold Scalper (Winrate)",
        factory=get_gold_scalping_winrate_strategy,  # Factory function
        description="Gold scalper with maximum win-rate filters"
    ),
    # ... more strategies
}
```

**Registry = Strategy Lookup Table**
- Maps `strategy: "gold_scalping_winrate"` (from accounts.yaml) → Python factory function
- Each strategy key must be registered here
- Factory functions instantiate strategy objects with specific profiles

---

## 🔧 INDIVIDUAL STRATEGY FILES

### Files: `src/strategies/*.py`

**Purpose:** Implement strategy-specific logic and profiles

**Example:** `gold_scalping_winrate.py`

```python
from .gold_scalping_optimized import GoldScalpingStrategy

def get_gold_scalping_winrate_strategy():
    """Factory function for registry"""
    return GoldScalpingStrategy(
        profile='winrate',              # Strategy profile
        instruments=['XAU_USD']
    )
```

### What's Per-Strategy?

**Strategy files define:**
- Trading logic (entry/exit rules)
- Technical indicators (EMA, RSI, etc.)
- Profile-specific parameters (winrate, strict1, topdown)
- Signal generation
- Position management logic

**Strategy files do NOT define:**
- Risk limits (comes from accounts.yaml)
- Account IDs (comes from accounts.yaml)
- Global exposure limits (comes from LIVE_TRADING_CONFIG_UNIFIED.yaml)

---

## 🔄 CONFIGURATION FLOW

### How It All Works Together

```
1. System reads LIVE_TRADING_CONFIG_UNIFIED.yaml
   └─ Loads global settings (max_exposure, telegram, etc.)
   └─ Loads lane definitions (strategy blueprints)

2. System reads accounts.yaml
   └─ Maps accounts to strategies
   └─ Applies account-specific risk settings

3. For each active account:
   a. Look up strategy key in registry.py
   b. Call factory function to instantiate strategy
   c. Pass account risk settings to strategy
   d. Start trading with account credentials

4. Strategy executes:
   └─ Generates signals based on strategy logic
   └─ Respects risk limits from accounts.yaml
   └─ Respects global limits from LIVE_TRADING_CONFIG_UNIFIED.yaml
```

---

## 📊 CONFIGURATION PRECEDENCE

### Order of Priority (Highest to Lowest)

1. **Account-specific settings** (accounts.yaml)
   - Risk per trade
   - Daily risk limits
   - Position limits

2. **Lane settings** (LIVE_TRADING_CONFIG_UNIFIED.yaml)
   - Trading pairs/instruments
   - Strategy selection
   - Active/inactive status

3. **Global settings** (LIVE_TRADING_CONFIG_UNIFIED.yaml)
   - Total portfolio exposure
   - System-wide position limits
   - Telegram/news settings

4. **Strategy defaults** (strategy *.py files)
   - Entry/exit logic
   - Indicator parameters
   - Profile-specific settings

### Example: Max Positions

```
Global: max_concurrent_positions = 5     (system-wide)
Account: max_positions = 1               (account limit)
→ Result: Account will never exceed 1 position
```

---

## 🎯 SINGLE SOURCE OF TRUTH

### Each Config Has a Role

| Config File | Responsible For | Never Contains |
|-------------|-----------------|----------------|
| `LIVE_TRADING_CONFIG_UNIFIED.yaml` | Global limits, lanes, system mode | Account IDs, API keys |
| `accounts.yaml` | Account-strategy mapping, risk per account | Strategy logic, global limits |
| `registry.py` | Strategy key → factory mapping | Risk settings, account IDs |
| Strategy `*.py` files | Trading logic, signals | Risk limits, account IDs |

### ✅ No Duplication, No Conflicts

- **Account ID** → Only in `accounts.yaml`
- **Risk limits** → Only in `accounts.yaml` (per-account) and `LIVE_TRADING_CONFIG_UNIFIED.yaml` (global)
- **Strategy logic** → Only in strategy `*.py` files
- **Strategy key mapping** → Only in `registry.py`

---

## 🔍 EXAMPLE: Gold Scalper (Winrate) Config Chain

### 1. Global Lane Definition
**File:** `LIVE_TRADING_CONFIG_UNIFIED.yaml`
```yaml
lanes:
  - id: "lane_gold_winrate_demo"
    strategy: "gold_scalping_winrate"
    active: true
    instruments: ["XAU_USD"]
```

### 2. Account Mapping
**File:** `accounts.yaml`
```yaml
gold_scalp_winrate:
  account_id: "101-004-30719775-004"
  strategy: "gold_scalping_winrate"
  trading_pairs: ["XAU_USD"]
  risk_settings:
    max_risk_per_trade: 0.012
    max_daily_risk: 0.03
    max_positions: 1
  active: true
```

### 3. Registry Lookup
**File:** `registry.py`
```python
"gold_scalping_winrate": StrategyDefinition(
    key="gold_scalping_winrate",
    factory=get_gold_scalping_winrate_strategy,
)
```

### 4. Strategy Implementation
**File:** `gold_scalping_winrate.py`
```python
def get_gold_scalping_winrate_strategy():
    return GoldScalpingStrategy(profile='winrate')
```

### 5. Execution
```
System loads account 004 → 
  Finds strategy "gold_scalping_winrate" in registry → 
    Calls get_gold_scalping_winrate_strategy() → 
      Creates GoldScalpingStrategy(profile='winrate') → 
        Trades XAU_USD with 1.2% risk per trade
```

---

## 🛡️ BENEFITS OF THIS ARCHITECTURE

### ✅ Advantages

1. **Separation of Concerns**
   - Global settings ≠ Account settings ≠ Strategy logic

2. **Easy Strategy Switching**
   - Change `strategy: "old"` → `strategy: "new"` in accounts.yaml
   - No code changes required

3. **Account Isolation**
   - Each account has independent risk settings
   - No cross-contamination of performance

4. **Centralized Registry**
   - All strategies registered in one place
   - Easy to add/remove strategies

5. **Profile Flexibility**
   - Same base strategy (e.g., GoldScalpingStrategy)
   - Multiple profiles (winrate, strict1, topdown)
   - Each profile = separate account

---

## 📝 SUMMARY

### Configuration Responsibility Matrix

| What | Where | Who Controls It |
|------|-------|-----------------|
| Trading mode (LIVE/DEMO) | `LIVE_TRADING_CONFIG_UNIFIED.yaml` | Global system |
| Max total exposure | `LIVE_TRADING_CONFIG_UNIFIED.yaml` | Global system |
| Account → Strategy mapping | `accounts.yaml` | Account admin |
| Risk per account | `accounts.yaml` | Account admin |
| Strategy key → Function | `registry.py` | Developer |
| Entry/exit logic | Strategy `*.py` | Developer |
| Profile selection | Strategy `*.py` factory | Developer |

### Is Config Global or Per-Strategy?

**Both!**
- **Global:** System-wide limits, mode, lanes
- **Per-Account:** Risk limits, position sizing, active status
- **Per-Strategy:** Trading logic, indicators, profiles

**The system is NEITHER purely global NOR purely per-strategy. It's a hybrid hierarchy where each level has clear responsibilities.**

---

**Architecture Documentation**  
**Author:** AI Assistant  
**System Version:** GCloud Trading System v2.0  
**Date:** November 16, 2025

