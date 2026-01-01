# Account Reservations for New Strategies

**Date:** November 16, 2025

---

## ✅ Accounts Reserved (Strategies Removed)

### Account `101-004-30719775-005`
- **Previous Strategy:** All-Weather 70% WR (`all_weather_70wr`)
- **Status:** ✅ Reserved - Strategy removed, account set to inactive
- **Name:** "Reserved for New Strategy"
- **Ready for:** New strategy assignment

### Account `101-004-30719775-006`
- **Previous Strategy:** GBP/USD Rank #1 (`gbp_rank_1`)
- **Status:** ✅ Reserved - Strategy removed, account set to inactive
- **Name:** "Reserved for New Strategy"
- **Ready for:** New strategy assignment

### Account `101-004-30719775-009`
- **Previous Strategy:** GBP/USD Rank #2 (`gbp_rank_2`)
- **Status:** ✅ Reserved - Strategy removed, account set to inactive
- **Name:** "Reserved for New Strategy"
- **Ready for:** New strategy assignment

---

## 📋 Account 002 Status

### Account `101-004-30719775-002`
- **Current Status:** Not in `accounts.yaml` (not currently assigned)
- **Historical Reference:** 
  - Referenced in `oanda_config.env` as `GOLD_SCALP_ACCOUNT`
  - Previously used for Gold Scalping strategy
  - Currently **AVAILABLE** for new strategy assignment

**Note:** Account 002 is not currently in the active accounts list, so it's available for use. You can add it to `accounts.yaml` when ready to assign a new strategy.

---

## 🎯 Available Accounts for New Strategies

You now have **4 accounts** ready for new strategy development:

1. ✅ `101-004-30719775-002` - Not in config (available)
2. ✅ `101-004-30719775-005` - Reserved (inactive, placeholder)
3. ✅ `101-004-30719775-006` - Reserved (inactive, placeholder)
4. ✅ `101-004-30719775-009` - Reserved (inactive, placeholder)

---

## 📊 Current Active Accounts (7 remaining)

After removing the 3 strategies, you still have these active:

1. `101-004-30719775-001` → Gold Scalper (Topdown)
2. `101-004-30719775-003` → Gold Scalper (Strict1)
3. `101-004-30719775-004` → Gold Scalper (Winrate)
4. `101-004-30719775-007` → Gold Scalping (Base)
5. `101-004-30719775-008` → Momentum Trading
6. `101-004-30719775-010` → Trade With Pat ORB (Dual Session)
7. `101-004-30719775-011` → Dynamic Multi-Pair Unified

---

## 🔧 Next Steps

When you develop new strategies, you can:

1. **Assign to reserved accounts:**
   - Update `accounts.yaml` for accounts 005, 006, or 009
   - Change `strategy: "placeholder"` to your new strategy key
   - Set `active: true`
   - Add appropriate `trading_pairs` and `risk_settings`

2. **Add account 002:**
   - Add a new entry in `accounts.yaml` for account 002
   - Configure with your new strategy

3. **Deploy:**
   - Run `deploy_strategy.sh` to push changes to GCloud

---

**Last Updated:** November 16, 2025

