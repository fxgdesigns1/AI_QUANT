# Strategies NOT Assigned to Accounts

**Generated:** November 16, 2025

---

## ❌ Strategies with NO Account Assignment

### 1. **Alpha EMA Momentum** (`alpha`)
- **Status:** Registered but NOT assigned
- **Description:** EMA(3/8/21) crossover with momentum confirmation
- **Action Needed:** Assign to an account in `accounts.yaml`

### 2. **Pattern Discovery V11** (`pattern_discovery_v11`)
- **Status:** Registered but NOT assigned
- **Description:** RSI band + EMA separation pattern engine derived from v11 dataset
- **Action Needed:** Assign to an account in `accounts.yaml`

### 3. **GBP/USD Rank #3** (`gbp_rank_3`)
- **Status:** Registered but NOT directly assigned
- **Description:** Lowest drawdown GBP/USD EMA strategy for conservative deployment
- **Note:** Account `101-004-30719775-010` is assigned to `trade_with_pat_orb_dual`, not `gbp_rank_3`
- **Action Needed:** Either assign to a new account or reassign account 010

---

## ⚠️ Strategies with Lanes but NO Account IDs

These strategies have lanes configured in `LIVE_TRADING_CONFIG_UNIFIED.yaml` but **NO account_id** in `accounts.yaml`:

### 4. **Gold Scalper (Winrate)** (`gold_scalping_winrate`)
- **Lane ID:** `lane_gold_winrate_demo`
- **Status:** Active in config, but **NO account_id assigned**
- **Description:** Gold scalper profile emphasizing maximum win-rate and tighter filters
- **Action Needed:** Add account_id to `accounts.yaml` for this lane

### 5. **Gold Scalper (Strict1)** (`gold_scalping_strict1`)
- **Lane ID:** `lane_gold_strict1_demo`
- **Status:** Active in config, but **NO account_id assigned**
- **Description:** Gold scalper strict profile with conservative entries and risk
- **Action Needed:** Add account_id to `accounts.yaml` for this lane

### 6. **Gold Scalper (Topdown)** (`gold_scalping_topdown`)
- **Lane ID:** `lane_gold_topdown_demo`
- **Status:** Active in config, but **NO account_id assigned**
- **Description:** Gold scalper top-down profile aligning higher timeframe bias with entries
- **Action Needed:** Add account_id to `accounts.yaml` for this lane

---

## ✅ Strategies WITH Account Assignment

These strategies ARE properly assigned:

1. ✅ `gold_scalping` → Account `101-004-30719775-007`
2. ✅ `momentum_trading` → Account `101-004-30719775-008`
3. ✅ `gbp_rank_1` → Account `101-004-30719775-006`
4. ✅ `gbp_rank_2` → Account `101-004-30719775-009`
5. ✅ `all_weather_70wr` → Account `101-004-30719775-005`
6. ✅ `dynamic_multi_pair_unified` → Account `101-004-30719775-011`
7. ✅ `trade_with_pat_orb_dual` → Account `101-004-30719775-010`
8. ✅ `ultra_strict_forex` → Account `101-004-30719775-003` (inactive)

---

## 📊 Summary

- **Total Registered Strategies:** 13
- **Assigned to Accounts:** 8 (including 1 inactive)
- **Unassigned:** 6 strategies
  - 3 completely unassigned (alpha, pattern_discovery_v11, gbp_rank_3)
  - 3 have lanes but no account_id (gold_scalping_winrate, gold_scalping_strict1, gold_scalping_topdown)

---

## 🎯 Available Accounts for Assignment

You have these inactive accounts available:
- `101-004-30719775-004` - Reserve Account (inactive)
- `101-004-30719775-003` - Legacy Ultra Strict (inactive, currently assigned to ultra_strict_forex)
- `101-004-30719775-001` - Strategy Zeta Account (inactive)

**Note:** You may need to create new demo accounts for the 3 Gold Scalper lanes if you want to keep them separate.

---

## 🔧 Action Items

1. **Assign account IDs to Gold Scalper lanes:**
   - Add entries in `accounts.yaml` for `lane_gold_winrate_demo`, `lane_gold_strict1_demo`, `lane_gold_topdown_demo`

2. **Assign unassigned strategies:**
   - Decide if you want to assign `alpha`, `pattern_discovery_v11`, and `gbp_rank_3` to accounts
   - Use available inactive accounts or create new ones

3. **Resolve account 010 conflict:**
   - Account `101-004-30719775-010` is assigned to `trade_with_pat_orb_dual` in accounts.yaml
   - But blotter shows it running `gbp_rank_3` - verify which is correct

