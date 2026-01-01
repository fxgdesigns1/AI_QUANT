# Account Assignments Update

**Date:** November 16, 2025

---

## ✅ Changes Made

### Removed Strategies from Accounts:
1. ❌ **Account 101-004-30719775-004** - Removed `momentum_trading` (was Reserve Account)
2. ❌ **Account 101-004-30719775-003** - Removed `ultra_strict_forex` (was Legacy Ultra Strict)
3. ❌ **Account 101-004-30719775-001** - Removed `arbitrage` (was Strategy Zeta Account)

### New Assignments:

#### 1. Gold Scalper (Winrate)
- **Account ID:** `101-004-30719775-004`
- **Strategy Key:** `gold_scalping_winrate`
- **Account Name:** "Gold Scalper (Winrate) DEMO"
- **Trading Pairs:** `["XAU_USD"]`
- **Risk Settings:**
  - Max risk per trade: 1.2%
  - Max daily risk: 3%
  - Max positions: 1
- **Status:** ✅ Active

#### 2. Gold Scalper (Strict1)
- **Account ID:** `101-004-30719775-003`
- **Strategy Key:** `gold_scalping_strict1`
- **Account Name:** "Gold Scalper (Strict1) DEMO"
- **Trading Pairs:** `["XAU_USD"]`
- **Risk Settings:**
  - Max risk per trade: 1.2%
  - Max daily risk: 3%
  - Max positions: 1
- **Status:** ✅ Active

#### 3. Gold Scalper (Topdown)
- **Account ID:** `101-004-30719775-001`
- **Strategy Key:** `gold_scalping_topdown`
- **Account Name:** "Gold Scalper (Topdown) DEMO"
- **Trading Pairs:** `["XAU_USD"]`
- **Risk Settings:**
  - Max risk per trade: 1.2%
  - Max daily risk: 3%
  - Max positions: 1
- **Status:** ✅ Active

---

## 📊 Updated Account Summary

### All Active Accounts (10 total):

1. ✅ `101-004-30719775-001` → **Gold Scalper (Topdown)** - NEW
2. ✅ `101-004-30719775-003` → **Gold Scalper (Strict1)** - NEW
3. ✅ `101-004-30719775-004` → **Gold Scalper (Winrate)** - NEW
4. ✅ `101-004-30719775-005` → All-Weather 70% WR
5. ✅ `101-004-30719775-006` → GBP/USD Rank #1
6. ✅ `101-004-30719775-007` → Gold Scalping (Base)
7. ✅ `101-004-30719775-008` → Momentum Trading
8. ✅ `101-004-30719775-009` → GBP/USD Rank #2
9. ✅ `101-004-30719775-010` → Trade With Pat ORB (Dual Session)
10. ✅ `101-004-30719775-011` → Dynamic Multi-Pair Unified

---

## 🎯 Lane Mapping

The lanes in `LIVE_TRADING_CONFIG_UNIFIED.yaml` now have corresponding accounts:

- `lane_gold_winrate_demo` → Account `101-004-30719775-004` ✅
- `lane_gold_strict1_demo` → Account `101-004-30719775-003` ✅
- `lane_gold_topdown_demo` → Account `101-004-30719775-001` ✅

---

## 🚀 Next Steps

1. **Deploy Updated Configuration:**
   ```bash
   bash deploy_strategy.sh
   ```

2. **Verify Service Restart:**
   - Check that all 10 accounts are initialized
   - Verify the 3 new Gold Scalper strategies are loaded

3. **Monitor First Trades:**
   - Watch for signals from the new Gold Scalper profiles
   - Compare performance between the 3 profiles

---

## 📝 Notes

- All 3 Gold Scalper profiles are now **active** and ready for trading
- Risk settings match the base Gold Scalping account for consistency
- All accounts are using **demo mode** (OANDA practice accounts)
- The lanes in `LIVE_TRADING_CONFIG_UNIFIED.yaml` are now fully connected to accounts

