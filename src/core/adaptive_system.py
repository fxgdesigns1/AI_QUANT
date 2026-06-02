import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from .market_regime import MarketRegime

logger = logging.getLogger(__name__)

class MarketCondition(Enum):
    NORMAL = "normal"
    ELEVATED_VOLATILITY = "elevated_volatility"
    HIGH_VOLATILITY = "high_volatility"
    CENTRAL_BANK_EVENT = "central_bank_event"
    MOMENTUM_REVERSAL = "momentum_reversal"
    RISK_OFF = "risk_off"

@dataclass
class RiskAdjustment:
    position_size_multiplier: float
    stop_loss_multiplier: float
    confidence_threshold_modifier: float
    reason: str

class AdaptiveMarketDetector:
    """
    Detects market conditions that require strategy adaptations.
    """
    
    def __init__(self):
        self.thresholds = {
            'high_volatility': 0.02,  # 2% price change
            'elevated_volatility': 0.01,  # 1% price change
        }
        
    def detect_condition(self, instrument: str, price_change_pct: float, volatility: float) -> MarketCondition:
        """
        Detect current market condition based on recent metrics.
        """
        abs_change = abs(price_change_pct)
        
        if abs_change >= self.thresholds['high_volatility']:
            return MarketCondition.HIGH_VOLATILITY
        elif abs_change >= self.thresholds['elevated_volatility']:
            return MarketCondition.ELEVATED_VOLATILITY
            
        # Could add more complex logic here (news checks, etc.)
        return MarketCondition.NORMAL

class AdaptiveRiskManager:
    """
    Dynamically adjusts risk based on market conditions.
    """
    
    def get_risk_adjustment(self, condition: MarketCondition, regime: MarketRegime) -> RiskAdjustment:
        """
        Get risk multipliers and modifiers based on market state.
        """
        # Defaults
        size_mult = 1.0
        sl_mult = 1.0
        conf_mod = 0.0
        reasons = []
        
        # 1. Adapt to Volatility Condition
        if condition == MarketCondition.HIGH_VOLATILITY:
            size_mult *= 0.5   # Cut size in half
            sl_mult *= 2.0     # Double stops
            conf_mod += 0.15   # Need 15% more confidence
            reasons.append("High Volatility")
        elif condition == MarketCondition.ELEVATED_VOLATILITY:
            size_mult *= 0.75
            sl_mult *= 1.5
            conf_mod += 0.05
            reasons.append("Elevated Volatility")
            
        # 2. Adapt to Market Regime
        if regime == MarketRegime.TRENDING:
            size_mult *= 1.2   # Slightly larger position in trends
            conf_mod -= 0.05   # Slightly easier entry (catch pullbacks)
            reasons.append("Trending Market")
        elif regime == MarketRegime.CHOPPY:
            size_mult *= 0.5   # Reduce size significantly
            conf_mod += 0.20   # Harder entry
            reasons.append("Choppy Market")
        elif regime == MarketRegime.RANGING:
            conf_mod += 0.10   # Need more confirmation
            reasons.append("Ranging Market")
            
        return RiskAdjustment(
            position_size_multiplier=max(0.1, min(2.0, size_mult)),
            stop_loss_multiplier=max(0.5, min(3.0, sl_mult)),
            confidence_threshold_modifier=conf_mod,
            reason=", ".join(reasons)
        )
