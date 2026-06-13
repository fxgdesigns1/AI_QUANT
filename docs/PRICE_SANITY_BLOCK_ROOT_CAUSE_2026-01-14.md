# Price Sanity Block Root Cause Analysis
## 2026-01-14T17:09:00Z

### Problem Summary

System experiencing **400+ price sanity blocks per account** preventing XAU_USD trades from executing.

**Symptoms**:
- XAU_USD signals generated with entry price `2650.50`
- Current market price: `4618`  
- Stop loss: `2645.50` (entry - 5.0)
- Deviation: `42.63%` vs threshold `1.00%`
- Result: **PRICE_SANITY_BLOCK stop_too_far**

### Root Cause Identified

**CRITICAL BUG**: Strategy is generating XAU_USD signals using **EUR_USD price data**

#### Evidence

From runner logs at `2026-01-14T17:04:39Z`:
```
📊 Generated BUY signal: XAU_USD @ 2650.50000 (confidence: 0.55)
STRAT_EVIDENCE system=ALPHA account=001 strategy=momentum instrument=EUR_USD price_mid=1.08510 ...
```

**Mismatch**:
- Signal generated for: `XAU_USD`
- Price data used: `EUR_USD` (mid=1.08510)
- Signal entry price: `2650.50` ← **Not from any current market data**

#### Explanation

The `momentum_trading.py` strategy does:

1. Iterates through `market_data.items()` (e.g., EUR_USD with price 1.085)
2. For EACH instrument in market_data, calls `get_candles(instrument)` to fetch historical candles
3. **BUG**: When XAU_USD is in the configured instruments list, it fetches XAU_USD candles
4. Calculates indicators from XAU_USD candles (which may be OLD/cached)
5. Uses the last candle close price (`~2650`) as a pseudo "current price"
6. But then uses EUR_USD's `ask` from `market_data` for `entry_price`
7. Result: Signal says XAU_USD @ 2650 but uses EUR_USD's spread/price

Actually, re-examining the code flow:
- Line 107-110: `for instrument, price_data in market_data.items():`
- Line 111-113: Extracts `bid`, `ask` from `price_data`
- Line 139: `candles = get_candles(instrument, ...)`  ← Fetches candles for the SAME instrument
- Line 215: `entry_price = ask` ← Should be using the correct ask price

**Wait - deeper issue**: The entry price `2650.50` suggests that somewhere the candle's close price is being used instead of `ask`. Let me trace this more carefully...

### Actual Root Cause (Revised)

Looking at the logs, `STRAT_EVIDENCE` shows `instrument=EUR_USD` but the signal is for `XAU_USD`. This means:

1. The strategy is configured with instruments like `["EUR_USD", "GBP_USD", ...]`
2. `market_data` contains prices for those instruments only
3. But INSIDE the strategy, `get_candles()` is being called for **a different instrument** (XAU_USD)
4. The candle fetch succeeds (XAU_USD historical data)
5. The signal is generated using XAU_USD candles but EUR_USD's bid/ask

**OR** - there's a simpler explanation:

The strategy is using **old/cached candle data** where XAU_USD was around 2650 (this could be from days/weeks ago when gold prices were lower), and the `get_candles()` call is returning stale data OR there's no validation that the candles are fresh.

### Hypothesis: Stale Candle Data

XAU_USD real-time price: **$4618**  
XAU_USD signal entry price: **$2650**  

Price difference: **$1968** (42.6%)

This suggests the candles fetched are from **weeks or months ago** when gold was at $2650 levels.

### Fix Required

**Option 1**: Add candle freshness validation
- Check the timestamp of the latest candle
- Reject if older than N minutes (e.g., 30 minutes)

**Option 2**: Use current market price for entry, not candle close
- Candles should ONLY be for indicator calculation
- Entry price MUST come from real-time `market_data` ask/bid

**Option 3** (RECOMMENDED): Both
1. Validate candle freshness
2. Ensure entry_price uses `market_data` ask, NOT candle close
3. Add assertion: `abs(entry_price - mid) / mid < 0.05` (5% sanity check)

### Immediate Action Required

1. **Add diagnostic logging** to strategy to log:
   - Candle timestamps (first and last)
   - Entry price source (bid/ask from market_data vs candle)
   - Price deviation between entry and current market mid

2. **Add candle freshness check**:
   ```python
   latest_candle_time = datetime.fromisoformat(candles[-1].time.replace('Z', '+00:00'))
   age_seconds = (datetime.now(timezone.utc) - latest_candle_time).total_seconds()
   if age_seconds > 1800:  # 30 minutes
       logger.warning(f"STALE_CANDLES instrument={instrument} age_seconds={age_seconds}")
       continue
   ```

3. **Add entry price validation**:
   ```python
   entry_price = ask
   deviation_pct = abs(entry_price - mid) / mid * 100
   if deviation_pct > 5.0:
       logger.error(f"ENTRY_PRICE_SANITY instrument={instrument} entry={entry_price} mid={mid} dev_pct={deviation_pct}")
       continue
   ```

### Status

- ❌ **BLOCKED**: Trading cannot proceed with 42% price deviations
- ⚠️ **URGENT**: Fix required before system can operate smoothly
- 📊 **Evidence**: 400+ blocks on accounts 004 and 005

---

**Next Step**: Implement candle freshness validation and entry price sanity check in `momentum_trading.py`
