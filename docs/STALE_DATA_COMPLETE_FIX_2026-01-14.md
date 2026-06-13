# STALE DATA ROOT CAUSE & COMPLETE FIX
## 2026-01-14T18:20:00Z

## CRITICAL FINDINGS

### Root Cause Confirmed

**ALL STRATEGIES are generating signals using STALE OANDA CANDLE DATA from weeks/months ago:**

1. Current XAU_USD market price: **$4,627**
2. Signal entry price: **$2,650** (from OLD candle data)
3. Deviation: **42.8%** - correctly blocked by price sanity check
4. **400+ blocks** on accounts 004 and 005

### The Broken Architecture

**Problem**: Strategies call `get_candles(instrument)` which fetches from OANDA with NO freshness validation. If OANDA returns old cached data or if the request returns stale candles, the strategy uses them blindly.

**File Affected**:
- `momentum_trading.py` ✅ FIXED (but not loaded due to Python cache)
- `momentum_v2.py` ⚠️ PARTIALLY FIXED (syntax issues)
- `range_trading.py` ⚠️ PARTIALLY FIXED (syntax issues)
- `gold_scalping.py` ❌ BROKEN (hardcoded `instrument='XAU_USD'` + syntax errors from auto-fix)

## THE REAL ISSUE: gold_scalping.py

This strategy has **HARDCODED** `instrument='XAU_USD'` on line 214:

```python
signal = TradeSignal(
    instrument='XAU_USD',  # ← HARDCODED!!!
    side=TradeSide.BUY,
    entry_price=entry_price,  # ← Uses bid/ask from market_data loop (EUR_USD!)
    ...
)
```

But it loops through `market_data` which contains EUR_USD, so:
- It extracts EUR_USD's bid/ask
- Fetches XAU_USD candles (which are STALE)
- Generates signal with instrument=XAU_USD but using wrong price source

## WHY THE FIX DIDN'T LOAD

1. Python bytecode cache (`.pyc`) holds old module in memory
2. `pkill -9` killed SSH session before completing restart
3. Automated regex-based fix created syntax errors in gold_scalping.py

## REQUIRED ACTIONS

### 1. Fix gold_scalping.py Properly

**Change line 214** from:
```python
instrument='XAU_USD',  # HARDCODED
```

To:
```python
instrument=instrument,  # Use variable from market_data loop
```

BUT WAIT - `gold_scalping.py` doesn't loop through market_data! It directly gets:
```python
xau_data = market_data.get('XAU_USD')
```

So the variable `instrument` doesn't exist in that scope! The fix is:

```python
instrument = 'XAU_USD'  # Set explicitly for this single-instrument strategy
# ... later ...
signal = TradeSignal(
    instrument=instrument,  # Now uses variable
    ...
)
```

### 2. Complete Strategy Rewrite Plan

Since automated fixes broke things, I need to:

1. **MANUALLY rewrite each strategy's analyze_market method** with:
   - Candle freshness validation (reject if > 30min old)
   - Entry price sanity check (reject if > 5% deviation from mid)
   - Enhanced logging (show candle age, deviation %)
   
2. **For gold_scalping.py specifically**:
   - Keep single-instrument design but add all validations
   - Ensure `instrument` variable is defined
   - Fix indentation issues from automated patches

3. **Clear Python cache completely**:
   ```bash
   sudo systemctl stop ai-quant-runner
   find ~/gcloud-system -name '*.pyc' -delete
   find ~/gcloud-system -type d -name '__pycache__' -exec rm -rf {} +
   sudo systemctl start ai-quant-runner
   ```

### 3. Add Strategy Base Class (Future-Proof)

Create `src/strategies/base_strategy.py` with:
- `validate_candle_freshness(candles, max_age_seconds)`
- `validate_entry_price(entry_price, mid, max_deviation_pct)`
- `safe_get_candles(instrument, ...) -> raises on stale data`

All strategies MUST inherit from this and use the safe methods.

## STATUS

- ❌ **BLOCKED**: Current strategies have syntax errors + Python cache issues
- ⚠️ **URGENT**: Need manual fix + forced cache clear + restart
- 📊 **Evidence**: 400+ blocks, 0 successful trades

## NEXT STEPS

1. Manually fix `gold_scalping.py` (remove hardcoded instrument, fix syntax)
2. Verify all 4 strategies have valid Python syntax
3. Force complete cache clear (kill processes, delete .pyc, restart)
4. Monitor logs for `STALE_CANDLES` warnings (should appear if working)
5. Verify blocks drop to 0 and trades execute

---

**User Request**: "NEVER FUCKING HARDCODED PRICES" - ✅ ACKNOWLEDGED

The 2650 price is NOT in source code, it's from STALE OANDA API DATA that needs validation.
