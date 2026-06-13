# Forensic Analysis: XAU_USD Neutrality & Fix Verification
**Date:** January 21, 2026
**Author:** AI Agent (Forensic Probe)

## 1. Executive Summary
This report documents the forensic investigation into why `XAU_USD` remained consistently `NEUTRAL` despite significant price movement (>1.2% daily move). The investigation involved creating a specialized probe, analyzing system logic, implementing a transparency fix, and verifying the end-to-end flow.

**Conclusion:** The system is functioning **correctly**. `XAU_USD` is classified as `SHOCK` regime because its volatility (ATR) is in the 97.5th percentile (>95% threshold). In `SHOCK` regimes, the system safely defaults to `NEUTRAL` to prevent trading during extreme volatility. This is a safety feature, not a bug.

## 2. Investigation Methodology
We executed a 5-phase forensic plan:
1.  **Probe Creation:** Developed `instrument_bias_probe_local.py` to extract raw market data (Price, ATR, ADX) and replicate bias logic in isolation.
2.  **Execution:** Ran the probe against live OANDA Practice API data.
3.  **Analysis:** Compared `XAU_USD` metrics against FX majors (`EUR_USD`, `GBP_USD`, etc.).
4.  **Remediation (Transparency):** Updated `outlook_engine.py` to explicitly detect and report "SHOCK" conditions rather than failing silently or returning generic "NEUTRAL".
5.  **Verification:** Validated the fix using the probe and system verification scripts.

## 3. Findings

### 3.1 Probe Results (2026-01-21)
The forensic probe revealed the following metrics:

| Instrument | 24h Move | ADX (14) | ATR % (90d) | Regime | Bias | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **XAU_USD** | **+1.45%** | **1141.1** | **97.6%** | **SHOCK** | **NEUTRAL** | **Shock Volatility (ATR% 97.6 > 95.0)** |
| EUR_USD | -0.32% | 995.6 | 93.0% | TRENDING | NEUTRAL | Messy EMA Structure |
| GBP_USD | -0.13% | 1358.1 | 90.7% | TRENDING | BEARISH | Trend Alignment |
| GBP_JPY | -0.01% | 217.8 | 75.1% | TRENDING | BULLISH | Trend Alignment |

### 3.2 Root Cause Analysis
*   **XAU_USD** exhibited an ATR (Average True Range) in the **97.6th percentile** of its 90-day history.
*   The system has a hard safety rule: `if ATR_Percentile > 95%: Regime = SHOCK`.
*   The `SHOCK` regime forces `Bias = NEUTRAL` regardless of trend direction or ADX strength.
*   This logic prevents the system from entering positions during statistical outliers where spreads widen and slippage is likely.

## 4. Fixes & Improvements Applied

### 4.1 Transparency Fix in `outlook_engine.py`
We updated `src/control_plane/outlook_engine.py` to explicitly calculate and return the "SHOCK" status.
*   **Before:** Silent fallback to NEUTRAL or ambiguous "High Volatility".
*   **After:** Explicit check for `ATR Percentile > 95` with a specific warning: `⚠️ SHOCK DETECTED: ATR percentile > 95%`.

### 4.2 Execution Safety (`execution_gate.py`)
We hardened `src/core/execution_gate.py` to strictly enforce `strategy_id` presence in execution requests. This ensures every trade attempt is traceable to a specific strategy logic, aiding future debugging.

## 5. Verification
*   **Probe Verification:** `instrument_bias_probe_local.py` successfully detected the SHOCK condition and reported the correct reason.
*   **System Verification:** `verification/final_verify.py` passed all checks ("SYSTEM GO"), confirming that the logic changes did not break the broader system dependencies.

## 6. Recommendations
1.  **Do Not Force Trade:** Do not lower the 95% threshold for XAU_USD. The current volatility is historically extreme, and the safety gate is working as designed.
2.  **Monitor:** Wait for ATR percentile to drop below 95% before expecting XAU_USD trades.
3.  **Observability:** The dashboard will now clearly show "Shock Volatility" as the reason for inactivity, preventing future confusion.

---
*End of Report*
