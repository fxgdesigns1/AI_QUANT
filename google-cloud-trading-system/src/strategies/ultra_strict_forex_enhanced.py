#!/usr/bin/env python3
"""
Enhanced Ultra Strict Forex Trading Strategy with Safe News Integration
NON-BREAKING enhancement that preserves all existing functionality
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd

# Import existing components
from ..core.order_manager import TradeSignal, OrderSide, get_order_manager
from ..core.data_feed import MarketData, get_data_feed
from ..core.news_integration import safe_news_integration

# Import existing strategy
from .ultra_strict_forex_optimized import UltraStrictForexStrategy, EMASignal, MomentumSignal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedUltraStrictForexStrategy(UltraStrictForexStrategy):
    """Enhanced Ultra Strict Forex Strategy with safe news integration"""
    
    def __init__(self):
        """Initialize enhanced strategy"""
        # Call parent constructor to preserve all existing functionality
        super().__init__()
        
        # Add news integration
        self.news_enabled = True
        self.news_pause_threshold = -0.3
        self.news_boost_threshold = 0.2
        
        logger.info("✅ Enhanced Ultra Strict Forex Strategy initialized with news integration")
    
    def analyze_market(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Enhanced market analysis with news awareness"""
        try:
            # Check news-based trading pause
            if self.news_enabled and safe_news_integration.should_pause_trading():
                logger.info("🚫 Trading paused due to news analysis")
                return []
            
            # Get existing technical analysis
            technical_signals = super().analyze_market(market_data)
            
            if not technical_signals:
                return []
            
            # Apply news-based enhancements
            enhanced_signals = []
            for signal in technical_signals:
                enhanced_signal = self._apply_news_enhancements(signal)
                if enhanced_signal:
                    enhanced_signals.append(enhanced_signal)
            
            logger.info(f"📊 Enhanced analysis: {len(enhanced_signals)} signals with news awareness")
            return enhanced_signals
            
        except Exception as e:
            logger.error(f"❌ Enhanced market analysis failed: {e}")
            # Fallback to existing method
            return super().analyze_market(market_data)
    
    def _apply_news_enhancements(self, signal: TradeSignal) -> Optional[TradeSignal]:
        """Apply news-based enhancements to trading signal"""
        try:
            if not self.news_enabled:
                return signal
            
            # Get news analysis
            news_analysis = safe_news_integration.get_news_analysis()
            
            # Apply news-based boost factor
            boost_factor = safe_news_integration.get_news_boost_factor(
                signal.side.value, 
                [signal.instrument]
            )
            
            # Adjust signal confidence
            signal.confidence = min(signal.confidence * boost_factor, 1.0)
            
            # Adjust position size based on news
            if boost_factor > 1.0:
                signal.quantity = signal.quantity * 1.1
                logger.info(f"📈 News boost applied to {signal.instrument} {signal.side.value}")
            elif boost_factor < 1.0:
                signal.quantity = signal.quantity * 0.9
                logger.info(f"📉 News reduction applied to {signal.instrument} {signal.side.value}")
            
            # Add news metadata
            if not hasattr(signal, 'metadata'):
                signal.metadata = {}
            
            signal.metadata.update({
                'news_sentiment': news_analysis['overall_sentiment'],
                'news_impact': news_analysis['market_impact'],
                'news_recommendation': news_analysis['trading_recommendation'],
                'news_confidence': news_analysis['confidence'],
                'news_boost_factor': boost_factor
            })
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ News enhancement failed: {e}")
            return signal
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get enhanced strategy status"""
        status = super().get_strategy_status()
        
        # Add news integration status
        status.update({
            'news_integration': {
                'enabled': self.news_enabled,
                'pause_threshold': self.news_pause_threshold,
                'boost_threshold': self.news_boost_threshold,
                'api_status': 'enabled' if safe_news_integration.enabled else 'disabled'
            }
        })
        
        return status

# Global instance
enhanced_ultra_strict_forex_strategy = EnhancedUltraStrictForexStrategy()
