#!/usr/bin/env python3
"""
Range Trading Strategy - For Flat/Choppy Markets
Trades reversals at support/resistance when no momentum exists
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

from ..core.order_manager import TradeSignal, OrderSide
from ..core.data_feed import MarketData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RangeTradingStrategy:
    """
    Range Trading Strategy - Profitable in flat markets
    Trades reversals at support/resistance levels
    """
    
    def __init__(self):
        """Initialize range trading strategy"""
        self.name = "Range Trading - Flat Markets"
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        
        # Range detection parameters
        self.lookback_period = 50          # Look back 50 bars for levels
        self.level_tolerance = 0.0015      # 0.15% proximity to level
        self.min_touches = 2               # Min 2 touches to confirm level
        
        # Entry requirements
        self.max_adx = 25                  # ADX < 25 (weak trend = ranging)
        self.min_volume = 0.20             # Moderate volume
        self.require_reversal_confirmation = True
        
        # Risk management
        self.stop_loss_pct = 0.006         # 0.6% SL
        self.take_profit_pct = 0.012       # 1.2% TP (1:2 R:R)
        self.max_trades_per_day = 10
        self.target_trades_per_day = 5     # Soft target
        
        # Data storage
        self.price_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.support_levels: Dict[str, List[float]] = {}
        self.resistance_levels: Dict[str, List[float]] = {}
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Target: {self.target_trades_per_day} trades/day")
    
    def _reset_daily_counters(self):
        """Reset daily counters"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trade_count = 0
            self.last_reset_date = current_date
    
    def _find_support_resistance(self, prices: List[float]) -> tuple:
        """
        Find support and resistance levels
        Returns: (support_levels, resistance_levels)
        """
        if len(prices) < self.lookback_period:
            return [], []
        
        recent_prices = prices[-self.lookback_period:]
        
        highs = []
        lows = []
        
        # Find local highs and lows (pivot points)
        for i in range(5, len(recent_prices) - 5):
            # Local high
            if recent_prices[i] == max(recent_prices[i-5:i+6]):
                highs.append(recent_prices[i])
            # Local low
            if recent_prices[i] == min(recent_prices[i-5:i+6]):
                lows.append(recent_prices[i])
        
        # Cluster nearby levels
        resistance = self._cluster_levels(highs)
        support = self._cluster_levels(lows)
        
        return support, resistance
    
    def _cluster_levels(self, levels: List[float]) -> List[float]:
        """Cluster nearby price levels"""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            cluster_mean = np.mean(current_cluster)
            if abs(level - cluster_mean) / cluster_mean < 0.003:  # Within 0.3%
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        
        if current_cluster:
            clusters.append(np.mean(current_cluster))
        
        return clusters[:3]  # Top 3 levels
    
    def _is_near_level(self, price: float, levels: List[float]) -> tuple:
        """
        Check if price is near a key level
        Returns: (is_near, level, distance)
        """
        for level in levels:
            distance_pct = abs(price - level) / level
            if distance_pct < self.level_tolerance:
                return True, level, distance_pct
        
        return False, None, None
    
    def _check_reversal_confirmation(self, prices: List[float], 
                                    direction: str) -> bool:
        """
        Check for reversal confirmation
        """
        if len(prices) < 3:
            return False
        
        recent = prices[-3:]
        
        if direction == 'BULLISH':
            # Looking for bounce from support
            # Recent bars should show: down, down, UP
            return recent[-1] > recent[-2]
        
        elif direction == 'BEARISH':
            # Looking for rejection from resistance
            # Recent bars should show: up, up, DOWN
            return recent[-1] < recent[-2]
        
        return False
    
    def analyze_market(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market for range trading opportunities"""
        self._reset_daily_counters()
        
        if self.daily_trade_count >= self.max_trades_per_day:
            return []
        
        # Update price history
        for instrument, data in market_data.items():
            if instrument in self.instruments:
                mid_price = (data.bid + data.ask) / 2
                if instrument not in self.price_history:
                    self.price_history[instrument] = []
                self.price_history[instrument].append(mid_price)
                
                if len(self.price_history[instrument]) > 100:
                    self.price_history[instrument] = self.price_history[instrument][-100:]
        
        signals = []
        
        for instrument in self.instruments:
            if instrument not in market_data or len(self.price_history.get(instrument, [])) < 50:
                continue
            
            prices = self.price_history[instrument]
            current_price = prices[-1]
            current_data = market_data[instrument]
            
            # Find support/resistance
            support, resistance = self._find_support_resistance(prices)
            
            if not support or not resistance:
                continue
            
            # Check if near support (potential BUY)
            near_support, support_level, support_dist = self._is_near_level(current_price, support)
            
            if near_support:
                # Check reversal confirmation
                if self.require_reversal_confirmation:
                    if not self._check_reversal_confirmation(prices, 'BULLISH'):
                        continue
                
                # Generate BUY signal
                entry = current_data.ask
                sl = entry * (1 - self.stop_loss_pct)
                tp = entry * (1 + self.take_profit_pct)
                
                signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.BUY,
                    units=50000,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    confidence=0.70,
                    strength=0.75,
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                
                signals.append(signal)
                logger.info(f"✅ RANGE BUY: {instrument} @ {support_level:.5f} (support bounce)")
                self.daily_trade_count += 1
            
            # Check if near resistance (potential SELL)
            near_resistance, resistance_level, resistance_dist = self._is_near_level(current_price, resistance)
            
            if near_resistance and self.daily_trade_count < self.max_trades_per_day:
                # Check reversal confirmation
                if self.require_reversal_confirmation:
                    if not self._check_reversal_confirmation(prices, 'BEARISH'):
                        continue
                
                # Generate SELL signal
                entry = current_data.bid
                sl = entry * (1 + self.stop_loss_pct)
                tp = entry * (1 - self.take_profit_pct)
                
                signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.SELL,
                    units=50000,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    confidence=0.70,
                    strength=0.75,
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                
                signals.append(signal)
                logger.info(f"✅ RANGE SELL: {instrument} @ {resistance_level:.5f} (resistance rejection)")
                self.daily_trade_count += 1
        
        return signals


# Global instance
_range_trading = None

def get_range_trading_strategy():
    """Get the global range trading strategy instance"""
    global _range_trading
    if _range_trading is None:
        _range_trading = RangeTradingStrategy()
    return _range_trading















