#!/usr/bin/env python3
"""
Gold Scalping Strategy - Scalping strategy optimized for XAU_USD
Tight stops, quick exits, session-specific signals
Integrated with Adaptive Market Regime Detection
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import statistics

from src.strategies.momentum_trading import TradeSignal, TradeSide, DecisionReason
import json
from src.strategies.base_strategy import BaseStrategy

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


class GoldScalpingStrategy(BaseStrategy):
    """Gold scalping strategy optimized for XAU_USD with Adaptive Logic"""
    
    STRATEGY_ID = "gold_scalping"
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the strategy"""
        super().__init__(config)
        self.name = "gold_scalping"
        
        # Gold-specific parameters
        self.scalp_pip_target = self.config.get('scalp_pip_target', 5)
        self.stop_loss_pips = self.config.get('stop_loss_pips', 3)
        self.use_volume_filter = self.config.get('use_volume_filter', True)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.40)
        
        # Spread limits for Gold
        self.max_spread_pips_xauusd = self.config.get('max_spread_pips_xauusd', 35.0)
        
        # Stage 3: Session and trade management
        self.last_session_trade_time: Optional[datetime] = None
        self.session_trade_count = 0
        self.last_trade_loss = False
        # Raise confidence threshold for quality-only scalps
        self.confidence_threshold = max(self.confidence_threshold, 0.55)  # Minimum 0.55
        
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

    def _log_decision(self, instrument: str, decision: str, reason: DecisionReason, metadata: Dict[str, Any] = None):
        """Log trading decision with structured format"""
        log_data = {
            "account_id": getattr(self, "account_id", "002"), # Default to 002 for gold
            "strategy": self.STRATEGY_ID,
            "instrument": instrument,
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "reason": reason.value,
            "metadata": metadata or {}
        }
        logger.info(f"DECISION_{decision}: {json.dumps(log_data)}")
    
    def _is_trading_session(self) -> bool:
        """Check if current time is within London or NY session (Stage 3)"""
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        # London: 7-16 UTC, NY: 12-21 UTC
        # Combined: 7-21 UTC (London + NY overlap)
        return 7 <= hour < 21
    
    def _reset_session_state_if_new_session(self):
        """Reset session trade count if new session started (Stage 3)"""
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        
        # Check if we've crossed into a new session day
        if self.last_session_trade_time:
            days_diff = (current_time.date() - self.last_session_trade_time.date()).days
            if days_diff > 0:
                self.session_trade_count = 0
                self.last_trade_loss = False
                self.last_session_trade_time = None
        elif hour < 7:  # Before London opens, reset
            self.session_trade_count = 0
            self.last_trade_loss = False

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
        
        # Stage 3: Session filter
        self._reset_session_state_if_new_session()
        if not self._is_trading_session():
            self._log_decision('XAU_USD', "SKIP", DecisionReason.OUTSIDE_SESSION, {"utc_hour": datetime.now(timezone.utc).hour})
            return signals
        
        # Stage 3: Max trades per session + stop after first loss
        if self.session_trade_count >= 1:
            self._log_decision('XAU_USD', "SKIP", DecisionReason.RISK_TOO_HIGH, {"reason": "Max trades per session reached", "count": self.session_trade_count})
            return signals
        
        if self.last_trade_loss:
            self._log_decision('XAU_USD', "SKIP", DecisionReason.RISK_TOO_HIGH, {"reason": "Stop after first loss"})
            return signals
        
        # News factor
        news_factor = 1.0
        if news_data and news_data.get('count', 0) > 0:
            news_factor = 1.1
        
        try:
            # Extract price data
            if not hasattr(xau_data, 'bid') or not hasattr(xau_data, 'ask'):
                self._log_decision('XAU_USD', "SKIP", DecisionReason.MISSING_DATA, {"error": "Missing bid/ask"})
                return signals
            
            bid = float(xau_data.bid)
            ask = float(xau_data.ask)
            spread = ask - bid
            spread_pips = spread  # For XAU_USD, spread is in price units (USD)
            
            if spread_pips > self.max_spread_pips_xauusd:
                self._log_decision('XAU_USD', "SKIP", DecisionReason.SPREAD_TOO_HIGH, {"spread": spread_pips, "max": self.max_spread_pips_xauusd})
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
                    else:
                        self._log_decision('XAU_USD', "SKIP", DecisionReason.MISSING_DATA, {"reason": "Insufficient candles"})
                        return signals
                except Exception as e:
                    logger.warning(f"Adaptive analysis failed for Gold: {e}")
                    self._log_decision('XAU_USD', "SKIP", DecisionReason.MISSING_DATA, {"error": str(e)})

            # BASE LOGIC
            confidence = 0.0
            
            if HAS_INDICATORS:
                try:
                    # Re-fetch or use existing candles
                    if 'candles' not in locals() or not candles:
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
                            
                            # Stage 3: Volatility/spread gate
                            # ATR must exceed minimum AND spread < X% of TP distance
                            atr_pct = atr / current_price if current_price > 0 else 0
                            min_atr_pct = 0.0015  # Minimum 0.15% volatility
                            
                            if atr_pct < min_atr_pct:
                                self._log_decision('XAU_USD', "SKIP", DecisionReason.LOW_VOLATILITY, {"atr_pct": atr_pct, "min": min_atr_pct})
                                return signals
                            
                            # Calculate TP distance and check spread efficiency
                            tp_distance = float(self.scalp_pip_target)
                            spread_pct_of_tp = (spread_pips / tp_distance) * 100 if tp_distance > 0 else 100
                            max_spread_pct = 20.0  # Spread must be < 20% of TP distance
                            
                            if spread_pct_of_tp >= max_spread_pct:
                                self._log_decision('XAU_USD', "SKIP", DecisionReason.SPREAD_TOO_HIGH, {"spread_pct_of_tp": spread_pct_of_tp, "max": max_spread_pct})
                                return signals
                            
                            base_confidence = 0.5
                            
                            # Volatility check - WIDENED for strong trends
                            # Allow higher volatility (up to 2.5%) for strong trends
                            if 0.002 < atr_pct < 0.025:
                                base_confidence += 0.15
                            
                            # Trend
                            if ema_fast and ema_slow and ema_fast > ema_slow:
                                base_confidence += 0.15
                            
                            # RSI - Trend Following Logic
                            # If RSI is strong (50-75), it supports the trend
                            if rsi and 50 < rsi < 75:
                                base_confidence += 0.15
                            # If RSI is oversold in a dip (30-50), it's a dip buy
                            elif rsi and 30 < rsi <= 50:
                                base_confidence += 0.10
                            
                            confidence = max(0.0, min(1.0, base_confidence))
                        else:
                             self._log_decision('XAU_USD', "SKIP", DecisionReason.INDICATORS_MISSING, {"reason": "ATR missing"})
                    else:
                         self._log_decision('XAU_USD', "SKIP", DecisionReason.MISSING_DATA, {"reason": "Not enough candles"})
                except Exception as e:
                    self._log_decision('XAU_USD', "SKIP", DecisionReason.MISSING_DATA, {"error": f"Indicators error: {str(e)}"})
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
                    strategy_key=self.STRATEGY_ID,
                    strategy_id=getattr(self, 'strategy_id', self.STRATEGY_ID),
                    metadata={
                        'regime': regime.value,
                        'condition': condition.value,
                        'confidence': confidence,
                        'risk_adjustment': risk_adj.reason if risk_adj else "None"
                    }
                )
                signals.append(signal)
                self._log_decision('XAU_USD', "FIRE", DecisionReason.NO_SIGNAL, {"confidence": confidence, "required": required_conf})
                logger.info(f"📊 Gold Scalping: BUY XAU_USD @ {entry_price:.2f} | Conf: {confidence:.2f} | Regime: {regime.value}")
                
                # Stage 3: Update session state
                self.session_trade_count += 1
                self.last_session_trade_time = datetime.now(timezone.utc)
                # Note: last_trade_loss will be updated by external position monitoring
            else:
                self._log_decision('XAU_USD', "SKIP", DecisionReason.CONFIDENCE_LOW, {"confidence": confidence, "required": required_conf})
        
        except Exception as e:
            logger.warning(f"Error in Gold Scalping: {e}")
            self._log_decision('XAU_USD', "SKIP", DecisionReason.MISSING_DATA, {"error": str(e)})
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'enabled': self.enabled,
            'type': 'gold_scalping_adaptive',
            'status': 'active',
            'config': self.config
        }
