import numpy as np
import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    CHOPPY = "CHOPPY"
    UNKNOWN = "UNKNOWN"

@dataclass
class RegimeAnalysis:
    regime: MarketRegime
    adx: float
    consistency: float
    volatility: float
    description: str
    # New fields for countdown transparency
    required_candles: int = 50
    current_candles: int = 0
    candles_remaining: int = 0
    timeframe_seconds: int = 3600  # Default H1
    eta_seconds: int = 0

class MarketRegimeDetector:
    """
    Detects market regimes based on price action and indicators.
    """

    def __init__(self):
        self.adx_period = 14
        self.volatility_period = 20
    
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
        # Using a simple EMA approximation for efficiency if needed, but here's Wilder's
        # First value is simple sum
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
        if len(dx) >= period * 2: # Need enough data
             adx[period*2-1] = np.mean(dx[period:period*2]) # Initial mean
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

    def detect_regime(self, instrument: str, candles: List[Any], timeframe_seconds: int = 3600) -> RegimeAnalysis:
        """
        Analyze candles to determine market regime.
        """
        required_candles = 50
        current_candles = len(candles) if candles else 0
        candles_remaining = max(required_candles - current_candles, 0)
        eta_seconds = candles_remaining * timeframe_seconds
        
        if not candles or current_candles < required_candles:
             return RegimeAnalysis(
                 regime=MarketRegime.UNKNOWN, 
                 adx=0.0, 
                 consistency=0.0, 
                 volatility=0.0, 
                 description="Insufficient Data",
                 required_candles=required_candles,
                 current_candles=current_candles,
                 candles_remaining=candles_remaining,
                 timeframe_seconds=timeframe_seconds,
                 eta_seconds=eta_seconds
             )
             
        highs = [c.h for c in candles]
        lows = [c.l for c in candles]
        closes = [c.c for c in candles]
        
        adx = self.calculate_adx(highs, lows, closes)
        consistency = self.calculate_directional_consistency(closes)
        volatility = self.calculate_volatility(closes)
        
        regime = MarketRegime.RANGING
        description = "Sideways market"
        
        # Regime Logic
        if adx >= 25 and consistency > 0.6:
            regime = MarketRegime.TRENDING
            description = f"Strong Trend (ADX={adx:.1f})"
        elif adx > 20 and adx < 25 and consistency < 0.5:
             regime = MarketRegime.CHOPPY
             description = f"Choppy/Whipsaw (ADX={adx:.1f})"
        else:
             regime = MarketRegime.RANGING
             description = f"Ranging (ADX={adx:.1f})"
             
        return RegimeAnalysis(
            regime=regime, 
            adx=adx, 
            consistency=consistency, 
            volatility=volatility, 
            description=description,
            required_candles=required_candles,
            current_candles=current_candles,
            candles_remaining=candles_remaining,
            timeframe_seconds=timeframe_seconds,
            eta_seconds=eta_seconds
        )
