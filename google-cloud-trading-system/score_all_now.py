#!/usr/bin/env python3
import sys, math, logging
sys.path.insert(0, '.')
from datetime import datetime
from typing import List, Dict, Tuple

from src.core.dynamic_account_manager import get_account_manager
from src.strategies.momentum_trading import get_momentum_trading_strategy

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

INSTRUMENTS = ['XAU_USD','GBP_USD','EUR_USD','USD_JPY','AUD_USD','NZD_USD','USD_CAD']
GRANULARITY = 'M5'
CANDLES = 200
ADX_PERIOD = 14
MOMENTUM_PERIOD = 40


def compute_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 2:
        return 0.0
    plus_dm = []
    minus_dm = []
    tr = []
    for i in range(1, len(closes)):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        plus_dm.append(max(up_move, 0.0) if up_move > down_move else 0.0)
        minus_dm.append(max(down_move, 0.0) if down_move > up_move else 0.0)
        tr_i = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr.append(tr_i)
    # Wilder's smoothing
    def wilder_smooth(values: List[float], period: int) -> List[float]:
        if len(values) < period:
            return []
        smoothed = [sum(values[:period])]
        for v in values[period:]:
            smoothed.append(smoothed[-1] - (smoothed[-1] / period) + v)
        return smoothed
    tr_s = wilder_smooth(tr, period)
    pdm_s = wilder_smooth(plus_dm, period)
    mdm_s = wilder_smooth(minus_dm, period)
    if not tr_s or not pdm_s or not mdm_s:
        return 0.0
    di_plus = [0.0]*len(tr_s)
    di_minus = [0.0]*len(tr_s)
    for i in range(len(tr_s)):
        if tr_s[i] == 0:
            di_plus[i] = 0.0
            di_minus[i] = 0.0
        else:
            di_plus[i] = 100.0 * (pdm_s[i] / tr_s[i])
            di_minus[i] = 100.0 * (mdm_s[i] / tr_s[i])
    dx = []
    for i in range(len(di_plus)):
        denom = (di_plus[i] + di_minus[i])
        if denom == 0:
            dx.append(0.0)
        else:
            dx.append(100.0 * abs(di_plus[i] - di_minus[i]) / denom)
    # ADX as Wilder's smoothing of DX
    adx_series = wilder_smooth(dx, period)
    if not adx_series:
        return 0.0
    return adx_series[-1] / period  # finalize per Wilder averaging


def compute_momentum_pct(closes: List[float], period: int = 40) -> float:
    if len(closes) < period + 1:
        return 0.0
    prev = closes[-period-1]
    last = closes[-1]
    if prev <= 0:
        return 0.0
    return (last - prev) / prev


def compute_volume_score_from_range(highs: List[float], lows: List[float]) -> float:
    # Proxy: average true range percentage over last 20 bars
    n = min(20, len(highs))
    if n < 2:
        return 0.0
    trs = [(highs[-i] - lows[-i]) / max(1e-9, highs[-i]) for i in range(1, n+1)]
    avg = sum(trs) / len(trs)
    # Map to 0..1 roughly (0%..0.5%)
    return max(0.0, min(1.0, avg / 0.005))


def main():
    print("== QUALITY SCORES (LIVE FETCH) ==")
    print(f"Time (London): {datetime.utcnow().strftime('%H:%M:%S')}\n")
    mgr = get_account_manager()
    active = mgr.get_active_accounts()
    if not active:
        print("CRITICAL: No active OANDA accounts available to fetch candles.")
        return
    client = mgr.get_account_client(active[0])
    strat = get_momentum_trading_strategy()
    results: List[Tuple[str, float, float, float, float, str, float, bool]] = []
    for inst in INSTRUMENTS:
        try:
            raw = client.get_candles(inst, granularity=GRANULARITY, count=CANDLES, price='M')
            candles = raw.get('candles', [])
            highs = [float(c['mid']['h']) for c in candles if c.get('complete')]
            lows = [float(c['mid']['l']) for c in candles if c.get('complete')]
            closes = [float(c['mid']['c']) for c in candles if c.get('complete')]
            if len(closes) < 50:
                print(f"{inst}: insufficient candles fetched ({len(closes)})")
                continue
            adx = compute_adx(highs, lows, closes, ADX_PERIOD)
            momentum = compute_momentum_pct(closes, MOMENTUM_PERIOD)
            vol_score = compute_volume_score_from_range(highs, lows)
            prices = closes[-50:]
            # regime classification
            if adx >= 25:
                regime = {'regime': 'TRENDING'}
            elif adx >= 15:
                regime = {'regime': 'RANGING'}
            else:
                regime = {'regime': 'CHOPPY'}
            qr = strat._calculate_adaptive_quality_score(inst, adx, momentum, vol_score, prices, regime, None)
            results.append((inst, qr['score'], qr['threshold'], adx, momentum, regime['regime'], vol_score, qr['passes']))
        except Exception as e:
            print(f"{inst}: error: {e}")
    # Print summary
    for inst, score, th, adx, mom, reg, vol, passed in results:
        print(f"{inst}: quality {score:.1f}/{th:.0f} | ADX {adx:.1f} | momentum {mom:.4f} | regime {reg} | vol_score {vol:.2f} | {'PASS' if passed else 'REJECT'}")

if __name__ == '__main__':
    main()
