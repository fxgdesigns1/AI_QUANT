#!/usr/bin/env python3
"""
Momentum V2 Strategy - Enhanced momentum strategy with adaptive filters and volatility adjustment
Integrated with Adaptive Market Regime Detection
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from src.strategies.momentum_trading import TradeSignal, TradeSide
from src.strategies.base_strategy import BaseStrategy

try:
    from src.control_plane.market_data_provider import get_candles
    from src.strategies.indicators import calculate_rsi, calculate_macd, calculate_ema, calculate_atr
    from src.core.market_regime import MarketRegimeDetector, MarketRegime
    from src.core.adaptive_system import AdaptiveMarketDetector, AdaptiveRiskManager, MarketCondition
    HAS_INDICATORS = True
except ImportError:
    HAS_INDICATORS = False
    logging.getLogger(__name__).warning("⚠️ Indicators module not available - using fallback logic")

logger = logging.getLogger(__name__)


class MomentumV2Strategy(BaseStrategy):
    """Enhanced Momentum Strategy with Adaptive Logic"""
    
    STRATEGY_ID = "momentum_v2"
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the strategy"""
        super().__init__(config)
        self.name = "momentum_v2"
        self.enabled = True
        
        self.adaptive_rsi = self.config.get('adaptive_rsi', True)
        self.volatility_filter = self.config.get('volatility_filter', True)
        self.min_trend_strength = self.config.get('min_trend_strength', 0.6)
        self.base_confidence_threshold = self.config.get('confidence_threshold', 0.40)
        self.max_spread_pips_major_fx = self.config.get('max_spread_pips_major_fx', 2.0)
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
            
        logger.info(f"MomentumV2Strategy initialized (Adaptive: {HAS_INDICATORS})")
    
    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[TradeSignal]:
        """Analyze market data"""
        if not self.enabled:
            return []
        
        signals = []
        if not market_data:
            return signals
        
        news_factor = 1.0
        if news_data and news_data.get('count', 0) > 0:
            news_factor = 1.1
        
        for instrument, price_data in market_data.items():
            try:
                if not hasattr(price_data, 'bid') or not hasattr(price_data, 'ask'):
                    continue
                
                bid = float(price_data.bid)
                ask = float(price_data.ask)
                spread = ask - bid
                
                is_xau = 'XAU' in instrument
                max_spread = self.max_spread_pips_xauusd if is_xau else self.max_spread_pips_major_fx
                
                if is_xau:
                    spread_pips = spread
                else:
                    spread_pips = spread * 10000
                
                if spread_pips > max_spread:
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

                # BASE LOGIC
                confidence = 0.0
                trend_strength = 0.0
                
                if HAS_INDICATORS:
                    try:
                        # Re-fetch or use existing candles
                        candles = get_candles(instrument, granularity="M5", count=100)
                        if candles and len(candles) >= 50:
                            closes = [c.c for c in candles]
                            highs = [c.h for c in candles]
                            lows = [c.l for c in candles]
                            
                            rsi = calculate_rsi(closes, period=14)
                            macd_result = calculate_macd(closes, fast=12, slow=26, signal=9)
                            ema_fast = calculate_ema(closes, period=12)
                            ema_slow = calculate_ema(closes, period=26)
                            atr = calculate_atr(highs, lows, closes, period=14)
                            
                            if rsi and macd_result:
                                macd_line, signal_line, histogram = macd_result
                                base_confidence = 0.5
                                
                                # RSI
                                if rsi < 40: base_confidence += 0.15
                                elif rsi > 60: base_confidence -= 0.10
                                
                                # MACD
                                if macd_line > signal_line and histogram > 0: base_confidence += 0.20
                                elif macd_line < signal_line: base_confidence -= 0.15
                                
                                # Trend Strength
                                if ema_fast and ema_slow and ema_fast > ema_slow:
                                    trend_strength = min(1.0, (ema_fast - ema_slow) / ema_slow * 1000)
                                    base_confidence += 0.15 * trend_strength
                                
                                # Volatility Filter
                                if atr:
                                    current_price = closes[-1]
                                    atr_pct = atr / current_price if current_price > 0 else 0
                                    if atr_pct < 0.002: base_confidence += 0.10
                                    elif atr_pct > 0.005: base_confidence -= 0.10
                                
                                confidence = max(0.0, min(1.0, base_confidence))
                    except Exception:
                        pass
                
                # APPLY ADAPTIVE FACTORS
                if risk_adj:
                    required_conf = self.base_confidence_threshold + risk_adj.confidence_threshold_modifier
                    stop_mult = risk_adj.stop_loss_multiplier
                else:
                    required_conf = self.base_confidence_threshold
                    stop_mult = 1.0

                confidence *= news_factor
                confidence *= (1.0 - (spread_pips / max_spread) * 0.25)
                
                if trend_strength >= self.min_trend_strength or confidence >= required_conf * 1.2:
                    if confidence >= required_conf:
                        if is_xau:
                            stop_distance = 5.0 * stop_mult
                            tp_distance = 15.0
                        else:
                            stop_distance = 0.0010 * stop_mult
                            tp_distance = 0.0030
                        
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
                        logger.info(f"📊 Momentum V2: BUY {instrument} @ {entry_price:.5f} | Conf: {confidence:.2f} | Regime: {regime.value}")
            
            except Exception as e:
                logger.warning(f"Error in Momentum V2: {e}")
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'id': self.STRATEGY_ID,
            'enabled': self.enabled,
            'type': 'momentum_enhanced_adaptive',
            'status': 'active',
            'config': self.config
        }
