#!/usr/bin/env python3
"""
Gold Scalping Strategy - Scalping strategy optimized for XAU_USD
Tight stops, quick exits, session-specific signals
Integrated with Adaptive Market Regime Detection
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from src.strategies.momentum_trading import TradeSignal, TradeSide

try:
    from src.control_plane.market_data_provider import get_candles
    from src.strategies.indicators import calculate_atr, calculate_ema, calculate_rsi
    from src.core.market_regime import MarketRegimeDetector, MarketRegime
    from src.core.adaptive_system import AdaptiveMarketDetector, AdaptiveRiskManager, MarketCondition
    HAS_INDICATORS = True
except ImportError:
    HAS_INDICATORS = False
    logging.getLogger(__name__).warning("⚠️ Indicators module not available - using fallback logic")

logger = logging.getLogger(__name__)


class GoldScalpingStrategy:
    """Gold scalping strategy optimized for XAU_USD with Adaptive Logic"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the strategy"""
        self.config = config or {}
        self.name = "gold_scalping"
        self.enabled = True
        
        # Gold-specific parameters
        self.scalp_pip_target = self.config.get('scalp_pip_target', 5)
        self.stop_loss_pips = self.config.get('stop_loss_pips', 3)
        self.use_volume_filter = self.config.get('use_volume_filter', True)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.40)
        
        # Spread limits for Gold
        self.max_spread_pips_xauusd = self.config.get('max_spread_pips_xauusd', 35.0)
        
        # Initialize Adaptive Components
        if HAS_INDICATORS:
            self.regime_detector = MarketRegimeDetector()
            self.market_detector = AdaptiveMarketDetector()
            self.risk_manager = AdaptiveRiskManager()
        else:
            self.regime_detector = None
            self.market_detector = None
            self.risk_manager = None
            
        logger.info(f"GoldScalpingStrategy initialized (Adaptive: {HAS_INDICATORS})")
    
    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[TradeSignal]:
        """Analyze XAU_USD market data and generate scalping signals"""
        if not self.enabled:
            return []
        
        signals = []
        
        if not market_data:
            return signals
        
        # Filter to XAU_USD only (hard requirement for gold strategy)
        xau_data = market_data.get('XAU_USD')
        if not xau_data:
            return signals
        
        # News factor
        news_factor = 1.0
        if news_data and news_data.get('count', 0) > 0:
            news_factor = 1.1
        
        try:
            # Extract price data
            if not hasattr(xau_data, 'bid') or not hasattr(xau_data, 'ask'):
                return signals
            
            bid = float(xau_data.bid)
            ask = float(xau_data.ask)
            spread = ask - bid
            spread_pips = spread  # For XAU_USD, spread is in price units (USD)
            
            if spread_pips > self.max_spread_pips_xauusd:
                return signals
            
            # ADAPTIVE ANALYSIS
            regime = MarketRegime.UNKNOWN
            condition = MarketCondition.NORMAL
            risk_adj = None
            
            if HAS_INDICATORS and self.regime_detector:
                try:
                    candles = get_candles('XAU_USD', granularity="M5", count=60)
                    if candles and len(candles) >= 50:
                        # Detect Regime
                        regime_analysis = self.regime_detector.detect_regime('XAU_USD', candles)
                        regime = regime_analysis.regime
                        
                        # Detect Condition
                        closes = [c.c for c in candles]
                        price_change = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
                        condition = self.market_detector.detect_condition('XAU_USD', price_change, regime_analysis.volatility)
                        
                        # Get Risk Adjustments
                        risk_adj = self.risk_manager.get_risk_adjustment(condition, regime)
                except Exception as e:
                    logger.warning(f"Adaptive analysis failed for Gold: {e}")

            # BASE LOGIC
            confidence = 0.0
            
            if HAS_INDICATORS:
                try:
                    # Re-fetch or use existing candles
                    candles = get_candles('XAU_USD', granularity="M5", count=50)
                    if candles and len(candles) >= 20:
                        closes = [c.c for c in candles]
                        highs = [c.h for c in candles]
                        lows = [c.l for c in candles]
                        
                        atr = calculate_atr(highs, lows, closes, period=14)
                        ema_fast = calculate_ema(closes, period=5)
                        ema_slow = calculate_ema(closes, period=12)
                        rsi = calculate_rsi(closes, period=14)
                        
                        if atr is not None:
                            current_price = closes[-1]
                            base_confidence = 0.5
                            
                            # Volatility check
                            atr_pct = atr / current_price if current_price > 0 else 0
                            if 0.002 < atr_pct < 0.008:
                                base_confidence += 0.15
                            
                            # Trend
                            if ema_fast and ema_slow and ema_fast > ema_slow:
                                base_confidence += 0.15
                            
                            # RSI
                            if rsi and 30 < rsi < 50:
                                base_confidence += 0.10
                            
                            confidence = max(0.0, min(1.0, base_confidence))
                except Exception:
                    pass
            
            # APPLY ADAPTIVE FACTORS
            if risk_adj:
                # Adjust confidence threshold
                required_conf = self.confidence_threshold + risk_adj.confidence_threshold_modifier
                
                # Scalping logic adjustments
                if condition == MarketCondition.HIGH_VOLATILITY:
                    # In high volatility, widen stops and targets
                    stop_mult = 1.5
                    target_mult = 1.5
                else:
                    stop_mult = 1.0
                    target_mult = 1.0
            else:
                required_conf = self.confidence_threshold
                stop_mult = 1.0
                target_mult = 1.0

            # Final confidence adjustments
            confidence *= news_factor
            spread_factor = 1.0 - (spread_pips / self.max_spread_pips_xauusd) * 0.3
            confidence *= spread_factor
            
            if confidence >= required_conf:
                stop_distance = float(self.stop_loss_pips) * stop_mult
                tp_distance = float(self.scalp_pip_target) * target_mult
                
                entry_price = ask
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + tp_distance
                
                signal = TradeSignal(
                    instrument='XAU_USD',
                    side=TradeSide.BUY,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        'regime': regime.value,
                        'condition': condition.value,
                        'confidence': confidence,
                        'risk_adjustment': risk_adj.reason if risk_adj else "None"
                    }
                )
                signals.append(signal)
                logger.info(f"📊 Gold Scalping: BUY XAU_USD @ {entry_price:.2f} | Conf: {confidence:.2f} | Regime: {regime.value}")
        
        except Exception as e:
            logger.warning(f"Error in Gold Scalping: {e}")
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'enabled': self.enabled,
            'type': 'gold_scalping_adaptive',
            'status': 'active',
            'config': self.config
        }
