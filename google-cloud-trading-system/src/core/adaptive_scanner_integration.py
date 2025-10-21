#!/usr/bin/env python3
"""
Adaptive Scanner Integration
Connects the AdaptiveMarketAnalyzer to the CandleBasedScanner
This is what SHOULD have been working from day 1!
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from .adaptive_market_analyzer import get_adaptive_analyzer, MarketCondition

logger = logging.getLogger(__name__)

class AdaptiveScannerMixin:
    """
    Mixin to add adaptive capabilities to CandleBasedScanner
    
    Features:
    - Monitors market conditions every scan
    - Automatically adjusts strategy thresholds
    - Loosens when no signals (0 signals for 1 hour → loosen 10%)
    - Tightens when too many losses (win rate < 60% → tighten 10%)
    - Adapts to market regime changes
    """
    
    def init_adaptive_system(self):
        """Initialize adaptive capabilities"""
        self.adaptive_analyzer = get_adaptive_analyzer()
        
        # Tracking
        self.last_signal_time = datetime.now()
        self.last_adaptation_time = datetime.now()
        self.signals_since_adaptation = 0
        self.wins_since_adaptation = 0
        self.losses_since_adaptation = 0
        
        # Settings
        self.adaptation_interval_minutes = 30  # Check every 30 min
        self.no_signal_threshold_minutes = 60  # Loosen if no signals for 1 hour
        self.loosen_amount = 0.10  # Loosen by 10% (0.35 → 0.315)
        self.tighten_amount = 0.05  # Tighten by 5%
        
        logger.info("✅ Adaptive scanner capabilities initialized")
    
    def check_and_adapt_thresholds(self):
        """
        Check if thresholds need adaptation
        Called every scan cycle
        """
        now = datetime.now()
        
        # Only adapt every N minutes
        minutes_since_adaptation = (now - self.last_adaptation_time).total_seconds() / 60
        if minutes_since_adaptation < self.adaptation_interval_minutes:
            return
        
        # Get current market condition
        condition = self.adaptive_analyzer.get_current_condition()
        
        # Check for no signals situation
        minutes_since_signal = (now - self.last_signal_time).total_seconds() / 60
        
        if minutes_since_signal > self.no_signal_threshold_minutes:
            self._loosen_all_thresholds(condition)
            self.last_adaptation_time = now
            logger.warning(f"⚠️ No signals for {minutes_since_signal:.0f} minutes - loosening thresholds")
        
        # Check win rate
        if self.signals_since_adaptation >= 10:  # Need at least 10 signals
            win_rate = self.wins_since_adaptation / self.signals_since_adaptation
            
            if win_rate < 0.60:
                self._tighten_all_thresholds(condition)
                self.last_adaptation_time = now
                logger.warning(f"⚠️ Win rate {win_rate:.1%} too low - tightening thresholds")
            elif win_rate > 0.80:
                self._loosen_all_thresholds(condition)
                self.last_adaptation_time = now
                logger.info(f"✅ Win rate {win_rate:.1%} excellent - loosening for more opportunities")
    
    def _loosen_all_thresholds(self, condition: MarketCondition):
        """Loosen all strategy thresholds"""
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'min_signal_strength'):
                old_val = strategy.min_signal_strength
                new_val = max(0.10, old_val * (1 - self.loosen_amount))  # Floor at 0.10
                strategy.min_signal_strength = new_val
                logger.info(f"📉 {name}: Loosened signal strength {old_val:.2f} → {new_val:.2f}")
            
            if hasattr(strategy, 'min_momentum'):
                old_val = strategy.min_momentum
                new_val = max(0.0003, old_val * (1 - self.loosen_amount))
                strategy.min_momentum = new_val
                logger.info(f"📉 {name}: Loosened momentum {old_val:.4f} → {new_val:.4f}")
        
        # Reset counters
        self.signals_since_adaptation = 0
        self.wins_since_adaptation = 0
        self.losses_since_adaptation = 0
    
    def _tighten_all_thresholds(self, condition: MarketCondition):
        """Tighten all strategy thresholds"""
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'min_signal_strength'):
                old_val = strategy.min_signal_strength
                new_val = min(0.50, old_val * (1 + self.tighten_amount))  # Cap at 0.50
                strategy.min_signal_strength = new_val
                logger.info(f"📈 {name}: Tightened signal strength {old_val:.2f} → {new_val:.2f}")
            
            if hasattr(strategy, 'min_momentum'):
                old_val = strategy.min_momentum
                new_val = min(0.005, old_val * (1 + self.tighten_amount))
                strategy.min_momentum = new_val
                logger.info(f"📈 {name}: Tightened momentum {old_val:.4f} → {new_val:.4f}")
        
        # Reset counters
        self.signals_since_adaptation = 0
        self.wins_since_adaptation = 0
        self.losses_since_adaptation = 0
    
    def apply_adaptive_thresholds(self):
        """
        Apply adaptive analyzer's recommended thresholds
        This uses the sophisticated market condition analysis
        """
        condition = self.adaptive_analyzer.get_current_condition()
        
        logger.info(f"📊 Market Regime: {condition.regime.value}")
        logger.info(f"📊 Recommended confidence: {condition.recommended_confidence:.1%}")
        logger.info(f"📊 Quality score: {condition.overall_quality:.1%}")
        
        # Apply recommended confidence to all strategies
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'min_signal_strength'):
                strategy.min_signal_strength = condition.recommended_confidence
                logger.info(f"🎯 {name}: Set adaptive threshold → {condition.recommended_confidence:.1%}")
    
    def record_signal_result(self, strategy_name: str, won: bool):
        """Record a signal result for adaptation tracking"""
        self.signals_since_adaptation += 1
        if won:
            self.wins_since_adaptation += 1
        else:
            self.losses_since_adaptation += 1
        
        self.last_signal_time = datetime.now()


def enable_adaptive_scanning(scanner_instance):
    """
    Enable adaptive capabilities on a CandleBasedScanner instance
    
    Usage:
        scanner = CandleBasedScanner()
        enable_adaptive_scanning(scanner)
        scanner.start_scanning()  # Now with adaptive features!
    """
    # Add mixin methods to scanner
    scanner_instance.init_adaptive_system = AdaptiveScannerMixin.init_adaptive_system.__get__(scanner_instance)
    scanner_instance.check_and_adapt_thresholds = AdaptiveScannerMixin.check_and_adapt_thresholds.__get__(scanner_instance)
    scanner_instance._loosen_all_thresholds = AdaptiveScannerMixin._loosen_all_thresholds.__get__(scanner_instance)
    scanner_instance._tighten_all_thresholds = AdaptiveScannerMixin._tighten_all_thresholds.__get__(scanner_instance)
    scanner_instance.apply_adaptive_thresholds = AdaptiveScannerMixin.apply_adaptive_thresholds.__get__(scanner_instance)
    scanner_instance.record_signal_result = AdaptiveScannerMixin.record_signal_result.__get__(scanner_instance)
    
    # Initialize
    scanner_instance.init_adaptive_system()
    scanner_instance.apply_adaptive_thresholds()  # Apply initial adaptive thresholds
    
    logger.info("✅ Adaptive scanning enabled!")
    return scanner_instance




