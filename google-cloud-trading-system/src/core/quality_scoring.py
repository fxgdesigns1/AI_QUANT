from datetime import datetime
#!/usr/bin/env python3
"""
Quality Scoring System - Comprehensive 0-100 Scoring
Evaluates trade quality based on multiple factors
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import math

# Import local modules
try:
    from .market_regime import get_market_regime_detector
    from .session_manager import get_session_manager, MarketSession
    from .price_context_analyzer import get_price_context_analyzer
    HAS_CONTEXT_MODULES = True
except ImportError:
    HAS_CONTEXT_MODULES = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QualityFactor(Enum):
    """Quality factors for scoring"""
    TREND_STRENGTH = "Trend Strength"
    MOMENTUM = "Momentum"
    VOLUME = "Volume"
    PATTERN_QUALITY = "Pattern Quality"
    SESSION_QUALITY = "Session Quality"
    NEWS_ALIGNMENT = "News Alignment"
    MULTI_TIMEFRAME = "Multi-Timeframe Alignment"
    KEY_LEVEL = "Key Level Proximity"
    RISK_REWARD = "Risk-Reward Ratio"
    HISTORICAL_WIN_RATE = "Historical Win Rate"

@dataclass
class QualityScore:
    """Quality score structure"""
    total_score: float  # 0-100 overall score
    factors: Dict[QualityFactor, float]  # Individual factor scores (0-100)
    explanation: str  # Human-readable explanation
    recommendation: str  # "strong_buy", "buy", "neutral", "sell", "strong_sell"
    confidence: float  # 0.0-1.0
    expected_win_rate: float  # 0.0-1.0
    expected_risk_reward: float  # Expected R:R ratio

class QualityScoring:
    """
    Comprehensive quality scoring system
    Evaluates trade quality based on multiple factors
    """
    
    def __init__(self):
        """Initialize quality scoring system"""
        self.name = "Quality Scoring System"
        
        # Factor weights (sum = 1.0)
        self.weights = {
            QualityFactor.TREND_STRENGTH: 0.15,
            QualityFactor.MOMENTUM: 0.15,
            QualityFactor.VOLUME: 0.10,
            QualityFactor.PATTERN_QUALITY: 0.10,
            QualityFactor.SESSION_QUALITY: 0.10,
            QualityFactor.NEWS_ALIGNMENT: 0.10,
            QualityFactor.MULTI_TIMEFRAME: 0.15,
            QualityFactor.KEY_LEVEL: 0.05,
            QualityFactor.RISK_REWARD: 0.05,
            QualityFactor.HISTORICAL_WIN_RATE: 0.05
        }
        
        # Recommendation thresholds
        self.recommendation_thresholds = {
            "strong_buy": 80,
            "buy": 65,
            "neutral": 50,
            "sell": 35,
            "strong_sell": 20
        }
        
        # Historical win rates by instrument
        self.historical_win_rates = {
            "XAU_USD": 0.75,  # Gold has high win rate
            "GBP_USD": 0.70,
            "EUR_USD": 0.65,
            "USD_JPY": 0.60,
            "AUD_USD": 0.60,
            "NZD_USD": 0.55
        }
        
        # Initialize context modules if available
        self.market_regime_detector = None
        self.session_manager = None
        self.price_context_analyzer = None
        
        if HAS_CONTEXT_MODULES:
            try:
                self.market_regime_detector = get_market_regime_detector()
                self.session_manager = get_session_manager()
                self.price_context_analyzer = get_price_context_analyzer()
                logger.info("✅ Context modules loaded for quality scoring")
            except Exception as e:
                logger.warning(f"⚠️ Error loading context modules: {e}")
        
        logger.info(f"✅ {self.name} initialized")
    
    def score_trade_quality(self, instrument: str, side: str, 
                           market_data: Dict[str, Any],
                           context: Optional[Dict[str, Any]] = None) -> QualityScore:
        """
        Calculate comprehensive quality score for a trade
        
        Args:
            instrument: Instrument being traded
            side: Trade direction ("BUY" or "SELL")
            market_data: Market data dictionary
            context: Optional additional context
            
        Returns:
            QualityScore object with detailed scoring
        """
        # Initialize factor scores
        factor_scores = {}
        explanations = []
        
        # Get base market data
        adx = market_data.get("adx", 0)
        momentum = market_data.get("momentum", 0)
        volume = market_data.get("volume", 0)
        
        # 1. Score trend strength (ADX)
        trend_score = self._score_trend_strength(adx)
        factor_scores[QualityFactor.TREND_STRENGTH] = trend_score
        explanations.append(f"Trend strength: {trend_score:.0f}/100 (ADX: {adx:.1f})")
        
        # 2. Score momentum
        momentum_score = self._score_momentum(momentum, side)
        factor_scores[QualityFactor.MOMENTUM] = momentum_score
        explanations.append(f"Momentum: {momentum_score:.0f}/100 ({momentum:.4f})")
        
        # 3. Score volume
        volume_score = self._score_volume(volume)
        factor_scores[QualityFactor.VOLUME] = volume_score
        explanations.append(f"Volume: {volume_score:.0f}/100")
        
        # 4. Score pattern quality
        pattern_score = 50  # Default neutral score
        if context and "pattern" in context:
            pattern_score = self._score_pattern_quality(context["pattern"])
        factor_scores[QualityFactor.PATTERN_QUALITY] = pattern_score
        explanations.append(f"Pattern quality: {pattern_score:.0f}/100")
        
        # 5. Score session quality
        session_score = self._score_session_quality(context.get("timestamp") if context else None)
        factor_scores[QualityFactor.SESSION_QUALITY] = session_score
        explanations.append(f"Session quality: {session_score:.0f}/100")
        
        # 6. Score news alignment
        news_score = self._score_news_alignment(instrument, side, context)
        factor_scores[QualityFactor.NEWS_ALIGNMENT] = news_score
        explanations.append(f"News alignment: {news_score:.0f}/100")
        
        # 7. Score multi-timeframe alignment
        mtf_score = self._score_multi_timeframe_alignment(instrument, side, context)
        factor_scores[QualityFactor.MULTI_TIMEFRAME] = mtf_score
        explanations.append(f"Multi-timeframe alignment: {mtf_score:.0f}/100")
        
        # 8. Score key level proximity
        key_level_score = self._score_key_level_proximity(instrument, side, context)
        factor_scores[QualityFactor.KEY_LEVEL] = key_level_score
        explanations.append(f"Key level proximity: {key_level_score:.0f}/100")
        
        # 9. Score risk-reward ratio
        rr_score = self._score_risk_reward(context.get("risk_reward", 1.0))
        factor_scores[QualityFactor.RISK_REWARD] = rr_score
        explanations.append(f"Risk-reward: {rr_score:.0f}/100 (R:R {context.get('risk_reward', 1.0):.1f})")
        
        # 10. Score historical win rate
        win_rate_score = self._score_historical_win_rate(instrument)
        factor_scores[QualityFactor.HISTORICAL_WIN_RATE] = win_rate_score
        explanations.append(f"Historical win rate: {win_rate_score:.0f}/100")
        
        # Calculate weighted total score
        total_score = 0
        for factor, score in factor_scores.items():
            total_score += score * self.weights[factor]
        
        # Round to nearest integer
        total_score = round(total_score)
        
        # Get recommendation
        recommendation = self._get_recommendation(total_score)
        
        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(factor_scores)
        
        # Calculate expected win rate
        expected_win_rate = self._calculate_expected_win_rate(total_score, instrument)
        
        # Calculate expected risk-reward
        expected_risk_reward = context.get("risk_reward", 1.0) if context else 1.0
        
        # Create explanation string
        explanation = " | ".join(explanations)
        
        return QualityScore(
            total_score=total_score,
            factors=factor_scores,
            explanation=explanation,
            recommendation=recommendation,
            confidence=confidence,
            expected_win_rate=expected_win_rate,
            expected_risk_reward=expected_risk_reward
        )
    
    def _score_trend_strength(self, adx: float) -> float:
        """
        Score trend strength based on ADX
        
        Args:
            adx: Average Directional Index value
            
        Returns:
            Score from 0-100
        """
        # ADX interpretation:
        # 0-15: Weak trend
        # 15-25: Developing trend
        # 25-50: Strong trend
        # 50+: Very strong trend
        
        if adx >= 50:
            return 100
        elif adx >= 25:
            return 75 + (adx - 25) * 25 / 25  # 75-100
        elif adx >= 15:
            return 50 + (adx - 15) * 25 / 10  # 50-75
        else:
            return adx * 50 / 15  # 0-50
    
    def _score_momentum(self, momentum: float, side: str) -> float:
        """
        Score momentum alignment with trade direction
        
        Args:
            momentum: Momentum value (-1 to 1)
            side: Trade direction ("BUY" or "SELL")
            
        Returns:
            Score from 0-100
        """
        # Normalize momentum to 0-1 range based on direction
        if side == "BUY":
            normalized = (momentum + 1) / 2  # -1 to 1 -> 0 to 1
        else:  # SELL
            normalized = (1 - momentum) / 2  # -1 to 1 -> 1 to 0 -> 0 to 1
        
        # Score based on normalized value
        return normalized * 100
    
    def _score_volume(self, volume: float) -> float:
        """
        Score volume relative to average
        
        Args:
            volume: Volume relative to average (1.0 = average)
            
        Returns:
            Score from 0-100
        """
        if volume >= 2.0:
            return 100
        elif volume >= 1.5:
            return 90
        elif volume >= 1.0:
            return 75
        elif volume >= 0.75:
            return 60
        elif volume >= 0.5:
            return 40
        elif volume >= 0.25:
            return 25
        else:
            return 10
    
    def _score_pattern_quality(self, pattern_data: Dict[str, Any]) -> float:
        """
        Score chart pattern quality
        
        Args:
            pattern_data: Pattern data dictionary
            
        Returns:
            Score from 0-100
        """
        # If no pattern data, return neutral score
        if not pattern_data:
            return 50
        
        # Get pattern strength if available
        strength = pattern_data.get("strength", 0.5)
        
        # Convert to 0-100 score
        return strength * 100
    
    def _score_session_quality(self, timestamp: Optional[datetime] = None) -> float:
        """
        Score trading session quality
        
        Args:
            timestamp: Optional timestamp to check
            
        Returns:
            Score from 0-100
        """
        if not self.session_manager:
            return 50  # Neutral if no session manager
        
        # Get session quality from session manager
        quality, active_sessions = self.session_manager.get_session_quality(timestamp)
        
        # Prime trading time (London-NY overlap) gets 100
        if self.session_manager.is_prime_trading_time(timestamp):
            return 100
        
        # Otherwise use quality score directly
        return quality
    
    def _score_news_alignment(self, instrument: str, side: str, 
                             context: Optional[Dict[str, Any]] = None) -> float:
        """
        Score alignment with news sentiment
        
        Args:
            instrument: Instrument being traded
            side: Trade direction ("BUY" or "SELL")
            context: Optional additional context
            
        Returns:
            Score from 0-100
        """
        # If no context or news data, return neutral score
        if not context or "news" not in context:
            return 50
        
        news_data = context["news"]
        sentiment = news_data.get("sentiment", 0)  # -1 to 1
        
        # Calculate alignment with trade direction
        if side == "BUY":
            alignment = (sentiment + 1) / 2  # -1 to 1 -> 0 to 1
        else:  # SELL
            alignment = (1 - sentiment) / 2  # -1 to 1 -> 1 to 0 -> 0 to 1
        
        # Impact multiplier (higher impact = stronger effect)
        impact = news_data.get("impact", "low")
        impact_multiplier = 1.0
        if impact == "high":
            impact_multiplier = 1.5
        elif impact == "medium":
            impact_multiplier = 1.2
        
        # Calculate final score (capped at 100)
        score = min(100, alignment * 100 * impact_multiplier)
        
        return score
    
    def _score_multi_timeframe_alignment(self, instrument: str, side: str,
                                        context: Optional[Dict[str, Any]] = None) -> float:
        """
        Score multi-timeframe trend alignment
        
        Args:
            instrument: Instrument being traded
            side: Trade direction ("BUY" or "SELL")
            context: Optional additional context
            
        Returns:
            Score from 0-100
        """
        # If no context or timeframe data, return neutral score
        if not context or "timeframes" not in context:
            return 50
        
        timeframes = context["timeframes"]
        
        # Count aligned timeframes
        aligned = 0
        total = 0
        
        for tf, tf_data in timeframes.items():
            if "trend" in tf_data:
                total += 1
                tf_trend = tf_data["trend"]
                
                # Check alignment with trade direction
                if (side == "BUY" and tf_trend == "bullish") or (side == "SELL" and tf_trend == "bearish"):
                    aligned += 1
        
        # Calculate alignment percentage
        if total == 0:
            return 50
        
        alignment = aligned / total
        
        # Convert to score (0.5 alignment = 50, 1.0 alignment = 100)
        return alignment * 100
    
    def _score_key_level_proximity(self, instrument: str, side: str,
                                  context: Optional[Dict[str, Any]] = None) -> float:
        """
        Score proximity to key support/resistance levels
        
        Args:
            instrument: Instrument being traded
            side: Trade direction ("BUY" or "SELL")
            context: Optional additional context
            
        Returns:
            Score from 0-100
        """
        # If no context or level data, return neutral score
        if not context:
            return 50
        
        # Check for support/resistance levels
        nearest_support = context.get("nearest_support")
        nearest_resistance = context.get("nearest_resistance")
        current_price = context.get("current_price", 0)
        
        if not nearest_support or not nearest_resistance or not current_price:
            return 50
        
        # Calculate distances to levels
        distance_to_support = abs(current_price - nearest_support) / current_price
        distance_to_resistance = abs(nearest_resistance - current_price) / current_price
        
        # For buys, we want to be close to support (buying at support)
        # For sells, we want to be close to resistance (selling at resistance)
        if side == "BUY":
            # Closer to support = better
            proximity = 1.0 - min(1.0, distance_to_support * 100)  # Normalize to 0-1
        else:  # SELL
            # Closer to resistance = better
            proximity = 1.0 - min(1.0, distance_to_resistance * 100)  # Normalize to 0-1
        
        # Convert to score
        return proximity * 100
    
    def _score_risk_reward(self, risk_reward: float) -> float:
        """
        Score risk-reward ratio
        
        Args:
            risk_reward: Risk-reward ratio (reward/risk)
            
        Returns:
            Score from 0-100
        """
        # R:R interpretation:
        # < 1.0: Poor
        # 1.0-1.5: Below average
        # 1.5-2.0: Average
        # 2.0-3.0: Good
        # 3.0+: Excellent
        
        if risk_reward >= 3.0:
            return 100
        elif risk_reward >= 2.0:
            return 80 + (risk_reward - 2.0) * 20
        elif risk_reward >= 1.5:
            return 60 + (risk_reward - 1.5) * 40
        elif risk_reward >= 1.0:
            return 40 + (risk_reward - 1.0) * 40
        else:
            return max(0, risk_reward * 40)
    
    def _score_historical_win_rate(self, instrument: str) -> float:
        """
        Score based on historical win rate for this instrument
        
        Args:
            instrument: Instrument being traded
            
        Returns:
            Score from 0-100
        """
        # Get historical win rate for this instrument
        win_rate = self.historical_win_rates.get(instrument, 0.5)
        
        # Convert to score (0.5 = 50, 0.75 = 75, etc.)
        return win_rate * 100
    
    def _get_recommendation(self, total_score: float) -> str:
        """
        Get recommendation based on total score
        
        Args:
            total_score: Total quality score (0-100)
            
        Returns:
            Recommendation string
        """
        if total_score >= self.recommendation_thresholds["strong_buy"]:
            return "strong_buy"
        elif total_score >= self.recommendation_thresholds["buy"]:
            return "buy"
        elif total_score >= self.recommendation_thresholds["neutral"]:
            return "neutral"
        elif total_score >= self.recommendation_thresholds["sell"]:
            return "sell"
        else:
            return "strong_sell"
    
    def _calculate_confidence(self, factor_scores: Dict[QualityFactor, float]) -> float:
        """
        Calculate confidence based on data completeness
        
        Args:
            factor_scores: Dictionary of factor scores
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Count factors with non-neutral scores
        non_neutral = 0
        for factor, score in factor_scores.items():
            if abs(score - 50) > 10:  # Not close to neutral
                non_neutral += 1
        
        # Calculate confidence based on data completeness
        return non_neutral / len(factor_scores)
    
    def _calculate_expected_win_rate(self, total_score: float, instrument: str) -> float:
        """
        Calculate expected win rate based on quality score
        
        Args:
            total_score: Total quality score (0-100)
            instrument: Instrument being traded
            
        Returns:
            Expected win rate (0.0-1.0)
        """
        # Get base win rate for this instrument
        base_win_rate = self.historical_win_rates.get(instrument, 0.5)
        
        # Adjust based on quality score
        # 50 = base win rate
        # 100 = base + 0.25 (capped at 0.95)
        # 0 = base - 0.25 (floored at 0.05)
        
        adjustment = (total_score - 50) / 200  # -0.25 to +0.25
        
        # Apply adjustment and clamp to 0.05-0.95
        return max(0.05, min(0.95, base_win_rate + adjustment))
    
    def get_adaptive_threshold(self, base_threshold: float, 
                              market_regime: str, 
                              session_quality: float) -> float:
        """
        Get adaptive threshold based on market regime and session quality
        
        Args:
            base_threshold: Base threshold value
            market_regime: Market regime ("TRENDING", "RANGING", "CHOPPY")
            session_quality: Session quality score (0-100)
            
        Returns:
            Adjusted threshold
        """
        # Regime multipliers
        regime_multipliers = {
            "TRENDING": 0.85,  # Lower threshold in trending markets
            "RANGING": 1.15,   # Higher threshold in ranging markets
            "CHOPPY": 1.30     # Much higher threshold in choppy markets
        }
        
        # Session quality multiplier (higher quality = lower threshold)
        session_multiplier = 1.0 - ((session_quality - 50) / 200)  # 0.75 to 1.25
        
        # Get regime multiplier (default to 1.0 if unknown)
        regime_multiplier = regime_multipliers.get(market_regime, 1.0)
        
        # Calculate final threshold
        return base_threshold * regime_multiplier * session_multiplier


