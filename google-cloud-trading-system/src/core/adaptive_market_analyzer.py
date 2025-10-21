#!/usr/bin/env python3
"""
Adaptive Market Condition Analyzer
Automatically adjusts confidence thresholds and position sizing based on market conditions

This system:
1. Analyzes real-time market conditions (volatility, trend, spread, volume)
2. Calculates optimal confidence threshold for current conditions
3. Adjusts position sizing based on confidence level
4. Has a hard floor (minimum threshold) for safety
5. Logs all decisions for transparency
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING_STRONG = "trending_strong"      # Clear trend, high confidence
    TRENDING_WEAK = "trending_weak"          # Trend but choppy
    RANGING_TIGHT = "ranging_tight"          # Consolidation, low volatility
    RANGING_VOLATILE = "ranging_volatile"    # Choppy, high volatility
    BREAKOUT = "breakout"                    # Breaking key levels
    WHIPSAW = "whipsaw"                      # Dangerous, avoid


@dataclass
class MarketCondition:
    """Market condition assessment"""
    regime: MarketRegime
    volatility_score: float  # 0-1 (0=dead, 1=extreme)
    trend_strength: float    # 0-1 (0=ranging, 1=strong trend)
    spread_quality: float    # 0-1 (0=wide, 1=tight)
    volume_score: float      # 0-1 (0=low, 1=high)
    overall_quality: float   # 0-1 (combined score)
    
    # Recommended settings
    recommended_confidence: float
    recommended_risk_multiplier: float
    recommended_max_positions: int
    
    # Metadata
    timestamp: datetime
    reason: str


class AdaptiveMarketAnalyzer:
    """
    Analyzes market conditions and adapts trading parameters
    
    Key Features:
    - Dynamic confidence thresholds (60-80%)
    - Position sizing adjustments (0.5x - 2x)
    - Hard minimum floor (60% confidence)
    - Market regime detection
    - Session-aware adjustments
    """
    
    def __init__(self):
        self.name = "AdaptiveMarketAnalyzer"
        
        # CONFIDENCE THRESHOLD SETTINGS
        self.confidence_floor = 0.60      # Absolute minimum (never go below)
        self.confidence_ceiling = 0.80    # Maximum threshold (for bad conditions)
        self.confidence_optimal = 0.65    # Target for good conditions
        
        # POSITION SIZING MULTIPLIERS
        self.risk_min_multiplier = 0.5    # Reduce to 50% in bad conditions
        self.risk_max_multiplier = 2.0    # Increase to 200% in excellent conditions
        self.risk_normal_multiplier = 1.0  # Standard sizing
        
        # MARKET CONDITION WEIGHTS
        self.weights = {
            'volatility': 0.25,
            'trend': 0.30,
            'spread': 0.25,
            'volume': 0.20
        }
        
        # HISTORICAL DATA
        self.condition_history = []
        self.max_history = 100
        
        # SESSION ADJUSTMENTS
        self.session_multipliers = {
            'asian': 0.8,      # Lower confidence during Asian (lower liquidity)
            'london': 1.2,     # Higher confidence during London (best liquidity)
            'ny_overlap': 1.3, # Highest during London/NY overlap
            'ny_afternoon': 1.0 # Normal during NY afternoon
        }
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"   Confidence range: {self.confidence_floor:.0%} - {self.confidence_ceiling:.0%}")
        logger.info(f"   Optimal target: {self.confidence_optimal:.0%}")
        logger.info(f"   Risk multipliers: {self.risk_min_multiplier}x - {self.risk_max_multiplier}x")
    
    def analyze_market_conditions(
        self,
        market_data: Dict,
        recent_candles: Optional[List] = None
    ) -> MarketCondition:
        """
        Analyze current market conditions and return recommendations
        
        Args:
            market_data: Dict of current market prices/data
            recent_candles: Optional list of recent candles for analysis
            
        Returns:
            MarketCondition with recommended settings
        """
        
        # Calculate individual scores
        volatility_score = self._calculate_volatility_score(market_data, recent_candles)
        trend_strength = self._calculate_trend_strength(market_data, recent_candles)
        spread_quality = self._calculate_spread_quality(market_data)
        volume_score = self._calculate_volume_score(recent_candles)
        
        # Determine market regime
        regime = self._determine_regime(
            volatility_score,
            trend_strength,
            spread_quality
        )
        
        # Calculate overall quality score (weighted average)
        overall_quality = (
            volatility_score * self.weights['volatility'] +
            trend_strength * self.weights['trend'] +
            spread_quality * self.weights['spread'] +
            volume_score * self.weights['volume']
        )
        
        # Apply session adjustment
        session_type = self._get_current_session()
        session_multiplier = self.session_multipliers.get(session_type, 1.0)
        overall_quality *= session_multiplier
        
        # Cap between 0 and 1
        overall_quality = max(0.0, min(1.0, overall_quality))
        
        # Calculate recommended confidence threshold
        recommended_confidence = self._calculate_confidence_threshold(
            overall_quality,
            regime
        )
        
        # Calculate risk multiplier
        recommended_risk_multiplier = self._calculate_risk_multiplier(
            overall_quality,
            regime
        )
        
        # Calculate max positions
        recommended_max_positions = self._calculate_max_positions(
            overall_quality,
            regime
        )
        
        # Generate reason
        reason = self._generate_reason(
            regime,
            overall_quality,
            session_type,
            volatility_score,
            trend_strength
        )
        
        condition = MarketCondition(
            regime=regime,
            volatility_score=volatility_score,
            trend_strength=trend_strength,
            spread_quality=spread_quality,
            volume_score=volume_score,
            overall_quality=overall_quality,
            recommended_confidence=recommended_confidence,
            recommended_risk_multiplier=recommended_risk_multiplier,
            recommended_max_positions=recommended_max_positions,
            timestamp=datetime.now(),
            reason=reason
        )
        
        # Store in history
        self.condition_history.append(condition)
        if len(self.condition_history) > self.max_history:
            self.condition_history = self.condition_history[-self.max_history:]
        
        # Log the assessment
        logger.info(f"📊 Market Assessment: {regime.value.upper()}")
        logger.info(f"   Overall Quality: {overall_quality:.1%}")
        logger.info(f"   Recommended Confidence: {recommended_confidence:.1%}")
        logger.info(f"   Risk Multiplier: {recommended_risk_multiplier:.2f}x")
        logger.info(f"   Max Positions: {recommended_max_positions}")
        logger.info(f"   Reason: {reason}")
        
        return condition
    
    def _calculate_volatility_score(
        self,
        market_data: Dict,
        recent_candles: Optional[List]
    ) -> float:
        """
        Calculate volatility score (0-1)
        
        Perfect volatility: Medium (0.7-0.8)
        Too low: Hard to profit (0.3)
        Too high: Risky (0.5)
        """
        if not recent_candles or len(recent_candles) < 10:
            # Estimate from market data
            total_volatility = 0
            count = 0
            
            for pair_data in market_data.values():
                if hasattr(pair_data, 'volatility_score'):
                    total_volatility += pair_data.volatility_score
                    count += 1
            
            if count == 0:
                return 0.6  # Default medium
            
            avg_volatility = total_volatility / count
        else:
            # Calculate from candles (ATR-based)
            ranges = []
            for candle in recent_candles[-20:]:
                if 'high' in candle and 'low' in candle:
                    ranges.append(candle['high'] - candle['low'])
            
            if not ranges:
                return 0.6
            
            avg_range = sum(ranges) / len(ranges)
            # Normalize (assume 0.01% is low, 0.1% is high)
            avg_volatility = min(1.0, avg_range / 0.001)
        
        # Score: Prefer medium volatility
        if 0.4 <= avg_volatility <= 0.7:
            return 0.9  # Perfect
        elif 0.2 <= avg_volatility < 0.4:
            return 0.7  # Low but acceptable
        elif 0.7 < avg_volatility <= 0.9:
            return 0.8  # High but manageable
        elif avg_volatility < 0.2:
            return 0.4  # Too low
        else:
            return 0.5  # Too high
    
    def _calculate_trend_strength(
        self,
        market_data: Dict,
        recent_candles: Optional[List]
    ) -> float:
        """
        Calculate trend strength (0-1)
        
        Strong trend: High score (0.9)
        Ranging: Medium score (0.5)
        Choppy: Low score (0.3)
        """
        trending_count = 0
        ranging_count = 0
        total = 0
        
        for pair_data in market_data.values():
            if hasattr(pair_data, 'regime'):
                if pair_data.regime == 'trending':
                    trending_count += 1
                else:
                    ranging_count += 1
                total += 1
        
        if total == 0:
            return 0.5  # Default
        
        trending_ratio = trending_count / total
        
        # Score based on trending ratio
        if trending_ratio >= 0.7:
            return 0.9  # Most pairs trending
        elif trending_ratio >= 0.5:
            return 0.7  # Mixed but leaning trend
        elif trending_ratio >= 0.3:
            return 0.5  # Mixed
        else:
            return 0.4  # Mostly ranging
    
    def _calculate_spread_quality(self, market_data: Dict) -> float:
        """
        Calculate spread quality (0-1)
        
        Tight spreads: High score
        Wide spreads: Low score
        """
        spread_scores = []
        
        for pair_data in market_data.values():
            if hasattr(pair_data, 'spread'):
                spread_pips = pair_data.spread * 10000  # Convert to pips
                
                # Score based on spread
                if spread_pips < 1.0:
                    score = 1.0
                elif spread_pips < 2.0:
                    score = 0.9
                elif spread_pips < 3.0:
                    score = 0.7
                elif spread_pips < 5.0:
                    score = 0.5
                else:
                    score = 0.3
                
                spread_scores.append(score)
        
        if not spread_scores:
            return 0.7  # Default
        
        return sum(spread_scores) / len(spread_scores)
    
    def _calculate_volume_score(self, recent_candles: Optional[List]) -> float:
        """
        Calculate volume score (0-1)
        
        High volume: Good liquidity (0.9)
        Low volume: Poor liquidity (0.4)
        """
        if not recent_candles or len(recent_candles) < 5:
            # Default to medium during trading hours
            hour = datetime.now().hour
            if 8 <= hour <= 16:  # London/NY hours
                return 0.8
            else:
                return 0.5
        
        # Use volume from candles if available
        volumes = []
        for candle in recent_candles[-10:]:
            if 'volume' in candle:
                volumes.append(candle['volume'])
        
        if not volumes:
            return 0.7  # Default
        
        avg_volume = sum(volumes) / len(volumes)
        
        # Score based on volume
        if avg_volume > 3000:
            return 0.9
        elif avg_volume > 2000:
            return 0.8
        elif avg_volume > 1000:
            return 0.6
        else:
            return 0.5
    
    def _determine_regime(
        self,
        volatility: float,
        trend: float,
        spread: float
    ) -> MarketRegime:
        """Determine market regime from scores"""
        
        # Strong trending
        if trend >= 0.7 and volatility >= 0.6 and spread >= 0.7:
            return MarketRegime.TRENDING_STRONG
        
        # Weak trending
        elif trend >= 0.5 and volatility >= 0.4:
            return MarketRegime.TRENDING_WEAK
        
        # Tight ranging
        elif trend < 0.5 and volatility < 0.5:
            return MarketRegime.RANGING_TIGHT
        
        # Volatile ranging (dangerous)
        elif trend < 0.5 and volatility >= 0.7:
            return MarketRegime.RANGING_VOLATILE
        
        # Breakout conditions
        elif volatility >= 0.8 and trend >= 0.6:
            return MarketRegime.BREAKOUT
        
        # Whipsaw (very dangerous)
        elif spread < 0.5 and volatility >= 0.7:
            return MarketRegime.WHIPSAW
        
        else:
            return MarketRegime.RANGING_TIGHT
    
    def _get_current_session(self) -> str:
        """Determine current trading session"""
        hour = datetime.now().hour
        
        if 0 <= hour < 8:
            return 'asian'
        elif 8 <= hour < 13:
            return 'london'
        elif 13 <= hour < 17:
            return 'ny_overlap'
        else:
            return 'ny_afternoon'
    
    def _calculate_confidence_threshold(
        self,
        overall_quality: float,
        regime: MarketRegime
    ) -> float:
        """
        Calculate recommended confidence threshold
        
        Better conditions = Lower threshold (more trades)
        Worse conditions = Higher threshold (fewer, better trades)
        """
        
        # Base threshold calculation (inverse of quality)
        # High quality (0.9) -> Low threshold (0.62)
        # Low quality (0.3) -> High threshold (0.78)
        
        base_threshold = self.confidence_ceiling - (
            overall_quality * (self.confidence_ceiling - self.confidence_floor)
        )
        
        # Regime adjustments
        regime_adjustments = {
            MarketRegime.TRENDING_STRONG: -0.05,    # Lower threshold (more trades)
            MarketRegime.TRENDING_WEAK: 0.0,        # No adjustment
            MarketRegime.RANGING_TIGHT: +0.03,      # Slightly higher
            MarketRegime.RANGING_VOLATILE: +0.08,   # Much higher (selective)
            MarketRegime.BREAKOUT: -0.03,           # Slightly lower
            MarketRegime.WHIPSAW: +0.10            # Very high (avoid most trades)
        }
        
        adjustment = regime_adjustments.get(regime, 0.0)
        threshold = base_threshold + adjustment
        
        # Ensure within bounds
        threshold = max(self.confidence_floor, min(self.confidence_ceiling, threshold))
        
        return threshold
    
    def _calculate_risk_multiplier(
        self,
        overall_quality: float,
        regime: MarketRegime
    ) -> float:
        """
        Calculate position size multiplier
        
        Better conditions = Larger positions
        Worse conditions = Smaller positions
        """
        
        # Base multiplier from quality
        base_multiplier = self.risk_min_multiplier + (
            overall_quality * (self.risk_max_multiplier - self.risk_min_multiplier)
        )
        
        # Regime adjustments
        regime_multipliers = {
            MarketRegime.TRENDING_STRONG: 1.2,    # Increase size
            MarketRegime.TRENDING_WEAK: 1.0,      # Normal
            MarketRegime.RANGING_TIGHT: 0.8,      # Reduce size
            MarketRegime.RANGING_VOLATILE: 0.6,   # Much smaller
            MarketRegime.BREAKOUT: 1.1,           # Slightly larger
            MarketRegime.WHIPSAW: 0.5             # Very small
        }
        
        multiplier = base_multiplier * regime_multipliers.get(regime, 1.0)
        
        # Ensure within bounds
        multiplier = max(self.risk_min_multiplier, min(self.risk_max_multiplier, multiplier))
        
        return multiplier
    
    def _calculate_max_positions(
        self,
        overall_quality: float,
        regime: MarketRegime
    ) -> int:
        """Calculate recommended maximum positions"""
        
        if overall_quality >= 0.8:
            base_positions = 5
        elif overall_quality >= 0.6:
            base_positions = 3
        elif overall_quality >= 0.4:
            base_positions = 2
        else:
            base_positions = 1
        
        # Regime adjustments
        if regime in [MarketRegime.RANGING_VOLATILE, MarketRegime.WHIPSAW]:
            base_positions = max(1, base_positions - 1)
        elif regime == MarketRegime.TRENDING_STRONG:
            base_positions = min(5, base_positions + 1)
        
        return base_positions
    
    def _generate_reason(
        self,
        regime: MarketRegime,
        quality: float,
        session: str,
        volatility: float,
        trend: float
    ) -> str:
        """Generate human-readable explanation"""
        
        reasons = []
        
        # Regime
        if regime == MarketRegime.TRENDING_STRONG:
            reasons.append("Strong trends detected")
        elif regime == MarketRegime.RANGING_VOLATILE:
            reasons.append("Choppy/volatile - caution advised")
        elif regime == MarketRegime.WHIPSAW:
            reasons.append("Dangerous whipsaw conditions")
        else:
            reasons.append(f"{regime.value.replace('_', ' ').title()}")
        
        # Quality
        if quality >= 0.8:
            reasons.append("excellent market quality")
        elif quality >= 0.6:
            reasons.append("good market quality")
        elif quality >= 0.4:
            reasons.append("fair market quality")
        else:
            reasons.append("poor market quality")
        
        # Session
        if session == 'ny_overlap':
            reasons.append("prime time liquidity")
        elif session == 'london':
            reasons.append("London session active")
        elif session == 'asian':
            reasons.append("Asian session (lower liquidity)")
        
        # Volatility
        if volatility >= 0.8:
            reasons.append("high volatility")
        elif volatility <= 0.4:
            reasons.append("low volatility")
        
        return ", ".join(reasons)
    
    def get_current_condition(self) -> Optional[MarketCondition]:
        """Get the most recent market condition assessment"""
        if self.condition_history:
            return self.condition_history[-1]
        return None
    
    def should_trade(self, signal_confidence: float) -> Tuple[bool, str]:
        """
        Determine if a signal should be traded based on current conditions
        
        Returns:
            (should_trade: bool, reason: str)
        """
        current_condition = self.get_current_condition()
        
        if not current_condition:
            # No assessment yet, use default threshold
            if signal_confidence >= self.confidence_optimal:
                return True, f"Signal confidence {signal_confidence:.1%} meets default threshold"
            else:
                return False, f"Signal confidence {signal_confidence:.1%} below default threshold"
        
        # Check against adaptive threshold
        if signal_confidence >= current_condition.recommended_confidence:
            return True, (
                f"Signal confidence {signal_confidence:.1%} meets adaptive threshold "
                f"{current_condition.recommended_confidence:.1%} "
                f"({current_condition.regime.value})"
            )
        else:
            return False, (
                f"Signal confidence {signal_confidence:.1%} below adaptive threshold "
                f"{current_condition.recommended_confidence:.1%} "
                f"({current_condition.regime.value})"
            )
    
    def adjust_position_size(self, base_position_size: int) -> int:
        """
        Adjust position size based on current market conditions
        
        Args:
            base_position_size: Base position size before adjustment
            
        Returns:
            Adjusted position size
        """
        current_condition = self.get_current_condition()
        
        if not current_condition:
            return base_position_size  # No adjustment
        
        adjusted_size = int(base_position_size * current_condition.recommended_risk_multiplier)
        
        logger.info(
            f"Position sizing: {base_position_size} units × "
            f"{current_condition.recommended_risk_multiplier:.2f}x = {adjusted_size} units "
            f"(Market: {current_condition.regime.value})"
        )
        
        return adjusted_size
    
    def get_status_report(self) -> Dict:
        """Get current status report for monitoring"""
        current = self.get_current_condition()
        
        if not current:
            return {
                'status': 'No assessment yet',
                'confidence_threshold': self.confidence_optimal,
                'risk_multiplier': 1.0
            }
        
        return {
            'regime': current.regime.value,
            'overall_quality': f"{current.overall_quality:.1%}",
            'confidence_threshold': f"{current.recommended_confidence:.1%}",
            'risk_multiplier': f"{current.recommended_risk_multiplier:.2f}x",
            'max_positions': current.recommended_max_positions,
            'reason': current.reason,
            'timestamp': current.timestamp.isoformat(),
            'settings': {
                'floor': f"{self.confidence_floor:.0%}",
                'ceiling': f"{self.confidence_ceiling:.0%}",
                'optimal': f"{self.confidence_optimal:.0%}"
            }
        }


# Global singleton instance
_adaptive_analyzer = None

def get_adaptive_analyzer() -> AdaptiveMarketAnalyzer:
    """Get the global adaptive analyzer instance"""
    global _adaptive_analyzer
    if _adaptive_analyzer is None:
        _adaptive_analyzer = AdaptiveMarketAnalyzer()
    return _adaptive_analyzer


