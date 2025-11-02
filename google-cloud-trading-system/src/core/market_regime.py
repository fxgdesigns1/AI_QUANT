#!/usr/bin/env python3
"""
Market Regime Detection System
Automatically detects trending, ranging, or choppy market conditions
and adapts trading criteria accordingly
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """
    Detects market regime (trending/ranging/choppy) and provides
    adaptive thresholds for entry criteria
    """
    
    def __init__(self):
        """Initialize market regime detector"""
        self.name = "Market Regime Detector"
        
        # Regime detection thresholds
        self.trending_adx_threshold = 25
        self.ranging_adx_threshold = 20
        self.direction_consistency_threshold = 0.7
        
        # Adaptive multipliers
        self.trending_multiplier = 0.85  # Easier entry (15% lower thresholds)
        self.ranging_multiplier = 1.15   # Harder entry (15% higher thresholds)
        self.choppy_multiplier = 1.30    # Much harder (30% higher thresholds)
        
        logger.info(f"✅ {self.name} initialized")
    
    def _calc_direction_consistency(self, prices: List[float]) -> float:
        """
        Calculate what % of bars are moving in the same direction
        Returns: 0.0 to 1.0 (1.0 = all bars in same direction)
        """
        if len(prices) < 20:
            return 0.0
        
        # Check last 20 bars
        recent_prices = prices[-20:]
        
        # Count up bars and down bars
        up_bars = sum(1 for i in range(1, len(recent_prices)) 
                     if recent_prices[i] > recent_prices[i-1])
        down_bars = sum(1 for i in range(1, len(recent_prices)) 
                       if recent_prices[i] < recent_prices[i-1])
        
        total_bars = len(recent_prices) - 1
        
        # Return the dominant direction percentage
        dominant = max(up_bars, down_bars)
        return dominant / total_bars if total_bars > 0 else 0.0
    
    def _calc_volatility_trend(self, prices: List[float]) -> str:
        """
        Determine if volatility is expanding, contracting, or stable
        Returns: 'EXPANDING', 'CONTRACTING', or 'STABLE'
        """
        if len(prices) < 40:
            return 'STABLE'
        
        # Calculate ATR for recent and older periods
        recent_atr = self._calculate_atr(prices[-20:])
        older_atr = self._calculate_atr(prices[-40:-20])
        
        if recent_atr > older_atr * 1.2:
            return 'EXPANDING'
        elif recent_atr < older_atr * 0.8:
            return 'CONTRACTING'
        else:
            return 'STABLE'
    
    def _calculate_atr(self, prices: List[float]) -> float:
        """Simple ATR calculation"""
        if len(prices) < 2:
            return 0.0
        
        ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        return np.mean(ranges) if ranges else 0.0
    
    def _find_key_levels(self, prices: List[float]) -> Dict[str, List[float]]:
        """
        Identify support and resistance levels
        Returns: {'support': [levels], 'resistance': [levels]}
        """
        if len(prices) < 50:
            return {'support': [], 'resistance': []}
        
        highs = []
        lows = []
        
        # Find local highs and lows
        for i in range(5, len(prices) - 5):
            # Local high (pivot high)
            if prices[i] == max(prices[i-5:i+6]):
                highs.append(prices[i])
            # Local low (pivot low)
            if prices[i] == min(prices[i-5:i+6]):
                lows.append(prices[i])
        
        # Cluster nearby levels (within 0.3%)
        resistance_levels = self._cluster_levels(highs, tolerance=0.003)
        support_levels = self._cluster_levels(lows, tolerance=0.003)
        
        return {
            'resistance': resistance_levels[:3],  # Top 3 resistance levels
            'support': support_levels[:3]          # Top 3 support levels
        }
    
    def _cluster_levels(self, levels: List[float], tolerance: float = 0.003) -> List[float]:
        """
        Cluster nearby price levels together
        tolerance: 0.003 = 0.3%
        """
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # If within tolerance of cluster mean, add to cluster
            cluster_mean = np.mean(current_cluster)
            if abs(level - cluster_mean) / cluster_mean < tolerance:
                current_cluster.append(level)
            else:
                # Start new cluster
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        
        # Add final cluster
        if current_cluster:
            clusters.append(np.mean(current_cluster))
        
        return clusters
    
    def _trending_regime(self, prices: List[float], adx: float, 
                        direction_consistency: float) -> Dict:
        """
        Detect trending market regime
        """
        # Determine trend direction
        recent_prices = prices[-20:]
        trend_slope = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        direction = 'BULLISH' if trend_slope > 0 else 'BEARISH'
        strength = min(1.0, (adx / 50) * direction_consistency)
        
        return {
            'regime': 'TRENDING',
            'direction': direction,
            'strength': strength,
            'adapt_multiplier': self.trending_multiplier,
            'adx': adx,
            'consistency': direction_consistency,
            'description': f'{direction} trend with {adx:.1f} ADX'
        }
    
    def _ranging_regime(self, prices: List[float], 
                       support_resistance: Dict) -> Dict:
        """
        Detect ranging market regime
        """
        current_price = prices[-1]
        
        # Find range boundaries
        if support_resistance['support'] and support_resistance['resistance']:
            support = max(support_resistance['support'])
            resistance = min(support_resistance['resistance'])
            
            # Calculate position in range
            range_size = resistance - support
            position_in_range = (current_price - support) / range_size if range_size > 0 else 0.5
        else:
            support = min(prices[-50:]) if len(prices) >= 50 else prices[-1]
            resistance = max(prices[-50:]) if len(prices) >= 50 else prices[-1]
            position_in_range = 0.5
        
        return {
            'regime': 'RANGING',
            'support': support,
            'resistance': resistance,
            'position_in_range': position_in_range,
            'adapt_multiplier': self.ranging_multiplier,
            'description': f'Range {support:.5f} - {resistance:.5f}'
        }
    
    def _choppy_regime(self, prices: List[float], adx: float) -> Dict:
        """
        Detect choppy/uncertain market regime
        """
        # Count direction changes in last 20 bars
        recent_prices = prices[-20:] if len(prices) >= 20 else prices
        direction_changes = 0
        
        for i in range(2, len(recent_prices)):
            prev_move = recent_prices[i-1] - recent_prices[i-2]
            curr_move = recent_prices[i] - recent_prices[i-1]
            
            # Direction changed if signs are different
            if prev_move * curr_move < 0:
                direction_changes += 1
        
        choppiness = direction_changes / (len(recent_prices) - 2) if len(recent_prices) > 2 else 0.5
        
        return {
            'regime': 'CHOPPY',
            'choppiness': choppiness,
            'adx': adx,
            'adapt_multiplier': self.choppy_multiplier,
            'description': f'Choppy market (ADX {adx:.1f}, {direction_changes} changes)'
        }
    
    def analyze_regime(self, instrument: str, prices: List[float], 
                      adx: float) -> Dict:
        """
        Main regime analysis function
        
        Returns regime dict with:
        - regime: 'TRENDING', 'RANGING', or 'CHOPPY'
        - adapt_multiplier: How much to adjust thresholds
        - Additional regime-specific data
        """
        if len(prices) < 30:
            logger.warning(f"Not enough price data for {instrument} ({len(prices)} bars)")
            return {
                'regime': 'UNKNOWN',
                'adapt_multiplier': 1.0,
                'description': 'Insufficient data'
            }
        
        # Calculate key metrics
        direction_consistency = self._calc_direction_consistency(prices)
        volatility_trend = self._calc_volatility_trend(prices)
        support_resistance = self._find_key_levels(prices)
        
        # Classify regime
        if adx >= self.trending_adx_threshold and direction_consistency >= self.direction_consistency_threshold:
            # Strong trend detected
            regime = self._trending_regime(prices, adx, direction_consistency)
            logger.info(f"📈 {instrument}: TRENDING {regime['direction']} (ADX {adx:.1f}, consistency {direction_consistency:.0%})")
        
        elif adx < self.ranging_adx_threshold:
            # Weak trend = ranging market
            regime = self._ranging_regime(prices, support_resistance)
            logger.info(f"↔️  {instrument}: RANGING (ADX {adx:.1f})")
        
        else:
            # Ambiguous = choppy market
            regime = self._choppy_regime(prices, adx)
            logger.info(f"🌀 {instrument}: CHOPPY (ADX {adx:.1f})")
        
        # Add volatility info
        regime['volatility_trend'] = volatility_trend
        regime['support_resistance'] = support_resistance
        
        return regime
    
    def get_adaptive_thresholds(self, base_thresholds: Dict, regime: Dict) -> Dict:
        """
        Adjust thresholds based on market regime
        
        Trending: multiply by 0.85 (easier to enter - catch pullbacks)
        Ranging: multiply by 1.15 (harder - wait for key levels)
        Choppy: multiply by 1.30 (much harder - very selective)
        
        Args:
            base_thresholds: {'quality': 70, 'momentum': 0.008, 'confidence': 0.65}
            regime: Regime dict from analyze_regime()
        
        Returns:
            Adjusted thresholds dict
        """
        multiplier = regime.get('adapt_multiplier', 1.0)
        
        adapted = {
            'quality_min': base_thresholds.get('quality', 70) * multiplier,
            'momentum_min': base_thresholds.get('momentum', 0.008) * multiplier,
            'confidence_min': base_thresholds.get('confidence', 0.65) * multiplier,
            'regime': regime['regime'],
            'multiplier': multiplier
        }
        
        logger.debug(f"Adaptive thresholds: Quality {adapted['quality_min']:.1f}, "
                    f"Momentum {adapted['momentum_min']:.4f} ({regime['regime']})")
        
        return adapted
    
    def is_near_key_level(self, current_price: float, regime: Dict, 
                         tolerance: float = 0.002) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Check if price is near support or resistance
        
        Returns: (is_near, level, level_type)
        tolerance: 0.002 = 0.2%
        """
        if regime['regime'] != 'RANGING':
            return False, None, None
        
        levels = regime.get('support_resistance', {})
        
        # Check resistance levels
        for resistance in levels.get('resistance', []):
            if abs(current_price - resistance) / resistance < tolerance:
                return True, resistance, 'RESISTANCE'
        
        # Check support levels
        for support in levels.get('support', []):
            if abs(current_price - support) / support < tolerance:
                return True, support, 'SUPPORT'
        
        return False, None, None


# Global instance
_market_regime_detector = None

def get_market_regime_detector() -> MarketRegimeDetector:
    """Get the global market regime detector instance"""
    global _market_regime_detector
    if _market_regime_detector is None:
        _market_regime_detector = MarketRegimeDetector()
    return _market_regime_detector


















