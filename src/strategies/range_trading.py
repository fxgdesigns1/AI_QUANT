#!/usr/bin/env python3
"""
Range Trading Strategy - Mean-reversion strategy for sideways markets
Integrated with Adaptive Market Regime Detection (Critical for Range Trading)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from src.strategies.momentum_trading import TradeSignal, TradeSide

try:
    from src.control_plane.market_data_provider import get_candles
    from src.strategies.indicators import calculate_bollinger_bands, calculate_rsi, calculate_sma
    from src.core.market_regime import MarketRegimeDetector, MarketRegime
    from src.core.adaptive_system import AdaptiveMarketDetector, AdaptiveRiskManager, MarketCondition
    HAS_INDICATORS = True
except ImportError:
    HAS_INDICATORS = False
    logging.getLogger(__name__).warning("⚠️ Indicators module not available - using fallback logic")

logger = logging.getLogger(__name__)


class RangeTradingStrategy:
    """Mean-reversion strategy with Adaptive Regime Detection"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the strategy"""
        self.config = config or {}
        self.name = "range_trading"
        self.enabled = True
        
        self.bb_period = self.config.get('bb_period', 20)
        self.bb_std_dev = self.config.get('bb_std_dev', 2.0)
        self.base_confidence_threshold = self.config.get('confidence_threshold', 0.40)
        self.max_spread_pips_major_fx = self.config.get('max_spread_pips_major_fx', 2.0)
        
        # Initialize Adaptive Components
        if HAS_INDICATORS:
            self.regime_detector = MarketRegimeDetector()
            self.market_detector = AdaptiveMarketDetector()
            self.risk_manager = AdaptiveRiskManager()
        else:
            self.regime_detector = None
            self.market_detector = None
            self.risk_manager = None
            
        logger.info(f"RangeTradingStrategy initialized (Adaptive: {HAS_INDICATORS})")
    
    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[TradeSignal]:
        """Analyze market data"""
        if not self.enabled:
            return []
        
        signals = []
        if not market_data:
            return signals
        
        # News factor
        news_factor = 1.0
        if news_data and news_data.get('count', 0) > 20:
            news_factor = 0.95 # Range trading hates news
        
        for instrument, price_data in market_data.items():
            try:
                if not hasattr(price_data, 'bid') or not hasattr(price_data, 'ask'):
                    continue
                
                bid = float(price_data.bid)
                ask = float(price_data.ask)
                spread = ask - bid
                spread_pips = spread * 10000
                
                if spread_pips > self.max_spread_pips_major_fx:
                    continue
                
                # ADAPTIVE ANALYSIS
                regime = MarketRegime.UNKNOWN
                condition = MarketCondition.NORMAL
                risk_adj = None
                
                if HAS_INDICATORS and self.regime_detector:
                    try:
                        candles = get_candles(instrument, granularity="M5", count=60)
                        if candles and len(candles) >= 50:
                            regime_analysis = self.regime_detector.detect_regime(instrument, candles)
                            regime = regime_analysis.regime
                            
                            closes = [c.c for c in candles]
                            price_change = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
                            condition = self.market_detector.detect_condition(instrument, price_change, regime_analysis.volatility)
                            
                            risk_adj = self.risk_manager.get_risk_adjustment(condition, regime)
                    except Exception as e:
                        logger.warning(f"Adaptive analysis failed: {e}")

                # CRITICAL GUARD: Range trading MUST NOT run in TRENDING markets
                if regime == MarketRegime.TRENDING:
                    logger.debug(f"Skipping {instrument} - Regime is TRENDING (bad for Range)")
                    continue

                # BASE LOGIC
                confidence = 0.0
                
                if HAS_INDICATORS:
                    try:
                        # Re-fetch or use existing candles
                        candles = get_candles(instrument, granularity="M5", count=100)
                        if candles and len(candles) >= self.bb_period + 10:
                            closes = [c.c for c in candles]
                            bb_result = calculate_bollinger_bands(closes, period=self.bb_period, std_dev=self.bb_std_dev)
                            
                            if bb_result:
                                upper_band, middle_band, lower_band = bb_result
                                current_price = closes[-1]
                                bb_width = upper_band - lower_band
                                
                                bb_position = ((current_price - lower_band) / bb_width) * 100 if bb_width > 0 else 50
                                
                                base_confidence = 0.4
                                
                                # Buy at lower BB
                                if bb_position < 20: base_confidence += 0.25
                                elif bb_position < 30: base_confidence += 0.15
                                
                                # Sell logic (omitted for now as only BUY signals in stub)
                                
                                # Confirm range (SMA deviation)
                                sma_20 = calculate_sma(closes, period=20)
                                if sma_20:
                                    dev = abs(current_price - sma_20) / sma_20
                                    if dev < 0.001: base_confidence += 0.15
                                
                                confidence = max(0.0, min(1.0, base_confidence))
                    except Exception:
                        pass
                
                # APPLY ADAPTIVE FACTORS
                if risk_adj:
                    required_conf = self.base_confidence_threshold + risk_adj.confidence_threshold_modifier
                    if regime == MarketRegime.RANGING:
                        required_conf -= 0.05 # Easier to trade in Ranging
                else:
                    required_conf = self.base_confidence_threshold

                confidence *= news_factor
                confidence *= (1.0 - (spread_pips / self.max_spread_pips_major_fx) * 0.2)
                
                if confidence >= required_conf:
                    stop_distance = 0.0010
                    tp_distance = 0.0020
                    
                    entry_price = ask
                    stop_loss = entry_price - stop_distance
                    take_profit = entry_price + tp_distance
                    
                    signal = TradeSignal(
                        instrument=instrument,
                        side=TradeSide.BUY,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        metadata={
                            'regime': regime.value,
                            'condition': condition.value,
                            'confidence': confidence
                        }
                    )
                    signals.append(signal)
                    logger.info(f"📊 Range: BUY {instrument} @ {entry_price:.5f} | Conf: {confidence:.2f} | Regime: {regime.value}")
            
            except Exception as e:
                logger.warning(f"Error in Range strategy: {e}")
                
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'enabled': self.enabled,
            'type': 'range_adaptive',
            'status': 'active',
            'config': self.config
        }
