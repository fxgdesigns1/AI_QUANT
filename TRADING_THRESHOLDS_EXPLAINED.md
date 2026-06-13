# Trading Thresholds & Safety Rules

**Date:** 2026-01-20  
**Status:** STRICT ALIGNMENT ENFORCED ✅

## 🚨 Safety Rule: Daily Bias MUST Be Directional

**CRITICAL:** The system will **NOT trade** if daily bias is NEUTRAL, even if weekly is BULLISH/BEARISH.

**Reason:** Trading without clear daily momentum is dangerous. We require alignment on BOTH timeframes.

## 📊 Gold (XAU_USD) Trading Thresholds

### Outlook Engine Thresholds (for bias classification):

1. **Minimum Move for BULLISH/BEARISH:**
   - **0.8%** move required to classify as BULLISH or BEARISH
   - Moves below 0.8% are classified as **NEUTRAL** (blocks trading)

2. **Confidence Levels:**
   - **HIGH confidence:** 1.5%+ move
   - **MEDIUM confidence:** 1.2%+ move (0.8% × 1.5)
   - **LOW confidence:** 0.8% - 1.2% move

### What This Means for Trading:

**To allow trading for gold:**
- Daily price must move **at least 0.8%** from yesterday's close
- This gives daily bias = BULLISH or BEARISH (not NEUTRAL)
- Weekly bias must also be BULLISH or BEARISH (aligned with daily)
- All other filters must pass (regime, EMA, session, news)

**Example Scenarios:**

| Gold Move | Daily Bias | Weekly Bias | Can Trade? | Reason |
|-----------|------------|-------------|------------|--------|
| +1.80% | BULLISH (HIGH) | BULLISH | ✅ YES | Both aligned, strong move |
| +0.9% | BULLISH (LOW) | BULLISH | ✅ YES | Both aligned, above threshold |
| +0.5% | NEUTRAL | BULLISH | ❌ NO | Daily too weak (< 0.8%) |
| +1.20% | BULLISH (MEDIUM) | NEUTRAL | ❌ NO | Weekly not directional |
| +1.50% | BULLISH (HIGH) | BEARISH | ❌ NO | Misaligned directions |

## 📊 FX Pairs (EUR_USD, GBP_USD, etc.) Thresholds

**Minimum Move for BULLISH/BEARISH:**
- **0.3%** move required (tighter than gold, as FX moves in smaller % terms)

**Confidence Levels:**
- **HIGH confidence:** 0.7%+ move
- **MEDIUM confidence:** 0.45%+ move (0.3% × 1.5)
- **LOW confidence:** 0.3% - 0.45% move

## ✅ Current Safety Rules

1. **Daily bias MUST be BULLISH or BEARISH** (NEUTRAL blocks trading)
2. **Weekly bias MUST be BULLISH or BEARISH** (NEUTRAL blocks trading)
3. **Daily and weekly MUST match** (both BULLISH or both BEARISH)
4. **Gold requires 0.8%+ move** to get directional daily bias
5. **FX requires 0.3%+ move** to get directional daily bias

## 🔍 How to Check Current State

```bash
# Check latest daily outlook for gold
cat runtime/outlook_daily.json | python3 -m json.tool | grep -A 10 "XAU_USD"

# Check if 006 can trade (alignment check)
python3 debug_006.py
```

## ⚠️ Important Notes

- **0.8% is the MINIMUM** for gold to get a directional bias
- Moves below 0.8% are **NEUTRAL** and **block trading**
- A 1.80% move is **well above threshold** and gets **HIGH confidence BULLISH**
- The system is **fail-closed**: if daily is NEUTRAL, trading is blocked regardless of weekly bias
