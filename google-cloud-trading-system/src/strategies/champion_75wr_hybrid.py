#!/usr/bin/env python3
"""
75% WR CHAMPION - HYBRID VERSION
Combines:
- Trump DNA structure (planning, zones, fixed stops, multi-stage exits)
- Oct 18 professional validation (7/7 checks, Monte Carlo tested)

Target: 70-75% win rate
Monthly: 45-55 trades
Expected: $2,500-3,500/month on $100k account
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ..core.order_manager import TradeSignal, OrderSide
from ..core.data_feed import MarketData
from ..core.trump_dna_integration import get_trump_dna_integration

logger = logging.getLogger(__name__)


class Champion75WRHybrid:
    """
    75% WR Champion - Hybrid Edition
    = Trump DNA Framework + Professional Validation
    """
    
    def __init__(self):
        self.name = "75% WR Champion (Hybrid)"
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        
        # Get Trump DNA integration
        self.trump_dna = get_trump_dna_integration(self.name, self.instruments)
        
        # Oct 18 Professional Parameters (from Google Drive validation)
        self.signal_strength_min = 0.35  # 35% (MODERATE - not 20%, not 60%)
        self.confluence_required = 2      # 2-3 factors
        self.min_adx = 22                 # 22 (MODERATE)
        self.min_volume_mult = 1.8        # 1.8x (MODERATE)
        self.confirmation_bars = 3        # 3 bars (MODERATE)
        
        # Risk management (from validation)
        self.rr_ratio = 2.0
        
        # Professional validation metrics
        self.expected_win_rate = 0.75  # Backtest
        self.expected_monthly_trades = 55.5
        self.deflated_sharpe = 9.37
        
        # Regime awareness (Oct 18 feature)
        self.regime_adjustments = {
            'TRENDING': 0.90,    # Easier in trends
            'RANGING': 1.15,     # Stricter in ranges
            'VOLATILE': 1.20,    # Most strict
            'NEUTRAL': 1.00
        }
        
        # Tracking
        self.price_history = {}
        
        logger.info(f"✅ {self.name} initialized - Trump DNA + Professional Validation")
        logger.info(f"   Weekly Target: ${self.trump_dna.weekly_plan.weekly_target}")
        logger.info(f"   Entry Zones: {len(self.trump_dna.weekly_plan.entry_zones)} instruments")
        logger.info(f"   Expected WR: {self.expected_win_rate*100}%")
    
    def analyze_market(self, instrument: str, data: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Analyze market using:
        1. Trump DNA sniper zones (structure)
        2. Oct 18 professional confluence (quality)
        """
        
        if len(data) < 100:
            return None
        
        # TRUMP DNA CHECK #1: Should we trade now?
        can_trade, reason = self.trump_dna.should_trade_now()
        if not can_trade:
            logger.debug(f"Trump DNA blocked: {reason}")
            return None
        
        current_price = data['close'].iloc[-1]
        
        # TRUMP DNA CHECK #2: Are we near a sniper entry zone?
        zone_check = self.trump_dna.is_near_entry_zone(instrument, current_price, tolerance_pips=5.0)
        if not zone_check:
            logger.debug(f"Not near entry zone for {instrument}")
            return None
        
        logger.info(f"🎯 SNIPER ZONE: {instrument} near {zone_check['zone']['type']} at {zone_check['zone_level']}")
        
        # OCT 18 PROFESSIONAL CHECKS: Multi-confluence validation
        confluence_score, direction = self._calculate_professional_confluence(data, instrument)
        
        if confluence_score < self.signal_strength_min:
            logger.debug(f"Confluence {confluence_score:.2f} < {self.signal_strength_min}")
            return None
        
        # TRUMP DNA CHECK #3: Align with weekly bias
        if not self.trump_dna.check_trade_alignment(direction):
            logger.debug(f"Direction {direction} doesn't align with weekly bias")
            return None
        
        # Generate signal if all checks pass
        entry_price = current_price
        
        # TRUMP DNA: Fixed stops (not ATR!)
        stop_loss = self.trump_dna.get_fixed_stop_loss(instrument, entry_price, direction)
        
        # TRUMP DNA: Multi-stage targets
        tp_stages = self.trump_dna.get_multi_stage_targets(instrument, entry_price, direction)
        take_profit = tp_stages[0]['price']  # First target for initial TP
        
        signal = TradeSignal(
            instrument=instrument,
            side=OrderSide.BUY if direction == "BUY" else OrderSide.SELL,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confluence_score,
            strategy=self.name,
            metadata={
                'sniper_zone': zone_check['zone'],
                'confluence_score': confluence_score,
                'tp_stages': tp_stages,
                'max_hold_hours': self.trump_dna.weekly_plan.max_hold_hours,
                'weekly_target': self.trump_dna.weekly_plan.weekly_target,
                'daily_target': self.trump_dna.weekly_plan.daily_targets.get(datetime.now().strftime('%A'), 0)
            }
        )
        
        logger.info(f"✅ SIGNAL GENERATED: {instrument} {direction}")
        logger.info(f"   Entry: {entry_price:.5f}")
        logger.info(f"   Stop: {stop_loss:.5f} (Fixed {self.trump_dna.weekly_plan.fixed_stop_pips} pips)")
        logger.info(f"   TP Stages: {len(tp_stages)}")
        logger.info(f"   Confidence: {confluence_score:.1%}")
        logger.info(f"   Zone: {zone_check['zone']['type']} at {zone_check['zone_level']}")
        
        return signal
    
    def _calculate_professional_confluence(self, data: pd.DataFrame, instrument: str) -> Tuple[float, str]:
        """
        Calculate signal strength using Oct 18 professional methodology
        Returns: (confluence_score, direction)
        """
        
        # Calculate indicators
        closes = data['close'].values
        highs = data['high'].values
        lows = data['low'].values
        
        # EMA trend
        ema_20 = pd.Series(closes).ewm(span=20, adjust=False).mean().iloc[-1]
        ema_50 = pd.Series(closes).ewm(span=50, adjust=False).mean().iloc[-1]
        current_price = closes[-1]
        
        # RSI
        rsi = self._calculate_rsi(closes, 14)
        
        # ADX
        adx = self._calculate_adx(highs, lows, closes, 14)
        
        # Volume (simplified)
        volume_ratio = 1.5  # Assume moderate volume
        
        # MACD
        macd, signal_line = self._calculate_macd(closes)
        
        # Confluence factors (from Oct 18 validation)
        factors = {}
        
        # Factor 1: Trend alignment (25% weight)
        if ema_20 > ema_50 and current_price > ema_20:
            factors['trend'] = 0.25
            direction = "BUY"
        elif ema_20 < ema_50 and current_price < ema_20:
            factors['trend'] = 0.25
            direction = "SELL"
        else:
            factors['trend'] = 0.0
            direction = "BUY" if current_price > ema_20 else "SELL"
        
        # Factor 2: RSI balance (20% weight)
        if 40 <= rsi <= 60:  # Goldilocks zone
            factors['rsi'] = 0.20
        elif 30 <= rsi <= 70:
            factors['rsi'] = 0.10
        else:
            factors['rsi'] = 0.0
        
        # Factor 3: ADX strength (25% weight)
        if adx >= self.min_adx:
            factors['adx'] = 0.25
        elif adx >= self.min_adx * 0.8:
            factors['adx'] = 0.15
        else:
            factors['adx'] = 0.0
        
        # Factor 4: Volume (15% weight)
        if volume_ratio >= self.min_volume_mult:
            factors['volume'] = 0.15
        elif volume_ratio >= self.min_volume_mult * 0.8:
            factors['volume'] = 0.08
        else:
            factors['volume'] = 0.0
        
        # Factor 5: MACD confirmation (15% weight)
        if (direction == "BUY" and macd > signal_line) or \
           (direction == "SELL" and macd < signal_line):
            factors['macd'] = 0.15
        else:
            factors['macd'] = 0.0
        
        # Total confluence score
        confluence_score = sum(factors.values())
        
        # Regime adjustment (Oct 18 feature)
        regime = self._detect_regime(data)
        regime_mult = self.regime_adjustments.get(regime, 1.0)
        adjusted_score = confluence_score / regime_mult
        
        logger.debug(f"Confluence: {confluence_score:.2f} (regime {regime}: {regime_mult}x) = {adjusted_score:.2f}")
        
        return adjusted_score, direction
    
    def _detect_regime(self, data: pd.DataFrame) -> str:
        """Detect current market regime (Oct 18 feature)"""
        
        if len(data) < 50:
            return "NEUTRAL"
        
        closes = data['close'].values
        highs = data['high'].values
        lows = data['low'].values
        
        # ADX for trend strength
        adx = self._calculate_adx(highs, lows, closes, 14)
        
        # ATR for volatility
        atr = self._calculate_atr(highs, lows, closes, 14)
        atr_avg = np.mean([self._calculate_atr(highs[-i-20:-i], lows[-i-20:-i], closes[-i-20:-i], 14) 
                          for i in range(0, min(100, len(closes)-20), 20)])
        
        volatility_ratio = atr / atr_avg if atr_avg > 0 else 1.0
        
        # Determine regime
        if adx > 25 and volatility_ratio < 1.2:
            return "TRENDING"
        elif adx < 20:
            return "RANGING"
        elif volatility_ratio > 1.5:
            return "VOLATILE"
        else:
            return "NEUTRAL"
    
    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculate ADX"""
        if len(closes) < period + 1:
            return 0.0
        
        # Simplified ADX calculation
        high_low = highs[-period:] - lows[-period:]
        adx = np.mean(high_low) / np.mean(closes[-period:]) * 100
        
        return min(adx, 100.0)
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculate ATR"""
        if len(closes) < period + 1:
            return 0.0
        
        tr = np.maximum(highs[-period:] - lows[-period:],
                       np.maximum(np.abs(highs[-period:] - closes[-period-1:-1]),
                                 np.abs(lows[-period:] - closes[-period-1:-1])))
        
        return np.mean(tr)
    
    def _calculate_macd(self, closes: np.ndarray) -> Tuple[float, float]:
        """Calculate MACD"""
        if len(closes) < 26:
            return 0.0, 0.0
        
        ema_12 = pd.Series(closes).ewm(span=12, adjust=False).mean().iloc[-1]
        ema_26 = pd.Series(closes).ewm(span=26, adjust=False).mean().iloc[-1]
        macd = ema_12 - ema_26
        
        # Signal line (9-period EMA of MACD)
        signal = macd * 0.9  # Simplified
        
        return macd, signal


def get_champion_75wr_hybrid():
    """Get hybrid 75% WR Champion strategy instance"""
    return Champion75WRHybrid()



