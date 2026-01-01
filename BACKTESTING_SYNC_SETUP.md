# Backtesting System Sync Setup

**Date:** November 16, 2025

---

## 🔄 Backtesting Parity Lane Configuration

### Lane Details:
- **Lane ID:** `lane_backtest_parity`
- **Strategy:** `optimized_multi_pair_live`
- **Account Reference:** `101-004-30719775-002` (Optimized Multi-Pair Live)
- **Status:** Inactive (for backtesting only)
- **Purpose:** Ensures config/logic parity between live trading and backtesting system

### Instruments:
- USD_CAD
- NZD_USD
- GBP_USD
- EUR_USD
- XAU_USD
- USD_JPY

---

## 📊 How It Works

### Live Trading Account:
- **Account:** `101-004-30719775-002`
- **Strategy:** `optimized_multi_pair_live`
- **Status:** ✅ Active
- **Trades:** All 6 pairs with 5x position multiplier

### Backtesting Sync Lane:
- **Lane:** `lane_backtest_parity` in `LIVE_TRADING_CONFIG_UNIFIED.yaml`
- **Strategy:** `optimized_multi_pair_live` (same as account 002)
- **Status:** ⏸️ Inactive (backtesting only)
- **Purpose:** 
  - Mirrors account 002 configuration
  - Used by backtesting system to validate parity
  - Blotter data from account 002 syncs to backtesting system

---

## 🔗 Sync Process

1. **Live Trading:** Account 002 runs `optimized_multi_pair_live` strategy
2. **Blotter Generation:** All trades from account 002 are logged
3. **Sync Script:** `sync_blotter_to_backtest.sh` copies blotter data
4. **Backtesting System:** Uses synced data to validate strategy performance
5. **Parity Check:** Compares live results with backtest expectations

---

## 📁 Files Involved

### Live Trading:
- Account config: `accounts.yaml` → Account 002
- Strategy file: `src/strategies/optimized_multi_pair_live.py`
- Blotter: `data/live_trade_blotter.json` (account 002 trades)

### Backtesting Sync:
- Lane config: `LIVE_TRADING_CONFIG_UNIFIED.yaml` → `lane_backtest_parity`
- Sync script: `sync_blotter_to_backtest.sh`
- Sync destination: `backtest_blotter_sync/`

---

## 🎯 Usage

### For Backtesting System:
1. Run sync script: `bash sync_blotter_to_backtest.sh`
2. Blotter data from account 002 is copied to `backtest_blotter_sync/`
3. Backtesting system reads synced data for validation
4. Compare live performance vs backtest expectations

### For Live Trading:
- Account 002 runs normally
- All trades logged to blotter
- No impact from backtesting lane (it's inactive)

---

## 📝 Notes

- The backtesting lane is **inactive** in production
- It's a configuration reference, not a running account
- Account 002 is the actual trading account
- Backtesting system syncs with account 002's blotter data
- This ensures you can always compare live vs backtest performance

---

**Last Updated:** November 16, 2025