# Global instance
_quality_scoring = None

def get_quality_scoring() -> QualityScoring:
    """Get the global quality scoring instance"""
    global _quality_scoring
    if _quality_scoring is None:
        _quality_scoring = QualityScoring()
    return _quality_scoring


if __name__ == "__main__":
    # Test quality scoring
    scorer = get_quality_scoring()
    
    # Test with minimal data
    minimal_data = {
        "adx": 25.0,
        "momentum": 0.5,
        "volume": 1.2
    }
    
    # Test with context data
    context = {
        "pattern": {
            "name": "Double Bottom",
            "strength": 0.8
        },
        "timestamp": None,
        "news": {
            "sentiment": 0.3,
            "impact": "medium"
        },
        "timeframes": {
            "M5": {"trend": "bullish"},
            "M15": {"trend": "bullish"},
            "H1": {"trend": "neutral"},
            "H4": {"trend": "bearish"}
        },
        "current_price": 1.2000,
        "nearest_support": 1.1950,
        "nearest_resistance": 1.2050,
        "risk_reward": 2.5
    }
    
    # Score a BUY trade
    buy_score = scorer.score_trade_quality("EUR_USD", "BUY", minimal_data, context)
    
    print(f"BUY Trade Quality Score: {buy_score.total_score}/100")
    print(f"Recommendation: {buy_score.recommendation}")
    print(f"Confidence: {buy_score.confidence:.2f}")
    print(f"Expected Win Rate: {buy_score.expected_win_rate:.2f}")
    print(f"Explanation: {buy_score.explanation}")
    
    # Score a SELL trade with same data
    sell_score = scorer.score_trade_quality("EUR_USD", "SELL", minimal_data, context)
    
    print(f"\nSELL Trade Quality Score: {sell_score.total_score}/100")
    print(f"Recommendation: {sell_score.recommendation}")
    
    # Test adaptive thresholds
    base_threshold = 0.5
    print(f"\nAdaptive Thresholds:")
    print(f"Base: {base_threshold}")
    print(f"Trending: {scorer.get_adaptive_threshold(base_threshold, 'TRENDING', 90):.4f}")
    print(f"Ranging: {scorer.get_adaptive_threshold(base_threshold, 'RANGING', 90):.4f}")
    print(f"Choppy: {scorer.get_adaptive_threshold(base_threshold, 'CHOPPY', 90):.4f}")
