#!/usr/bin/env python3
"""
Adaptive Strategy Base Class
Integrates adaptive market analyzer with all strategies
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.core.adaptive_market_analyzer import get_adaptive_analyzer, MarketCondition

logger = logging.getLogger(__name__)


class AdaptiveStrategyMixin:
    """
    Mixin to add adaptive capabilities to any strategy
    
    Usage:
        class MyStrategy(AdaptiveStrategyMixin, BaseStrategy):
            def analyze(self, market_data):
                # Get adaptive assessment
                condition = self.assess_market_conditions(market_data)
                
                # Generate signals as normal
                signals = self.generate_signals(market_data)
                
                # Filter based on adaptive threshold
                filtered_signals = self.filter_by_adaptive_threshold(signals, condition)
                
                # Adjust position sizes
                adjusted_signals = self.adjust_position_sizes(filtered_signals, condition)
                
                return adjusted_signals
    """
    
    def __init__(self):
        """Initialize adaptive capabilities"""
        self.adaptive_analyzer = get_adaptive_analyzer()
        logger.info(f"✅ Adaptive capabilities enabled for {getattr(self, 'name', 'strategy')}")
    
    def assess_market_conditions(
        self,
        market_data: Dict,
        recent_candles: Optional[List] = None
    ) -> MarketCondition:
        """
        Assess current market conditions
        
        Args:
            market_data: Current market data
            recent_candles: Optional recent candle data
            
        Returns:
            MarketCondition with adaptive recommendations
        """
        return self.adaptive_analyzer.analyze_market_conditions(
            market_data,
            recent_candles
        )
    
    def should_trade_signal(self, signal_confidence: float) -> tuple[bool, str]:
        """
        Determine if a signal should be traded based on adaptive threshold
        
        Args:
            signal_confidence: Confidence level of the signal (0-1)
            
        Returns:
            (should_trade: bool, reason: str)
        """
        return self.adaptive_analyzer.should_trade(signal_confidence)
    
    def filter_by_adaptive_threshold(
        self,
        signals: List,
        condition: Optional[MarketCondition] = None
    ) -> List:
        """
        Filter signals based on adaptive confidence threshold
        
        Args:
            signals: List of trading signals
            condition: Market condition (if None, will get current)
            
        Returns:
            Filtered list of signals that meet adaptive threshold
        """
        if not signals:
            return []
        
        if condition is None:
            condition = self.adaptive_analyzer.get_current_condition()
        
        if condition is None:
            # No assessment yet, use default
            logger.warning("⚠️ No market assessment available, using default threshold")
            return [s for s in signals if getattr(s, 'confidence', 0) >= 0.65]
        
        filtered = []
        threshold = condition.recommended_confidence
        
        for signal in signals:
            signal_conf = getattr(signal, 'confidence', 0)
            should_trade, reason = self.should_trade_signal(signal_conf)
            
            if should_trade:
                filtered.append(signal)
                logger.info(
                    f"✅ Signal accepted: {signal_conf:.1%} confidence "
                    f"(threshold: {threshold:.1%}, {condition.regime.value})"
                )
            else:
                logger.info(
                    f"❌ Signal rejected: {signal_conf:.1%} confidence "
                    f"(threshold: {threshold:.1%}, {condition.regime.value})"
                )
        
        logger.info(
            f"📊 Adaptive filtering: {len(signals)} signals → {len(filtered)} accepted "
            f"(Market: {condition.regime.value}, Quality: {condition.overall_quality:.1%})"
        )
        
        return filtered
    
    def adjust_position_sizes(
        self,
        signals: List,
        condition: Optional[MarketCondition] = None
    ) -> List:
        """
        Adjust position sizes based on market conditions
        
        Args:
            signals: List of trading signals
            condition: Market condition (if None, will get current)
            
        Returns:
            Signals with adjusted position sizes
        """
        if not signals:
            return []
        
        if condition is None:
            condition = self.adaptive_analyzer.get_current_condition()
        
        if condition is None:
            logger.warning("⚠️ No market assessment, using default position sizes")
            return signals
        
        for signal in signals:
            if hasattr(signal, 'units'):
                original_units = signal.units
                adjusted_units = self.adaptive_analyzer.adjust_position_size(original_units)
                signal.units = adjusted_units
                
                logger.info(
                    f"📊 Position adjusted: {original_units} → {adjusted_units} units "
                    f"({condition.recommended_risk_multiplier:.2f}x, "
                    f"Market: {condition.regime.value})"
                )
        
        return signals
    
    def get_adaptive_max_positions(self) -> int:
        """Get recommended maximum positions for current conditions"""
        condition = self.adaptive_analyzer.get_current_condition()
        if condition:
            return condition.recommended_max_positions
        return 3  # Default
    
    def log_market_assessment(self):
        """Log current market assessment for transparency"""
        condition = self.adaptive_analyzer.get_current_condition()
        
        if not condition:
            logger.info("📊 No market assessment available yet")
            return
        
        logger.info("="*70)
        logger.info("📊 ADAPTIVE MARKET ASSESSMENT")
        logger.info("="*70)
        logger.info(f"Regime: {condition.regime.value.upper()}")
        logger.info(f"Overall Quality: {condition.overall_quality:.1%}")
        logger.info(f"Confidence Threshold: {condition.recommended_confidence:.1%}")
        logger.info(f"Risk Multiplier: {condition.recommended_risk_multiplier:.2f}x")
        logger.info(f"Max Positions: {condition.recommended_max_positions}")
        logger.info(f"Reason: {condition.reason}")
        logger.info("="*70)


def enable_adaptive_trading(strategy_instance):
    """
    Convenience function to add adaptive capabilities to an existing strategy
    
    Args:
        strategy_instance: Strategy instance to enhance
        
    Returns:
        Enhanced strategy with adaptive capabilities
    """
    if isinstance(strategy_instance, AdaptiveStrategyMixin):
        logger.info(f"✅ Strategy already has adaptive capabilities")
        return strategy_instance
    
    # Dynamically add adaptive capabilities
    strategy_instance.adaptive_analyzer = get_adaptive_analyzer()
    strategy_instance.assess_market_conditions = AdaptiveStrategyMixin.assess_market_conditions.__get__(strategy_instance)
    strategy_instance.should_trade_signal = AdaptiveStrategyMixin.should_trade_signal.__get__(strategy_instance)
    strategy_instance.filter_by_adaptive_threshold = AdaptiveStrategyMixin.filter_by_adaptive_threshold.__get__(strategy_instance)
    strategy_instance.adjust_position_sizes = AdaptiveStrategyMixin.adjust_position_sizes.__get__(strategy_instance)
    strategy_instance.get_adaptive_max_positions = AdaptiveStrategyMixin.get_adaptive_max_positions.__get__(strategy_instance)
    strategy_instance.log_market_assessment = AdaptiveStrategyMixin.log_market_assessment.__get__(strategy_instance)
    
    logger.info(f"✅ Adaptive capabilities added to {getattr(strategy_instance, 'name', 'strategy')}")
    
    return strategy_instance


