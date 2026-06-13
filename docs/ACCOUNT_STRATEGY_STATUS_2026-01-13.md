# Current Account & Strategy Status Report
**Generated:** 2026-01-13T00:55:00Z

## Summary

**Current State:** ⚠️ **LEGACY MODE** - Only Account 001 is active
- **Accounts Loaded:** 5 (001, 002, 003, 004, 005)
- **Accounts Active:** 1 (001 only)
- **Execution Status:** ✅ ENABLED (but trades being blocked by safety gates)

---

## Account Configuration

### ✅ Account 001 (ACTIVE)
- **Strategy:** `momentum`
- **Instruments:** EUR_USD, GBP_USD, XAU_USD, USD_JPY, AUD_USD (default set)
- **Status:** Generating signals every 30s
- **Trade Execution:** ❌ BLOCKED (Price Sanity Gate - stop loss too far from market)

### ❌ Accounts 002-005 (INACTIVE)
- **Reason:** No strategy assignments configured in runtime config
- **Current Behavior:** Loaded but not trading (legacy mode uses only first account)
- **To Activate:** Need to configure strategy_assignments via API or config file

---

## Will Accounts Make Trades Today?

### Account 001
- **Signals:** ✅ Generating (every 30s)
- **Execution Attempts:** ✅ Attempting trades
- **Current Blocker:** ❌ Price Sanity Gate
  - Strategy generates stop loss at 2645.50
  - Market price is ~4595.11
  - Deviation: 42.43% (threshold: 1.0%)
  - **Status:** All trades blocked until strategy logic generates valid stop losses

### Accounts 002-005
- **Status:** ❌ Not configured for trading
- **Requirement:** Strategy assignments must be configured

---

## Current Strategy Assignments

**Runtime Config:** No strategy_assignments configured
**Fallback:** Legacy mode using `active_strategy_key: momentum` on first account only

---

## Recommended Strategy Assignments (To Enable All 5 Accounts)

Based on system design, recommended assignments:

| Account | Strategy Key | Primary Instrument | Notes |
|---------|--------------|-------------------|-------|
| **001** | `momentum` | EUR_USD, GBP_USD, XAU_USD | ✅ Currently active |
| **002** | `momentum_v2` | EUR_USD, GBP_USD, USD_JPY | ⚠️ Needs assignment |
| **003** | `range` | EUR_USD, USD_JPY, GBP_USD | ⚠️ Needs assignment |
| **004** | `gold` | XAU_USD | ⚠️ Needs assignment |
| **005** | `eur_usd_5m_safe` | EUR_USD | ⚠️ Needs assignment |

**Note:** All strategies currently map to `momentum` or `gold` implementations (see `_get_strategy_by_key` mapping in working_trading_system.py)

---

## Trade Execution Status

### Current Blockers
1. **Price Sanity Gate:** Stop loss distances exceed 1.0% threshold
   - Affects: All signals from account 001
   - Cause: Strategy logic generating stop losses too far from current market price
   - Action Required: Review strategy stop loss calculation logic

2. **Strategy Assignments Missing:** Accounts 002-005 not configured
   - Action Required: Configure strategy_assignments via `/api/config` endpoint

### Safety Gates (Active & Working)
- ✅ Price Sanity Check (blocking invalid orders)
- ✅ Daily Trade Limits (3 per account)
- ✅ Rate Limiting (4 orders/min per VM)
- ✅ Cooldown Periods (300s per symbol, 120s per account)

---

## Next Steps

1. **To Enable All 5 Accounts:**
   ```bash
   # Use the assignment script or API endpoint
   bash scripts/assign_5_strategies_to_5_accounts.sh
   # OR configure via dashboard /api/config endpoint
   ```

2. **To Fix Price Sanity Blocks:**
   - Review momentum strategy stop loss calculation
   - Ensure stop losses are within 1.0% of market price for FX, 1.0% for metals
   - Consider strategy parameter tuning

3. **To Verify Trading:**
   - Monitor logs: `tail -f /tmp/runner.out`
   - Check for `TRADE EXECUTED` messages (not just `EXECUTING`)
   - Verify price sanity blocks are resolved

---

## Verification Commands

```bash
# Check current status
python3 scripts/show_account_strategy_status.py

# Check runner logs
tail -f /tmp/runner.out | grep -E "(STRAT_EVIDENCE|EXECUTING|TRADE EXECUTED|PRICE_SANITY_BLOCK)"

# Check execution status
grep "EXECUTION_UNLOCK_OK" .env
```
