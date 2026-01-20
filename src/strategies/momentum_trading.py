#!/usr/bin/env python3
"""
Momentum Trading Strategy with Adaptive Components
Integrated with MarketRegimeDetector and AdaptiveSystem
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

try:
    from src.control_plane.market_data_provider import get_candles
    from src.strategies.indicators import calculate_rsi, calculate_macd, calculate_ema
    from src.core.market_regime import MarketRegimeDetector, MarketRegime
    from src.core.adaptive_system import AdaptiveMarketDetector, AdaptiveRiskManager, MarketCondition
    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    logging.getLogger(__name__).warning(f"⚠️ Dependencies not available - using fallback logic: {e}")

logger = logging.getLogger(__name__)


class TradeSide(Enum):
    """Trade direction"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class TradeSignal:
    """Trading signal structure"""
    instrument: str
    side: TradeSide
    entry_price: float
    stop_loss: float
    take_profit: float
    account_id: Optional[str] = None
    strategy_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MomentumTradingStrategy:
    """Momentum trading strategy with adaptive capabilities"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the strategy"""
        self.config = config or {}
        self.name = "momentum_trading"
        self.enabled = True
        
        # Core parameters
        self.min_adx = self.config.get('min_adx', 15)
        self.min_momentum = self.config.get('min_momentum', 0.003)
        self.min_volume = self.config.get('min_volume', 0.15)
        self.base_confidence_threshold = self.config.get('confidence_threshold', 0.40)
        self.max_trades_per_day = self.config.get('max_trades_per_day', 10)
        
        # Spread/slippage thresholds
        self.max_spread_pips_major_fx = self.config.get('max_spread_pips_major_fx', 2.0)
        self.max_spread_pips_xauusd = self.config.get('max_spread_pips_xauusd', 35.0)
        self.max_slippage_pips_major_fx = self.config.get('max_slippage_pips_major_fx', 1.0)
        self.max_slippage_pips_xauusd = self.config.get('max_slippage_pips_xauusd', 20.0)
        
        # Initialize Adaptive Components
        if HAS_DEPENDENCIES:
            self.regime_detector = MarketRegimeDetector()
            self.market_detector = AdaptiveMarketDetector()
            self.risk_manager = AdaptiveRiskManager()
        else:
            self.regime_detector = None
            self.market_detector = None
            self.risk_manager = None
            
        logger.info(f"MomentumTradingStrategy initialized (Adaptive: {HAS_DEPENDENCIES})")
    
    def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals (wrapper for legacy calls)"""
        # This method is kept for compatibility but should call analyze_market
        # For now returns empty list as per original stub behavior if needed
        # But logically should route to analyze_market if possible or be deprecated
        return [] 
    
    def calculate_position_size(self, signal: Dict[str, Any], account_balance: float) -> float:
        """Calculate position size"""
        # Simplified stub implementation
        return 0.0
    
    def should_exit_position(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """Check if position should be exited"""
        return False
    
    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[TradeSignal]:
        """Analyze market data and generate trading signals"""
        if not self.enabled:
            return []
        
        signals = []
        if not market_data:
            return signals

        # News Sentiment Impact
        news_factor = 1.0
        if news_data and news_data.get('count', 0) > 0:
            news_factor = 1.1
            logger.debug(f"News factor applied: {news_factor}")
        
        for instrument, price_data in market_data.items():
            try:
                # 1. Basic Data Extraction
                if not hasattr(price_data, 'bid') or not hasattr(price_data, 'ask'):
                    continue
                
                bid = float(price_data.bid)
                ask = float(price_data.ask)
                mid = (bid + ask) / 2.0
                spread = ask - bid
                
                # 2. Spread Checks
                is_xau = 'XAU' in instrument
                max_spread = self.max_spread_pips_xauusd if is_xau else self.max_spread_pips_major_fx
                
                if is_xau:
                    spread_pips = spread
                else:
                    spread_pips = spread * 10000
                
                if spread_pips > max_spread:
                    continue
                
                # 3. Adaptive Analysis (Regime & Condition)
                regime = MarketRegime.UNKNOWN
                condition = MarketCondition.NORMAL
                risk_adj = None
                
                if HAS_DEPENDENCIES and self.regime_detector:
                    try:
                        # Get historical data for regime detection
                        candles = get_candles(instrument, granularity="M5", count=100)
                        if candles and len(candles) >= 50:
                            # Detect Regime
                            regime_analysis = self.regime_detector.detect_regime(instrument, candles)
                            regime = regime_analysis.regime
                            
                            # Detect Condition (using volatility from regime analysis)
                            # Simplified price change check for condition
                            closes = [c.c for c in candles]
                            price_change = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
                            condition = self.market_detector.detect_condition(instrument, price_change, regime_analysis.volatility)
                            
                            # Get Risk Adjustments
                            risk_adj = self.risk_manager.get_risk_adjustment(condition, regime)
                            
                            logger.info(f"Analysis {instrument}: {regime.value} ({regime_analysis.description}), {condition.value}. Adj: {risk_adj.reason}")
                        else:
                            logger.warning(f"Insufficient candles for {instrument}")
                            continue
                            
                    except Exception as e:
                        logger.warning(f"Adaptive analysis failed for {instrument}: {e}")
                        continue
                else:
                    logger.warning("Adaptive dependencies missing, skipping analysis")
                    continue

                # 4. Technical Indicators & Momentum (Existing Logic)
                closes = [c.c for c in candles]
                rsi = calculate_rsi(closes, period=14)
                macd_result = calculate_macd(closes, fast=12, slow=26, signal=9)
                ema_fast = calculate_ema(closes, period=12)
                ema_slow = calculate_ema(closes, period=26)
                
                if rsi is None or macd_result is None:
                    continue
                    
                macd_line, signal_line, histogram = macd_result
                
                # 5. Calculate Base Confidence
                base_confidence = 0.5
                
                # RSI Logic
                if rsi < 40: base_confidence += 0.15
                elif rsi > 60: base_confidence -= 0.10
                
                # MACD Logic
                if macd_line > signal_line and histogram > 0: base_confidence += 0.15
                elif macd_line < signal_line: base_confidence -= 0.10
                
                # EMA Trend Logic
                if ema_fast and ema_slow and ema_fast > ema_slow:
                    base_confidence += 0.10
                
                # 6. Apply Adaptive Adjustments
                final_confidence = max(0.0, min(1.0, base_confidence))
                
                if risk_adj:
                    # Modify confidence threshold based on regime
                    required_confidence = self.base_confidence_threshold + risk_adj.confidence_threshold_modifier
                    
                    # Log adjustment impact
                    if risk_adj.confidence_threshold_modifier != 0:
                        logger.debug(f"Threshold adjusted: {self.base_confidence_threshold} -> {required_confidence:.2f} ({risk_adj.reason})")
                else:
                    required_confidence = self.base_confidence_threshold
                
                # Apply other factors
                final_confidence *= news_factor
                spread_factor = 1.0 - (spread_pips / max_spread) * 0.3
                final_confidence *= spread_factor
                
                # 7. Signal Generation
                if final_confidence >= required_confidence:
                    # Calculate stops based on risk multiplier
                    multiplier = risk_adj.stop_loss_multiplier if risk_adj else 1.0
                    
                    if is_xau:
                        stop_distance = 5.0 * multiplier
                        tp_distance = 15.0 # Keep TP static or adapt?
                    else:
                        stop_distance = 0.0010 * multiplier
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
                            'confidence': final_confidence,
                            'risk_adjustment': risk_adj.reason if risk_adj else "None"
                        }
                    )
                    signals.append(signal)
                    logger.info(f"📊 SIGNAL GENERATED: {instrument} {TradeSide.BUY.value} @ {entry_price:.5f} | Conf: {final_confidence:.2f} | Regime: {regime.value}")
                
            except Exception as e:
                logger.error(f"Error analyzing {instrument}: {e}")
                continue
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'type': 'momentum_adaptive',
            'status': 'active',
            'config': self.config
        }
