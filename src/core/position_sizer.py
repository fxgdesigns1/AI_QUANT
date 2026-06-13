"""
Canonical position sizer for FXG. Single source of truth for lot calculation and SL validation.
Import calculate_lots() everywhere. Never duplicate this logic in any other file.

FXG FIX 2026-06-12: added champion cross pairs (AUD_CHF, EUR_AUD, EUR_NZD,
GBP_AUD, NZD_JPY) that were rejected as "Unknown instrument" and produced
0.00-lot champion cards. Minimum SL distances aligned to champion ATR stops:
3 pips forex (was 5), 3 pips JPY (was 10), $1.50 XAUUSD (was $3.00).
Incident cases (sub-pip SLs) remain hard-blocked; max-lot caps unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

FOREX_STANDARD = frozenset([
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCHF",
    "USDCAD", "EURGBP", "EURCHF", "GBPCHF", "EURCAD",
    # Champion cross pairs (quote treated 1:1 with USD, same convention as EURCHF/GBPCHF).
    # AUD/NZD-quoted pairs over-estimate risk-per-lot slightly -> conservative sizing.
    "AUDCHF", "EURAUD", "EURNZD", "GBPAUD", "AUDNZD", "GBPNZD",
])
FOREX_JPY = frozenset([
    "USDJPY", "GBPJPY", "EURJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
])


@dataclass
class SizingResult:
    lots: float
    raw_lots: float
    capped: bool
    sl_distance: float
    risk_per_lot: float
    risk_usd: float
    valid: bool
    rejection_reason: str = ""
    warning: str = ""


def _clean(symbol: str) -> str:
    return symbol.upper().replace("_", "")


def _reject(sl_dist: float, rpl: float, risk: float, reason: str) -> SizingResult:
    return SizingResult(
        lots=0.0, raw_lots=0.0, capped=False,
        sl_distance=sl_dist, risk_per_lot=rpl, risk_usd=risk,
        valid=False, rejection_reason=reason,
    )


def calculate_lots(
    symbol: str,
    entry: float,
    stop_loss: float,
    risk_usd: float = 300.0,
) -> SizingResult:
    """
    Calculate and validate lot size for a fixed-risk trade.
    Returns valid=False with rejection_reason if the setup must be rejected.
    Returns capped=True with warning if lots were hard-capped.
    A rejection cannot be bypassed. A cap produces a warning only.
    """
    sym = _clean(symbol)
    entry = float(entry)
    stop_loss = float(stop_loss)
    risk_usd = float(risk_usd)
    sl_distance = abs(entry - stop_loss)

    if sl_distance <= 0.0:
        return _reject(sl_distance, 0.0, risk_usd, "SL at or beyond entry")

    if sym == "XAUUSD":
        risk_per_lot = sl_distance * 100.0
        min_sl = 1.50
        max_lots = 0.5
        too_tight = sl_distance < min_sl
        tight_msg = f"SL too tight: ${sl_distance:.2f} < $1.50 minimum"
    elif sym == "XAGUSD":
        risk_per_lot = sl_distance * 5000.0
        min_sl = 0.10
        max_lots = 0.5
        too_tight = sl_distance < min_sl
        tight_msg = f"SL too tight: ${sl_distance:.4f} < $0.10 minimum"
    elif sym in FOREX_JPY:
        risk_per_lot = sl_distance * (100_000.0 / 150.0)
        min_sl = 0.030
        max_lots = 2.0
        too_tight = sl_distance < min_sl
        actual_pips = round(sl_distance / 0.01, 1)
        tight_msg = f"SL too tight: {actual_pips} pips < 3 pip minimum"
    elif sym in FOREX_STANDARD:
        risk_per_lot = sl_distance * 100_000.0
        min_sl = 0.00030
        max_lots = 2.0
        too_tight = sl_distance < min_sl
        actual_pips = round(sl_distance / 0.0001, 1)
        tight_msg = f"SL too tight: {actual_pips} pips < 3 pip minimum"
    else:
        return _reject(sl_distance, 0.0, risk_usd, f"Unknown instrument: {symbol}")

    if too_tight:
        return _reject(sl_distance, risk_per_lot, risk_usd, tight_msg)

    raw_lots = risk_usd / risk_per_lot
    rounded = max(round(raw_lots, 2), 0.01)

    capped = rounded > max_lots
    final_lots = max_lots if capped else rounded
    warning = f"Lots capped: {rounded:.2f} → {max_lots:.2f} (max for {sym})" if capped else ""

    return SizingResult(
        lots=final_lots,
        raw_lots=raw_lots,
        capped=capped,
        sl_distance=sl_distance,
        risk_per_lot=risk_per_lot,
        risk_usd=risk_usd,
        valid=True,
        warning=warning,
    )


if __name__ == "__main__":
    import sys
    PASS = "\033[32mPASS\033[0m"
    FAIL = "\033[31mFAIL\033[0m"
    failures = 0

    def check(name: str, r: SizingResult, *, valid: bool, capped: bool = False, lots: float | None = None, tol: float = 0.015) -> None:
        global failures
        ok = True
        if r.valid != valid:
            print(f"{FAIL} {name}: valid={r.valid} expected {valid}  [{r.rejection_reason or r.warning}]")
            ok = False
        if r.capped != capped:
            print(f"{FAIL} {name}: capped={r.capped} expected {capped}")
            ok = False
        if lots is not None and abs(r.lots - lots) > tol:
            print(f"{FAIL} {name}: lots={r.lots:.4f} expected ~{lots:.4f}")
            ok = False
        if ok:
            print(f"{PASS} {name}: lots={r.lots:.2f} valid={r.valid} capped={r.capped}  [{r.rejection_reason or r.warning or 'ok'}]")
        else:
            failures += 1

    # --- Incident-class cases: sub-minimum SLs must be BLOCKED ---
    # (Legacy cases used 3-4 pip distances, blocked by the old 5-pip minimum.
    #  Policy is now 3 pips; the guarantee under test is "below minimum = rejected".)
    check("NZDUSD 2pip",    calculate_lots("NZDUSD", 0.59543, 0.59563), valid=False)
    check("USDCHF 2pip",    calculate_lots("USDCHF", 1.00000, 1.00020), valid=False)
    check("AUDUSD 2pip",    calculate_lots("AUDUSD", 0.64500, 0.64520), valid=False)
    check("USDCHF 4pip ok", calculate_lots("USDCHF", 1.00000, 1.00040), valid=True, capped=True, lots=2.0)

    # --- Below 3-pip minimum: still BLOCKED ---
    check("EURUSD 2pip",    calculate_lots("EURUSD", 1.08500, 1.08480), valid=False)
    check("AUDCHF 2pip",    calculate_lots("AUD_CHF", 0.58500, 0.58480), valid=False)
    check("USDJPY 2pip",    calculate_lots("USDJPY", 155.000, 155.020), valid=False)

    # --- Valid forex standard ---
    check("EURUSD 100pip",  calculate_lots("EURUSD", 1.16000, 1.15000), valid=True, lots=0.30)
    check("GBPUSD 50pip",   calculate_lots("GBPUSD", 1.27000, 1.26500), valid=True, lots=0.60)

    # --- Champion cross pairs (previously Unknown instrument -> 0.00 lots) ---
    check("AUDCHF 3.9pip",  calculate_lots("AUD_CHF", 0.58500, 0.58461), valid=True, capped=True, lots=2.0)
    check("EURAUD 20pip",   calculate_lots("EUR_AUD", 1.66000, 1.65800), valid=True, lots=1.50)
    check("EURNZD 25pip",   calculate_lots("EUR_NZD", 1.79000, 1.78750), valid=True, lots=1.20)
    check("GBPAUD 30pip",   calculate_lots("GBP_AUD", 2.06000, 2.05700), valid=True, lots=1.00)
    check("NZDJPY 30pip",   calculate_lots("NZD_JPY", 89.500, 89.200), valid=True, lots=1.50)

    # --- JPY valid ---
    check("GBPJPY 150pip",  calculate_lots("GBPJPY", 196.000, 194.500), valid=True)
    check("USDJPY 20pip",   calculate_lots("USDJPY", 155.000, 154.800), valid=True, capped=True, lots=2.0)
    check("AUDJPY 30pip",   calculate_lots("AUD_JPY", 98.500, 98.200), valid=True, lots=1.50)

    # --- XAUUSD ---
    check("XAUUSD valid",   calculate_lots("XAUUSD", 4495.48, 4503.76), valid=True, lots=0.36)
    check("XAUUSD $1 SL",  calculate_lots("XAUUSD", 4495.48, 4496.48), valid=False)
    check("XAUUSD $2 SL",  calculate_lots("XAUUSD", 4495.48, 4497.48), valid=True, capped=True, lots=0.5)

    # --- XAGUSD ---
    check("XAGUSD valid",   calculate_lots("XAGUSD", 32.000, 31.900), valid=True, capped=True, lots=0.5)
    check("XAGUSD tight",   calculate_lots("XAGUSD", 32.000, 31.995), valid=False)

    # --- Hard cap ---
    check("EURUSD 5pip cap", calculate_lots("EURUSD", 1.10000, 1.09950), valid=True, capped=True, lots=2.0)
    check("XAUUSD cap",      calculate_lots("XAUUSD", 2000.00, 2005.00), valid=True, capped=True, lots=0.5)

    # --- SL on entry ---
    check("SL=entry",        calculate_lots("EURUSD", 1.10000, 1.10000), valid=False)

    # --- Unknown symbol ---
    check("BTCUSD unknown",  calculate_lots("BTCUSD", 50000, 49000), valid=False)

    sys.exit(1 if failures else 0)
