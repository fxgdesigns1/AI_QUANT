# Outlook Engine Bias Detection Fix - COMPLETE ✅

**Date:** 2026-01-20 17:40 UTC  
**Status:** FIXED & VERIFIED

## 🚨 Critical Issue Found

**Problem:** Outlook engine was misclassifying strong directional moves as NEUTRAL.

**Example:** Gold (XAU_USD) moving **1.80% in a day** was being labeled **NEUTRAL** instead of **BULLISH**.

**Root Cause:**
1. Daily bias used a **5-day lookback** instead of checking TODAY's move
2. Fixed **0.5% threshold** for all instruments (too high for FX, too low sensitivity for gold)
3. No instrument-specific thresholds (gold moves in larger % terms than FX)

## ✅ Fix Applied

### Changes to `src/control_plane/outlook_engine.py`:

1. **Daily Bias Now Uses TODAY's Move:**
   - **Before:** Compared current price to 5 days ago
   - **After:** Compares current price to **yesterday's close** (last complete daily candle)
   - **Result:** Captures strong intraday moves immediately

2. **Instrument-Specific Thresholds:**
   - **Gold/Silver (XAU_USD, XAG_USD):**
     - BULLISH threshold: **0.8%** (was 0.5%)
     - BEARISH threshold: **-0.8%** (was -0.5%)
     - Strong move: **1.5%+** gets HIGH confidence
   - **FX Pairs (EUR_USD, GBP_USD, etc.):**
     - BULLISH threshold: **0.3%** (was 0.5%)
     - BEARISH threshold: **-0.3%** (was -0.5%)
     - Strong move: **0.7%+** gets HIGH confidence

3. **Confidence Levels:**
   - **HIGH:** Strong moves (1.5%+ gold, 0.7%+ FX)
   - **MEDIUM:** Moderate moves (1.2%+ gold, 0.45%+ FX)
   - **LOW:** Small moves or neutral

## ✅ Verification

**Logic Test:**
```
XAU_USD with 1.80% move:
  Threshold: 0.8%
  Result: BULLISH (HIGH confidence) ✅
```

**Before Fix:** 1.80% move → NEUTRAL ❌  
**After Fix:** 1.80% move → BULLISH (HIGH confidence) ✅

## 🚀 Impact on Account 006

**Before:**
- Strong gold moves (1.80%+) labeled NEUTRAL
- Daily bias stayed NEUTRAL even with clear directional moves
- 006 blocked from trading due to "roadmap_misaligned"

**After:**
- Strong gold moves (1.80%+) correctly labeled BULLISH with HIGH confidence
- Daily bias reflects actual market movement
- 006 can now trade when:
  - Weekly bias is BULLISH/BEARISH
  - Daily shows strong move (now correctly classified)
  - Other filters pass (regime, EMA, session, news)

## 📊 Next Steps

1. **Runner Status:** ✅ Running (PID 37210) - will pick up fix on next scan
2. **Outlook Refresh:** Outlooks will regenerate with new logic on next compute cycle
3. **Monitor:** Watch `runtime/outlook_daily.json` and `runtime/outlook_weekly.json` for updated biases

## 🔍 How to Verify Fix is Working

```bash
# Check latest daily outlook
cat runtime/outlook_daily.json | python3 -m json.tool | grep -A 5 "XAU_USD"

# Watch for bias changes during strong moves
tail -f logs/runner.log | grep -E "(outlook|bias|XAU_USD)"
```

## ✅ Summary

- **Fix Status:** DEPLOYED ✅
- **Code Verified:** Logic correctly classifies 1.80% gold move as BULLISH ✅
- **Runner Status:** Active and will use new logic ✅
- **Expected Behavior:** Strong moves now correctly trigger BULLISH/BEARISH bias ✅

The outlook engine will now correctly identify strong directional moves and classify them appropriately, allowing 006 to trade when conditions are met.
