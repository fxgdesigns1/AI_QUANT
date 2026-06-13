#!/usr/bin/env python3
"""
Momentum Trading Strategy with Adaptive Components
Integrated with MarketRegimeDetector and AdaptiveSystem
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
import json

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


class DecisionReason(Enum):
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    OUTSIDE_SESSION = "OUTSIDE_SESSION"
    CONFIDENCE_LOW = "CONFIDENCE_LOW"
    SPREAD_TOO_HIGH = "SPREAD_TOO_HIGH"
    REGIME_MISMATCH = "REGIME_MISMATCH"
    MISSING_DATA = "MISSING_DATA"
    INDICATORS_MISSING = "INDICATORS_MISSING"
    RISK_TOO_HIGH = "RISK_TOO_HIGH"
    NO_SIGNAL = "NO_SIGNAL"
    EARNED_PYRAMIDING_BLOCKED = "EARNED_PYRAMIDING_BLOCKED"
    ENTRY_CONFIRMATION_FAILED = "ENTRY_CONFIRMATION_FAILED"

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
    strategy_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

from src.strategies.base_strategy import BaseStrategy

class MomentumTradingStrategy(BaseStrategy):
    """Momentum trading strategy with adaptive capabilities"""
    
    STRATEGY_ID = "momentum"
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the strategy"""
        super().__init__(config)
        self.name = "momentum_trading"
        
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
        
        # State for cooldowns
        self.last_entry_time: Dict[str, datetime] = {}
        
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

    def _log_decision(self, instrument: str, decision: str, reason: DecisionReason, metadata: Dict[str, Any] = None):
        """Log trading decision with structured format"""
        log_data = {
            "account_id": getattr(self, "account_id", "003"), # Default to 003 for momentum
            "strategy": self.STRATEGY_ID,
            "instrument": instrument,
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "reason": reason.value,
            "metadata": metadata or {}
        }
        # Use info for SKIPPED to ensure visibility as requested in Stage 1
        logger.info(f"DECISION_{decision}: {json.dumps(log_data)}")
    
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
        
        current_time = datetime.utcnow()

        for instrument, price_data in market_data.items():
            try:
                # 0. Cooldown Check (Stage 2)
                last_time = self.last_entry_time.get(instrument)
                if last_time:
                    elapsed = (current_time - last_time).total_seconds()
                    if elapsed < 45 * 60: # 45 minutes
                        self._log_decision(instrument, "SKIP", DecisionReason.COOLDOWN_ACTIVE, {"elapsed_min": elapsed/60})
                        continue

                # 1. Basic Data Extraction
                if not hasattr(price_data, 'bid') or not hasattr(price_data, 'ask'):
                    self._log_decision(instrument, "SKIP", DecisionReason.MISSING_DATA, {"error": "Missing bid/ask"})
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
                    self._log_decision(instrument, "SKIP", DecisionReason.SPREAD_TOO_HIGH, {"spread": spread_pips, "max": max_spread})
                    continue
                
                # 3. Adaptive Analysis (Regime & Condition)
                regime = MarketRegime.UNKNOWN
                condition = MarketCondition.NORMAL
                risk_adj = None
                
                if HAS_DEPENDENCIES and self.regime_detector:
                    try:
                        # Get historical data for regime detection
                        # Increased count for volatility gate (ATR history)
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
                            
                            logger.debug(f"Analysis {instrument}: {regime.value} ({regime_analysis.description}), {condition.value}. Adj: {risk_adj.reason}")
                        else:
                            self._log_decision(instrument, "SKIP", DecisionReason.MISSING_DATA, {"reason": "Insufficient candles"})
                            continue
                            
                    except Exception as e:
                        logger.warning(f"Adaptive analysis failed for {instrument}: {e}")
                        self._log_decision(instrument, "SKIP", DecisionReason.MISSING_DATA, {"error": str(e)})
                        continue
                else:
                    # Allow running without dependencies if needed, but log it
                    # logger.warning("Adaptive dependencies missing, skipping analysis")
                    pass

                # 4. Technical Indicators & Momentum (Existing Logic)
                if 'candles' not in locals() or not candles:
                     # Fallback if not fetched in adaptive block
                     candles = get_candles(instrument, granularity="M5", count=100)
                
                if not candles or len(candles) < 35: # Need enough for ATR median
                     self._log_decision(instrument, "SKIP", DecisionReason.MISSING_DATA, {"reason": "Not enough candles for indicators"})
                     continue

                closes = [c.c for c in candles]
                highs = [c.h for c in candles]
                lows = [c.l for c in candles]

                # Volatility Gate (Stage 2)
                # ATR(14) > rolling ATR median (last 20 periods)
                try:
                    # Calculate TRs
                    trs = []
                    for i in range(1, len(candles)):
                        h = highs[i]
                        l = lows[i]
                        pc = closes[i-1]
                        tr = max(h-l, abs(h-pc), abs(l-pc))
                        trs.append(tr)
                    
                    # Calculate ATRs (SMA of TR)
                    period = 14
                    atrs = []
                    # We need at least 20 ATR values, so we need 20 + 14 TRs = 34 candles.
                    if len(trs) >= period + 20:
                        for i in range(len(trs) - period - 20, len(trs) - period + 1): # Last 20 ATRs
                             # Slice TRs from i to i+period
                             window_tr = trs[i : i+period]
                             if len(window_tr) == period:
                                 atrs.append(sum(window_tr) / period)
                        
                        if atrs:
                            current_atr = atrs[-1]
                            rolling_median_atr = statistics.median(atrs[:-1]) if len(atrs) > 1 else current_atr
                            
                            # Gate
                            if current_atr <= rolling_median_atr:
                                self._log_decision(instrument, "SKIP", DecisionReason.LOW_VOLATILITY, {"atr": current_atr, "median": rolling_median_atr})
                                continue
                except Exception as e:
                    logger.warning(f"Volatility gate error: {e}")
                    self._log_decision(instrument, "SKIP", DecisionReason.MISSING_DATA, {"error": "Volatility calculation failed"})
                    continue

                rsi = calculate_rsi(closes, period=14)
                macd_result = calculate_macd(closes, fast=12, slow=26, signal=9)
                ema_fast = calculate_ema(closes, period=12)
                ema_slow = calculate_ema(closes, period=26)
                
                if rsi is None or macd_result is None:
                    self._log_decision(instrument, "SKIP", DecisionReason.INDICATORS_MISSING, {"rsi": rsi is None, "macd": macd_result is None})
                    continue
                    
                macd_line, signal_line, histogram = macd_result
                
                # 5. Calculate Base Confidence
                base_confidence = 0.5
                
                # RSI Logic - MOMENTUM (Trend Following)
                # Buy strong moves (RSI 50-70), avoid extreme overbought (>80)
                if rsi > 50 and rsi < 80: 
                    base_confidence += 0.15
                elif rsi < 30: 
                    # Oversold bounce
                    base_confidence += 0.10
                
                # MACD Logic
                if macd_line > signal_line: 
                    base_confidence += 0.15
                    if histogram > 0:
                        base_confidence += 0.05
                
                # EMA Trend Logic
                if ema_fast and ema_slow and ema_fast > ema_slow:
                    base_confidence += 0.15
                
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
                
                # 7. Entry Confirmation (Stage 2)
                # Require candle close beyond breakout level
                # For momentum, we use EMA crossover as breakout level
                if ema_fast and ema_slow:
                    breakout_level = ema_fast  # Fast EMA is the breakout level
                    last_close = closes[-1]
                    
                    # For BUY signals, require close above breakout level
                    if last_close <= breakout_level:
                        self._log_decision(instrument, "SKIP", DecisionReason.ENTRY_CONFIRMATION_FAILED, {
                            "last_close": last_close,
                            "breakout_level": breakout_level,
                            "required": "close > breakout for BUY"
                        })
                        continue
                
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
                    
                    # Note: Earned pyramiding check (Stage 2) requires position state
                    # This should be checked at execution time by the order manager
                    # If existing position unrealized PnL <= 0, block additional entries
                    
                    signal = TradeSignal(
                        instrument=instrument,
                        side=TradeSide.BUY,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        strategy_key=self.STRATEGY_ID,
                        strategy_id=getattr(self, 'strategy_id', self.STRATEGY_ID),
                        metadata={
                            'regime': regime.value,
                            'condition': condition.value,
                            'confidence': final_confidence,
                            'risk_adjustment': risk_adj.reason if risk_adj else "None"
                        }
                    )
                    signals.append(signal)
                    self._log_decision(instrument, "FIRE", DecisionReason.NO_SIGNAL, {"confidence": final_confidence, "required": required_confidence}) 
                    logger.info(f"📊 SIGNAL GENERATED: {instrument} {TradeSide.BUY.value} @ {entry_price:.5f} | Conf: {final_confidence:.2f} | Regime: {regime.value}")
                    
                    # Update state
                    self.last_entry_time[instrument] = current_time

                else:
                    self._log_decision(instrument, "SKIP", DecisionReason.CONFIDENCE_LOW, {"confidence": final_confidence, "required": required_confidence})
                
            except Exception as e:
                logger.error(f"Error analyzing {instrument}: {e}")
                self._log_decision(instrument, "SKIP", DecisionReason.MISSING_DATA, {"error": str(e)})
                continue
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        return {
            'name': self.name,
            'id': self.STRATEGY_ID,
            'enabled': self.enabled,
            'type': 'momentum_adaptive',
            'status': 'active',
            'config': self.config
        }
