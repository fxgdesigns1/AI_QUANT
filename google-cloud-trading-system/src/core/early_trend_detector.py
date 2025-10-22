#!/usr/bin/env python3
"""
Early Trend Detection System - Catch trends before they fully form
Uses leading indicators instead of lagging indicators
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EarlyTrendDetector:
    """
    Detect early trend formation using leading indicators:
    - Volume surge detection (institutional interest)
    - Price structure changes (HH/HL or LH/LL forming)
    - Volatility expansion (energy building)
    - Microstructure patterns (consolidation before breakout)
    """
    
    def __init__(self):
        """Initialize early trend detector"""
        self.name = "Early Trend Detector"
        
        # Detection thresholds
        self.volume_surge_threshold = 2.0  # 2x average = surge
        self.volatility_expansion_threshold = 1.3  # 30% increase
        self.consolidation_threshold = 0.002  # 0.2% range = tight
        self.structure_lookback = 10  # Bars to analyze structure
        
        logger.info(f"✅ {self.name} initialized")
    
    def detect_early_bullish(self, prices: List[float], volumes: Optional[List[float]] = None) -> Dict:
        """
        Detect early bullish trend formation
        
        Returns:
            Dict with:
                - detected: bool
                - probability: float (0.0-1.0)
                - signals: List[str] (which indicators triggered)
                - entry_price: float (optimal entry level)
        """
        if len(prices) < 30:
            return {'detected': False, 'probability': 0.0, 'signals': [], 'entry_price': prices[-1]}
        
        signals = []
        confidence_scores = []
        
        # 1. Price Structure Change (Higher Highs, Higher Lows forming)
        structure_result = self._detect_bullish_structure(prices)
        if structure_result['detected']:
            signals.append(f"Bullish structure forming ({structure_result['score']:.0%})")
            confidence_scores.append(structure_result['score'])
        
        # 2. Volatility Expansion (Energy building)
        volatility_result = self._detect_volatility_expansion(prices)
        if volatility_result['expanding']:
            signals.append(f"Volatility expanding ({volatility_result['expansion_pct']:.0%})")
            confidence_scores.append(min(volatility_result['expansion_pct'] / 100, 1.0))
        
        # 3. Volume Surge (if available)
        if volumes and len(volumes) >= 20:
            volume_result = self._detect_volume_surge(volumes)
            if volume_result['surge']:
                signals.append(f"Volume surge ({volume_result['multiplier']:.1f}x)")
                confidence_scores.append(min(volume_result['multiplier'] / 3.0, 1.0))
        
        # 4. Consolidation Before Breakout
        consolidation_result = self._detect_consolidation(prices)
        if consolidation_result['consolidating']:
            signals.append(f"Tight consolidation ({consolidation_result['range_pct']:.2%})")
            confidence_scores.append(0.7)  # Consolidation is bullish
        
        # 5. Momentum Acceleration
        momentum_result = self._detect_momentum_acceleration(prices)
        if momentum_result['accelerating'] and momentum_result['direction'] == 'BULLISH':
            signals.append(f"Momentum accelerating")
            confidence_scores.append(0.8)
        
        # Calculate overall probability
        if confidence_scores:
            probability = np.mean(confidence_scores)
        else:
            probability = 0.0
        
        # Determine optimal entry price (pullback level)
        entry_price = self._calculate_optimal_entry(prices, 'BULLISH')
        
        detected = probability >= 0.5  # At least 50% confidence
        
        if detected:
            logger.info(f"🔍 Early bullish trend detected: {probability:.0%} confidence")
            logger.info(f"   Signals: {', '.join(signals)}")
            logger.info(f"   Optimal entry: {entry_price:.5f}")
        
        return {
            'detected': detected,
            'probability': probability,
            'signals': signals,
            'entry_price': entry_price,
            'direction': 'BULLISH'
        }
    
    def detect_early_bearish(self, prices: List[float], volumes: Optional[List[float]] = None) -> Dict:
        """
        Detect early bearish trend formation
        
        Returns: Same structure as detect_early_bullish
        """
        if len(prices) < 30:
            return {'detected': False, 'probability': 0.0, 'signals': [], 'entry_price': prices[-1]}
        
        signals = []
        confidence_scores = []
        
        # 1. Price Structure Change (Lower Highs, Lower Lows forming)
        structure_result = self._detect_bearish_structure(prices)
        if structure_result['detected']:
            signals.append(f"Bearish structure forming ({structure_result['score']:.0%})")
            confidence_scores.append(structure_result['score'])
        
        # 2. Volatility Expansion
        volatility_result = self._detect_volatility_expansion(prices)
        if volatility_result['expanding']:
            signals.append(f"Volatility expanding ({volatility_result['expansion_pct']:.0%})")
            confidence_scores.append(min(volatility_result['expansion_pct'] / 100, 1.0))
        
        # 3. Volume Surge
        if volumes and len(volumes) >= 20:
            volume_result = self._detect_volume_surge(volumes)
            if volume_result['surge']:
                signals.append(f"Volume surge ({volume_result['multiplier']:.1f}x)")
                confidence_scores.append(min(volume_result['multiplier'] / 3.0, 1.0))
        
        # 4. Consolidation Before Breakdown
        consolidation_result = self._detect_consolidation(prices)
        if consolidation_result['consolidating']:
            signals.append(f"Tight consolidation ({consolidation_result['range_pct']:.2%})")
            confidence_scores.append(0.7)
        
        # 5. Momentum Acceleration
        momentum_result = self._detect_momentum_acceleration(prices)
        if momentum_result['accelerating'] and momentum_result['direction'] == 'BEARISH':
            signals.append(f"Momentum accelerating")
            confidence_scores.append(0.8)
        
        # Calculate overall probability
        if confidence_scores:
            probability = np.mean(confidence_scores)
        else:
            probability = 0.0
        
        # Determine optimal entry price
        entry_price = self._calculate_optimal_entry(prices, 'BEARISH')
        
        detected = probability >= 0.5
        
        if detected:
            logger.info(f"🔍 Early bearish trend detected: {probability:.0%} confidence")
            logger.info(f"   Signals: {', '.join(signals)}")
            logger.info(f"   Optimal entry: {entry_price:.5f}")
        
        return {
            'detected': detected,
            'probability': probability,
            'signals': signals,
            'entry_price': entry_price,
            'direction': 'BEARISH'
        }
    
    def _detect_bullish_structure(self, prices: List[float]) -> Dict:
        """Detect Higher Highs and Higher Lows forming"""
        if len(prices) < self.structure_lookback * 2:
            return {'detected': False, 'score': 0.0}
        
        recent = prices[-self.structure_lookback:]
        previous = prices[-self.structure_lookback * 2:-self.structure_lookback]
        
        # Find highs and lows in each period
        recent_high = max(recent)
        recent_low = min(recent)
        previous_high = max(previous)
        previous_low = min(previous)
        
        # Check for HH and HL
        higher_high = recent_high > previous_high
        higher_low = recent_low > previous_low
        
        if higher_high and higher_low:
            score = 0.9  # Strong bullish structure
        elif higher_high:
            score = 0.6  # Partial structure
        elif higher_low:
            score = 0.5  # Partial structure
        else:
            score = 0.0
        
        return {
            'detected': score >= 0.5,
            'score': score,
            'higher_high': higher_high,
            'higher_low': higher_low
        }
    
    def _detect_bearish_structure(self, prices: List[float]) -> Dict:
        """Detect Lower Highs and Lower Lows forming"""
        if len(prices) < self.structure_lookback * 2:
            return {'detected': False, 'score': 0.0}
        
        recent = prices[-self.structure_lookback:]
        previous = prices[-self.structure_lookback * 2:-self.structure_lookback]
        
        recent_high = max(recent)
        recent_low = min(recent)
        previous_high = max(previous)
        previous_low = min(previous)
        
        # Check for LH and LL
        lower_high = recent_high < previous_high
        lower_low = recent_low < previous_low
        
        if lower_high and lower_low:
            score = 0.9  # Strong bearish structure
        elif lower_high:
            score = 0.6
        elif lower_low:
            score = 0.5
        else:
            score = 0.0
        
        return {
            'detected': score >= 0.5,
            'score': score,
            'lower_high': lower_high,
            'lower_low': lower_low
        }
    
    def _detect_volatility_expansion(self, prices: List[float]) -> Dict:
        """Detect if volatility is expanding (energy building)"""
        if len(prices) < 40:
            return {'expanding': False, 'expansion_pct': 0}
        
        # Compare recent ATR to older ATR
        recent_atr = self._calculate_atr(prices[-20:])
        older_atr = self._calculate_atr(prices[-40:-20])
        
        if older_atr == 0:
            return {'expanding': False, 'expansion_pct': 0}
        
        expansion_pct = ((recent_atr - older_atr) / older_atr) * 100
        
        return {
            'expanding': recent_atr > older_atr * self.volatility_expansion_threshold,
            'expansion_pct': expansion_pct,
            'recent_atr': recent_atr,
            'older_atr': older_atr
        }
    
    def _calculate_atr(self, prices: List[float]) -> float:
        """Calculate Average True Range"""
        if len(prices) < 2:
            return 0.0
        ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        return np.mean(ranges) if ranges else 0.0
    
    def _detect_volume_surge(self, volumes: List[float]) -> Dict:
        """Detect volume surge (institutional interest)"""
        if len(volumes) < 20:
            return {'surge': False, 'multiplier': 1.0}
        
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-20:-1])
        
        if avg_volume == 0:
            return {'surge': False, 'multiplier': 1.0}
        
        multiplier = current_volume / avg_volume
        
        return {
            'surge': multiplier >= self.volume_surge_threshold,
            'multiplier': multiplier,
            'current': current_volume,
            'average': avg_volume
        }
    
    def _detect_consolidation(self, prices: List[float]) -> Dict:
        """Detect tight consolidation (precedes breakout)"""
        if len(prices) < 10:
            return {'consolidating': False, 'range_pct': 0}
        
        recent = prices[-10:]
        high = max(recent)
        low = min(recent)
        mid = (high + low) / 2
        
        if mid == 0:
            return {'consolidating': False, 'range_pct': 0}
        
        range_pct = (high - low) / mid
        
        return {
            'consolidating': range_pct <= self.consolidation_threshold,
            'range_pct': range_pct,
            'high': high,
            'low': low
        }
    
    def _detect_momentum_acceleration(self, prices: List[float]) -> Dict:
        """Detect if momentum is accelerating"""
        if len(prices) < 30:
            return {'accelerating': False, 'direction': 'NEUTRAL'}
        
        # Calculate momentum over different periods
        short_momentum = (prices[-1] - prices[-5]) / prices[-5] if prices[-5] != 0 else 0
        medium_momentum = (prices[-1] - prices[-10]) / prices[-10] if prices[-10] != 0 else 0
        long_momentum = (prices[-1] - prices[-20]) / prices[-20] if prices[-20] != 0 else 0
        
        # Check if momentum is increasing
        if short_momentum > medium_momentum > long_momentum > 0:
            return {'accelerating': True, 'direction': 'BULLISH', 'momentum': short_momentum}
        elif short_momentum < medium_momentum < long_momentum < 0:
            return {'accelerating': True, 'direction': 'BEARISH', 'momentum': short_momentum}
        else:
            return {'accelerating': False, 'direction': 'NEUTRAL', 'momentum': short_momentum}
    
    def _calculate_optimal_entry(self, prices: List[float], direction: str) -> float:
        """
        Calculate optimal entry price (wait for pullback, don't chase)
        
        For BULLISH: Entry slightly below current price (pullback to support)
        For BEARISH: Entry slightly above current price (pullback to resistance)
        """
        if len(prices) < 20:
            return prices[-1]
        
        current_price = prices[-1]
        recent_prices = prices[-20:]
        atr = self._calculate_atr(recent_prices)
        
        if direction == 'BULLISH':
            # Enter on pullback (0.5 ATR below current)
            entry = current_price - (0.5 * atr)
            # But not below recent support
            support = min(recent_prices[-10:])
            entry = max(entry, support)
        else:  # BEARISH
            # Enter on pullback (0.5 ATR above current)
            entry = current_price + (0.5 * atr)
            # But not above recent resistance
            resistance = max(recent_prices[-10:])
            entry = min(entry, resistance)
        
        return entry
    
    def calculate_trend_probability(self, prices: List[float], volumes: Optional[List[float]] = None) -> Dict:
        """
        Calculate probability of trend in either direction
        
        Returns: Dict with bullish_prob, bearish_prob, recommended_direction
        """
        bullish = self.detect_early_bullish(prices, volumes)
        bearish = self.detect_early_bearish(prices, volumes)
        
        if bullish['probability'] > bearish['probability']:
            recommended = 'BULLISH'
        elif bearish['probability'] > bullish['probability']:
            recommended = 'BEARISH'
        else:
            recommended = 'NEUTRAL'
        
        return {
            'bullish_probability': bullish['probability'],
            'bearish_probability': bearish['probability'],
            'recommended_direction': recommended,
            'bullish_signals': bullish['signals'],
            'bearish_signals': bearish['signals'],
            'bullish_entry': bullish['entry_price'],
            'bearish_entry': bearish['entry_price']
        }


# Global instance
_early_trend_detector = None


def get_early_trend_detector() -> EarlyTrendDetector:
    """Get the global early trend detector instance"""
    global _early_trend_detector
    if _early_trend_detector is None:
        _early_trend_detector = EarlyTrendDetector()
    return _early_trend_detector

