#!/usr/bin/env python3
"""Helper script to extend market_regime.py with daily/weekly support."""

import sys

content = '''import numpy as np
import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    CHOPPY = "CHOPPY"
    UNKNOWN = "UNKNOWN"

class OutlookBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"

@dataclass
class RegimeAnalysis:
    regime: MarketRegime
    adx: float
    consistency: float
    volatility: float
    description: str
    # New fields for daily/weekly
    regime_daily: Optional[MarketRegime] = None
    confidence_daily: Optional[float] = None
    outlook_daily: Optional[OutlookBias] = None
    regime_weekly: Optional[MarketRegime] = None
    confidence_weekly: Optional[float] = None
    outlook_weekly: Optional[OutlookBias] = None
    alignment: Optional[str] = None  # "agree", "mixed", "unknown"

class MarketRegimeDetector:
    """
    Detects market regimes based on price action and indicators.
    Extended to support daily and weekly timeframes.
    """

    def __init__(self):
        self.adx_period = 14
        self.volatility_period = 20
    
    def _resample_to_daily(self, candles: List[Any]) -> List[Dict[str, float]]:
        """Resample intraday candles to daily OHLC."""
        if not candles:
            return []
        
        # Group by day (UTC)
        daily_bars = {}
        for c in candles:
            # Assume candle has .time or timestamp
            if hasattr(c, "time"):
                ts = c.time
            elif hasattr(c, "timestamp"):
                ts = c.timestamp
            else:
                continue
            
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except:
                    continue
            elif isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                dt = ts
            
            day_key = dt.date()
            
            if day_key not in daily_bars:
                daily_bars[day_key] = {"h": c.h, "l": c.l, "o": c.o, "c": c.c, "count": 1}
            else:
                daily_bars[day_key]["h"] = max(daily_bars[day_key]["h"], c.h)
                daily_bars[day_key]["l"] = min(daily_bars[day_key]["l"], c.l)
                daily_bars[day_key]["c"] = c.c  # Last close of day
                daily_bars[day_key]["count"] += 1
        
        # Convert to list sorted by date
        result = []
        for day in sorted(daily_bars.keys()):
            result.append(daily_bars[day])
        return result
    
    def _resample_to_weekly(self, candles: List[Any]) -> List[Dict[str, float]]:
        """Resample candles to weekly OHLC."""
        if not candles:
            return []
        
        # Group by week (Monday = start of week)
        weekly_bars = {}
        for c in candles:
            if hasattr(c, "time"):
                ts = c.time
            elif hasattr(c, "timestamp"):
                ts = c.timestamp
            else:
                continue
            
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except:
                    continue
            elif isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                dt = ts
            
            # Get Monday of the week
            days_since_monday = dt.weekday()
            week_start = dt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
            week_key = week_start.date()
            
            if week_key not in weekly_bars:
                weekly_bars[week_key] = {"h": c.h, "l": c.l, "o": c.o, "c": c.c, "count": 1}
            else:
                weekly_bars[week_key]["h"] = max(weekly_bars[week_key]["h"], c.h)
                weekly_bars[week_key]["l"] = min(weekly_bars[week_key]["l"], c.l)
                weekly_bars[week_key]["c"] = c.c
                weekly_bars[week_key]["count"] += 1
        
        result = []
        for week in sorted(weekly_bars.keys()):
            result.append(weekly_bars[week])
        return result
    
    def calculate_adx(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """
        Calculate ADX (Average Directional Index).
        """
        if len(highs) < period * 2:
            return 0.0
            
        # Convert to numpy arrays
        highs = np.array(highs)
        lows = np.array(lows)
        closes = np.array(closes)
        
        # Calculate TR (True Range)
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate DM (Directional Movement)
        up_move = highs[1:] - highs[:-1]
        down_move = lows[:-1] - lows[1:]
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth TR and DM (Wilder's Smoothing)
        tr_smooth = np.zeros_like(tr)
        plus_dm_smooth = np.zeros_like(plus_dm)
        minus_dm_smooth = np.zeros_like(minus_dm)
        
        tr_smooth[period-1] = np.sum(tr[:period])
        plus_dm_smooth[period-1] = np.sum(plus_dm[:period])
        minus_dm_smooth[period-1] = np.sum(minus_dm[:period])
        
        for i in range(period, len(tr)):
            tr_smooth[i] = tr_smooth[i-1] - (tr_smooth[i-1]/period) + tr[i]
            plus_dm_smooth[i] = plus_dm_smooth[i-1] - (plus_dm_smooth[i-1]/period) + plus_dm[i]
            minus_dm_smooth[i] = minus_dm_smooth[i-1] - (minus_dm_smooth[i-1]/period) + minus_dm[i]
            
        # Calculate DI
        plus_di = 100 * (plus_dm_smooth / np.where(tr_smooth == 0, 1, tr_smooth))
        minus_di = 100 * (minus_dm_smooth / np.where(tr_smooth == 0, 1, tr_smooth))
        
        # Calculate DX
        sum_di = plus_di + minus_di
        dx = 100 * np.abs(plus_di - minus_di) / np.where(sum_di == 0, 1, sum_di)
        
        # Calculate ADX (Smoothed DX)
        adx = np.zeros_like(dx)
        if len(dx) >= period * 2:
             adx[period*2-1] = np.mean(dx[period:period*2])
             for i in range(period*2, len(dx)):
                 adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
                 
        return adx[-1]

    def calculate_directional_consistency(self, closes: List[float], period: int = 20) -> float:
        """
        Calculate what percentage of bars follow the dominant trend direction.
        Returns a score 0.0 to 1.0
        """
        if len(closes) < period:
            return 0.5
            
        recent_closes = closes[-period:]
        moves = np.diff(recent_closes)
        
        up_moves = np.sum(moves > 0)
        down_moves = np.sum(moves < 0)
        total_moves = len(moves)
        
        if total_moves == 0:
            return 0.5
            
        # Max consistency is seeing primarily one direction
        consistency = max(up_moves, down_moves) / total_moves
        return consistency

    def calculate_volatility(self, closes: List[float], period: int = 20) -> float:
        """
        Calculate normalized volatility (ATR / Price).
        """
        if len(closes) < period:
            return 0.0
        
        # Simple std dev based volatility for now, scaled to price
        recent = np.array(closes[-period:])
        return np.std(recent) / np.mean(recent)
    
    def _detect_outlook(self, closes: List[float]) -> OutlookBias:
        """Determine bias/outlook from price action."""
        if len(closes) < 2:
            return OutlookBias.NEUTRAL
        
        recent = closes[-20:] if len(closes) >= 20 else closes
        price_change = (recent[-1] - recent[0]) / recent[0] if recent[0] != 0 else 0.0
        
        if price_change > 0.001:  # 0.1% threshold
            return OutlookBias.BULLISH
        elif price_change < -0.001:
            return OutlookBias.BEARISH
        else:
            return OutlookBias.NEUTRAL

    def detect_regime(self, instrument: str, candles: List[Any]) -> RegimeAnalysis:
        """
        Analyze candles to determine market regime.
        Extended to compute daily and weekly regimes.
        """
        if not candles or len(candles) < 50:
             return RegimeAnalysis(MarketRegime.UNKNOWN, 0.0, 0.0, 0.0, "Insufficient Data")
             
        highs = [c.h for c in candles]
        lows = [c.l for c in candles]
        closes = [c.c for c in candles]
        
        # Original regime (intraday/resolved)
        adx = self.calculate_adx(highs, lows, closes)
        consistency = self.calculate_directional_consistency(closes)
        volatility = self.calculate_volatility(closes)
        
        regime = MarketRegime.RANGING
        description = "Sideways market"
        
        if adx >= 25 and consistency > 0.6:
            regime = MarketRegime.TRENDING
            description = f"Strong Trend (ADX={adx:.1f})"
        elif adx > 20 and adx < 25 and consistency < 0.5:
             regime = MarketRegime.CHOPPY
             description = f"Choppy/Whipsaw (ADX={adx:.1f})"
        else:
             regime = MarketRegime.RANGING
             description = f"Ranging (ADX={adx:.1f})"
        
        # Daily regime
        daily_bars = self._resample_to_daily(candles)
        regime_daily = MarketRegime.UNKNOWN
        confidence_daily = 0.0
        outlook_daily = OutlookBias.NEUTRAL
        
        if len(daily_bars) >= 14:
            daily_highs = [b["h"] for b in daily_bars]
            daily_lows = [b["l"] for b in daily_bars]
            daily_closes = [b["c"] for b in daily_bars]
            
            daily_adx = self.calculate_adx(daily_highs, daily_lows, daily_closes)
            daily_consistency = self.calculate_directional_consistency(daily_closes, period=min(20, len(daily_closes)))
            
            confidence_daily = min(1.0, (daily_adx / 30.0) * daily_consistency)
            
            if daily_adx >= 25 and daily_consistency > 0.6:
                regime_daily = MarketRegime.TRENDING
            elif daily_adx > 20 and daily_adx < 25 and daily_consistency < 0.5:
                regime_daily = MarketRegime.CHOPPY
            else:
                regime_daily = MarketRegime.RANGING
            
            outlook_daily = self._detect_outlook(daily_closes)
        
        # Weekly regime
        weekly_bars = self._resample_to_weekly(candles)
        regime_weekly = MarketRegime.UNKNOWN
        confidence_weekly = 0.0
        outlook_weekly = OutlookBias.NEUTRAL
        
        if len(weekly_bars) >= 8:
            weekly_highs = [b["h"] for b in weekly_bars]
            weekly_lows = [b["l"] for b in weekly_bars]
            weekly_closes = [b["c"] for b in weekly_bars]
            
            weekly_adx = self.calculate_adx(weekly_highs, weekly_lows, weekly_closes)
            weekly_consistency = self.calculate_directional_consistency(weekly_closes, period=min(10, len(weekly_closes)))
            
            confidence_weekly = min(1.0, (weekly_adx / 30.0) * weekly_consistency)
            
            if weekly_adx >= 25 and weekly_consistency > 0.6:
                regime_weekly = MarketRegime.TRENDING
            elif weekly_adx > 20 and weekly_adx < 25 and weekly_consistency < 0.5:
                regime_weekly = MarketRegime.CHOPPY
            else:
                regime_weekly = MarketRegime.RANGING
            
            outlook_weekly = self._detect_outlook(weekly_closes)
        
        # Alignment
        alignment = "unknown"
        if regime_daily != MarketRegime.UNKNOWN and regime_weekly != MarketRegime.UNKNOWN:
            if regime_daily == regime_weekly:
                alignment = "agree"
            elif (regime_daily == MarketRegime.TRENDING and regime_weekly == MarketRegime.RANGING) or \\
                 (regime_daily == MarketRegime.RANGING and regime_weekly == MarketRegime.TRENDING):
                alignment = "mixed"
            else:
                alignment = "mixed"
        
        # Resolved regime (backward compatible)
        if alignment == "agree":
            resolved_regime = regime_daily  # Use daily as primary
        elif alignment == "mixed":
            resolved_regime = MarketRegime.RANGING  # Default to ranging for mixed
        else:
            resolved_regime = regime  # Fall back to original
        
        return RegimeAnalysis(
            regime=resolved_regime,
            adx=adx,
            consistency=consistency,
            volatility=volatility,
            description=description,
            regime_daily=regime_daily,
            confidence_daily=confidence_daily,
            outlook_daily=outlook_daily,
            regime_weekly=regime_weekly,
            confidence_weekly=confidence_weekly,
            outlook_weekly=outlook_weekly,
            alignment=alignment
        )
'''

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/opt/ai-quant/src/core/market_regime.py"
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written extended market_regime.py to {target}")
