#!/usr/bin/env python3
"""
EUR/USD 5M Safe Strategy - Conservative EUR/USD strategy with strict risk controls
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
    from src.strategies.indicators import calculate_rsi, calculate_ema, calculate_sma, calculate_atr
    from src.core.market_regime import MarketRegimeDetector, MarketRegime
    from src.core.adaptive_system import AdaptiveMarketDetector, AdaptiveRiskManager, MarketCondition
    HAS_INDICATORS = True
except ImportError:
    HAS_INDICATORS = False
    logging.getLogger(__name__).warning("⚠️ Indicators module not available - using fallback logic")

logger = logging.getLogger(__name__)


class EurUsd5mSafeStrategy:
    """Conservative EUR/USD strategy with Adaptive Logic"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the strategy"""
        self.config = config or {}
        self.name = "eur_usd_5m_safe"
        self.enabled = True
        
        self.min_pip_distance = self.config.get('min_pip_distance', 10)
        self.max_spread_pips = self.config.get('max_spread_pips', 2)
        self.base_confidence_threshold = self.config.get('confidence_threshold', 0.50)
        
        # Initialize Adaptive Components
        if HAS_INDICATORS:
            self.regime_detector = MarketRegimeDetector()
            self.market_detector = AdaptiveMarketDetector()
            self.risk_manager = AdaptiveRiskManager()
        else:
            self.regime_detector = None
            self.market_detector = None
            self.risk_manager = None
            
        logger.info(f"EurUsd5mSafeStrategy initialized (Adaptive: {HAS_INDICATORS})")
    
    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[TradeSignal]:
        """Analyze EUR/USD market data"""
        if not self.enabled:
            return []
        
        signals = []
        if not market_data:
            return signals
        
        eur_usd_data = market_data.get('EUR_USD')
        if not eur_usd_data:
            return signals
        
        # News factor
        news_factor = 1.0
        if news_data and news_data.get('count', 0) > 15:
            news_factor = 0.90 # Conservative reduction
            
        try:
            if not hasattr(eur_usd_data, 'bid') or not hasattr(eur_usd_data, 'ask'):
                return signals
            
            bid = float(eur_usd_data.bid)
            ask = float(eur_usd_data.ask)
            spread = ask - bid
            spread_pips = spread * 10000
            
            if spread_pips > self.max_spread_pips:
                return signals
            
            # ADAPTIVE ANALYSIS
            regime = MarketRegime.UNKNOWN
            condition = MarketCondition.NORMAL
            risk_adj = None
            
            if HAS_INDICATORS and self.regime_detector:
                try:
                    candles = get_candles('EUR_USD', granularity="M5", count=60)
                    if candles and len(candles) >= 50:
                        regime_analysis = self.regime_detector.detect_regime('EUR_USD', candles)
                        regime = regime_analysis.regime
                        
                        closes = [c.c for c in candles]
                        price_change = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
                        condition = self.market_detector.detect_condition('EUR_USD', price_change, regime_analysis.volatility)
                        
                        risk_adj = self.risk_manager.get_risk_adjustment(condition, regime)
                except Exception as e:
                    logger.warning(f"Adaptive analysis failed for EURUSD: {e}")

            # BASE LOGIC
            confidence = 0.0
            
            if HAS_INDICATORS:
                try:
                    # Re-fetch or use existing candles
                    candles = get_candles('EUR_USD', granularity="M5", count=100)
                    if candles and len(candles) >= 50:
                        closes = [c.c for c in candles]
                        highs = [c.h for c in candles]
                        lows = [c.l for c in candles]
                        
                        rsi = calculate_rsi(closes, period=14)
                        ema_fast = calculate_ema(closes, period=12)
                        ema_slow = calculate_ema(closes, period=26)
                        sma_20 = calculate_sma(closes, period=20)
                        
                        if rsi and ema_fast and ema_slow:
                            current_price = closes[-1]
                            base_confidence = 0.5
                            confirmations = 0
                            
                            # 1. RSI
                            if 35 < rsi < 65:
                                base_confidence += 0.10
                                confirmations += 1
                            
                            # 2. Trend
                            if ema_fast > ema_slow:
                                base_confidence += 0.15
                                confirmations += 1
                            
                            # 3. SMA
                            if sma_20 and current_price > sma_20:
                                base_confidence += 0.10
                                confirmations += 1
                            
                            if confirmations >= 2:
                                confidence = max(0.0, min(1.0, base_confidence))
                except Exception:
                    pass
            
            # APPLY ADAPTIVE FACTORS
            if risk_adj:
                required_conf = self.base_confidence_threshold + risk_adj.confidence_threshold_modifier
                
                # In CHOPPY regime, disable this TREND-following strategy?
                if regime == MarketRegime.CHOPPY:
                    required_conf += 0.20 # Make it very hard to trade
                
                stop_mult = risk_adj.stop_loss_multiplier
            else:
                required_conf = self.base_confidence_threshold
                stop_mult = 1.0

            # Final adjustments
            confidence *= news_factor
            spread_factor = 1.0 - (spread_pips / self.max_spread_pips) * 0.15
            confidence *= spread_factor
            
            if confidence >= required_conf:
                stop_distance = 0.0010 * stop_mult
                tp_distance = 0.0030
                
                entry_price = ask
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + tp_distance
                
                signal = TradeSignal(
                    instrument='EUR_USD',
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
                logger.info(f"📊 EUR/USD Safe: BUY @ {entry_price:.5f} | Conf: {confidence:.2f} | Regime: {regime.value}")
        
        except Exception as e:
            logger.warning(f"Error in EUR/USD Safe: {e}")
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'enabled': self.enabled,
            'type': 'conservative_adaptive',
            'status': 'active',
            'config': self.config
        }
