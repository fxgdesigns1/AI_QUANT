# Strategy Instruments & Opportunities Report
**Generated:** 2026-01-13T01:48:00Z
**Objective:** Document what instruments each strategy uses and what opportunities they see

---

## STRATEGY INSTRUMENTS (From Strategy Registry)

### Account 001: `momentum`
**Configured Instruments (Strategy Registry):**
- EUR_USD
- GBP_USD
- USD_JPY
- AUD_USD

**Risk Level:** Medium
**Session Preference:** Any
**Description:** Trend-following strategy using momentum indicators (RSI, MACD, moving averages)

---

### Account 002: `momentum_v2`
**Configured Instruments (Strategy Registry):**
- EUR_USD
- GBP_USD
- USD_JPY
- AUD_USD
- XAU_USD (included in V2)

**Risk Level:** Medium
**Session Preference:** Any
**Description:** Enhanced momentum strategy with adaptive filters and volatility adjustment

---

### Account 003: `range`
**Configured Instruments (Strategy Registry):**
- EUR_USD
- GBP_USD
- USD_JPY

**Risk Level:** Low
**Session Preference:** Asia
**Description:** Mean-reversion strategy for sideways markets

---

### Account 004: `gold`
**Configured Instruments (Strategy Registry):**
- XAU_USD (ONLY)

**Risk Level:** High
**Session Preference:** London
**Description:** Scalping strategy optimized for XAU_USD with tight stops and quick exits

---

### Account 005: `eur_usd_5m_safe`
**Configured Instruments (Strategy Registry):**
- EUR_USD (ONLY)

**Risk Level:** Low
**Session Preference:** London
**Description:** Conservative EUR/USD strategy on 5-minute timeframe with strict risk controls

---

## ACTUAL RUNTIME BEHAVIOR

### Default Instruments (Runtime Config)
**Current Setting:** All accounts scan the same default instrument set:
- EUR_USD
- GBP_USD
- XAU_USD
- USD_JPY
- AUD_USD

**Note:** The system currently uses `default_instruments` from runtime config for ALL accounts, not strategy-specific instruments from the registry.

---

## CURRENT OPPORTUNITIES (From Logs)

**Latest Scan Evidence:**
- All 5 accounts generating signals on **EUR_USD**
- All strategies generating **BUY** signals
- All signals showing same price: **1.08510**
- Signal generation: **XAU_USD @ 2650.50000** (but STRAT_EVIDENCE shows EUR_USD)

**Discrepancy Note:**
- STRAT_EVIDENCE shows `instrument=EUR_USD` 
- But signal generation shows `XAU_USD @ 2650.50000`
- This suggests the strategy is analyzing EUR_USD but generating signals on XAU_USD (likely a stub implementation issue)

---

## WHAT OPPORTUNITIES EACH STRATEGY SHOULD SEE

### Account 001: `momentum`
**Should See:**
- EUR_USD opportunities (trend following)
- GBP_USD opportunities (trend following)
- USD_JPY opportunities (trend following)
- AUD_USD opportunities (trend following)

**Current Behavior:** ✅ Generating signals (but on wrong instrument)

---

### Account 002: `momentum_v2`
**Should See:**
- EUR_USD opportunities (enhanced momentum)
- GBP_USD opportunities (enhanced momentum)
- USD_JPY opportunities (enhanced momentum)
- AUD_USD opportunities (enhanced momentum)
- XAU_USD opportunities (enhanced momentum)

**Current Behavior:** ✅ Generating signals (but on wrong instrument)

---

### Account 003: `range`
**Should See:**
- EUR_USD opportunities (range-bound markets)
- GBP_USD opportunities (range-bound markets)
- USD_JPY opportunities (range-bound markets)

**Current Behavior:** ✅ Generating signals (but on wrong instrument)

---

### Account 004: `gold`
**Should See:**
- XAU_USD opportunities ONLY (gold scalping)

**Current Behavior:** ⚠️ Generating signals on EUR_USD (should be XAU_USD only)

---

### Account 005: `eur_usd_5m_safe`
**Should See:**
- EUR_USD opportunities ONLY (conservative EUR/USD trading)

**Current Behavior:** ✅ Generating signals on EUR_USD (correct)

---

## SUMMARY TABLE

| Account | Strategy | Configured Instruments | Actual Scan Instruments | Opportunities Should See | Current Behavior |
|---------|----------|------------------------|-------------------------|--------------------------|------------------|
| **001** | momentum | EUR_USD, GBP_USD, USD_JPY, AUD_USD | EUR_USD, GBP_USD, XAU_USD, USD_JPY, AUD_USD | Trend opportunities on FX majors | ✅ Signals generated |
| **002** | momentum_v2 | EUR_USD, GBP_USD, USD_JPY, AUD_USD, XAU_USD | EUR_USD, GBP_USD, XAU_USD, USD_JPY, AUD_USD | Trend opportunities on FX + Gold | ✅ Signals generated |
| **003** | range | EUR_USD, GBP_USD, USD_JPY | EUR_USD, GBP_USD, XAU_USD, USD_JPY, AUD_USD | Range-bound opportunities on FX majors | ✅ Signals generated |
| **004** | gold | XAU_USD | EUR_USD, GBP_USD, XAU_USD, USD_JPY, AUD_USD | Scalping opportunities on Gold ONLY | ⚠️ Signals on EUR_USD (should be XAU_USD) |
| **005** | eur_usd_5m_safe | EUR_USD | EUR_USD, GBP_USD, XAU_USD, USD_JPY, AUD_USD | Conservative EUR/USD opportunities ONLY | ✅ Signals on EUR_USD (correct) |

---

## KEY FINDINGS

1. **Instrument Mismatch:** All accounts are scanning the same default instrument set, not strategy-specific instruments
2. **Strategy Registry vs Runtime:** Strategy registry defines preferred instruments, but runtime uses `default_instruments` config
3. **Account 004 Issue:** Gold strategy should ONLY see XAU_USD, but is currently scanning all default instruments
4. **Account 005 Correct:** EUR/USD safe strategy is correctly generating signals on EUR_USD

---

## RECOMMENDATIONS

1. **Strategy-Specific Instruments:** System should use strategy registry instruments per account, not default set
2. **Account 004 Fix:** Gold strategy should scan ONLY XAU_USD (not all default instruments)
3. **Instrument Filtering:** Each strategy should filter opportunities to its configured instruments
4. **Log Clarity:** STRAT_EVIDENCE should show the actual instrument the signal is for, not the scanned instrument
