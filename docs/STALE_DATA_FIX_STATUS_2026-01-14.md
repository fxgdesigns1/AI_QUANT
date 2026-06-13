# STALE DATA FIX - STATUS REPORT
## 2026-01-14T19:30:00Z

## ✅ FIXES APPLIED

### 1. Added Stale Candle Rejection to `get_candles()`
**File**: `src/control_plane/market_data_provider.py`
**Fix**: Added mandatory freshness check that REJECTS candles older than 30 minutes
**Status**: ✅ Code deployed
**Impact**: ALL strategies calling `get_candles()` will now get `MarketDataError` if OANDA returns stale data

### 2. Removed XAU_USD from Default Instruments
**File**: `working_trading_system.py`
**Fix**: Removed 'XAU_USD' from default instruments list (line 624)
**Status**: ✅ Code deployed
**Impact**: New accounts/strategies won't include XAU_USD by default

## ❌ REMAINING PROBLEM

### The Issue
Strategies are STILL generating `XAU_USD @ 2650` signals even after fixes because:

1. **Python bytecode cache**: The runner is loading OLD `.pyc` files in memory
2. **Strategy files were deleted**: Earlier script removed strategy files but runner cached them
3. **Old strategies still loaded**: Runner must be restarted with cache cleared

### Evidence
- Logs show `momentum_trading.py` generating signals but file doesn't exist
- No `STALE_CANDLES` errors in logs (means either fix not loaded OR strategies catching exceptions)
- Strategies still generating XAU_USD signals with 2650 price

## 🚨 IMMEDIATE ACTION REQUIRED

### Manual Fix Steps (on VM):

```bash
# 1. Stop runner
sudo systemctl stop ai-quant-runner.service

# 2. Kill ALL Python processes (nuclear option)
sudo pkill -9 python
sudo pkill -9 -f runner

# 3. NUCLEAR cache clear
find ~/gcloud-system -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find ~/gcloud-system -name '*.pyc' -delete 2>/dev/null  
find ~/gcloud-system -name '*.pyo' -delete 2>/dev/null

# 4. Restore strategy files from backup OR recreate them
# (Check for .bak files)

# 5. Restart runner
sudo systemctl start ai-quant-runner.service

# 6. Monitor logs for STALE_CANDLES errors
sudo journalctl -u ai-quant-runner.service -f | grep -E 'STALE_CANDLES|XAU_USD|Generated'
```

## 🔍 WHY 2650 PRICE APPEARS

**This is NOT hardcoded in source code!** 

The price comes from:
1. OANDA's `get_candles('XAU_USD')` returning OLD candle data (weeks/months old when gold was $2650)
2. Strategies using that stale candle's close price somewhere in the flow
3. Price sanity check CORRECTLY blocking these trades (42% deviation)

## ✅ VERIFICATION CHECKLIST

After restart, verify:
- [ ] Logs show `STALE_CANDLES_REJECTED` errors when strategies try to use old candles
- [ ] NO signals generated with price 2650
- [ ] NO XAU_USD signals generated at all (if XAU_USD removed from configs)
- [ ] EUR_USD signals use real-time prices (around 1.085, not stale)
- [ ] Price sanity blocks drop to near-zero
- [ ] Actual trades execute successfully

## 📋 ROOT CAUSE SUMMARY

1. **OANDA API returns stale candles** (or system has cached old responses)
2. **Strategies use candle data** without validating freshness
3. **Entry prices calculated from stale candles** instead of real-time market_data
4. **Price sanity check works correctly** - blocks dangerous trades ✅
5. **System can't trade** because all signals are invalid

## 🎯 PERMANENT SOLUTION

1. ✅ `get_candles()` now rejects stale data (FIXED)
2. ⚠️ Strategies need to be updated to ONLY use `market_data` bid/ask for entry prices
3. ⚠️ Remove XAU_USD from ALL account configurations
4. ⚠️ Force cache clear and restart to load new code

---

**STATUS**: Partial fix deployed, requires manual cache clear + restart to take effect
