#!/usr/bin/env python3
"""
Profit Protection System
Manages trailing stops and break-even moves to protect gains
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProfitProtector:
    """
    Manages profit protection with intelligent trailing stops
    
    Protection stages:
    1. Initial: Original stop loss (-0.8%)
    2. +0.5% profit: Move to break-even
    3. +1.5% profit: Activate trailing stop (0.8% behind peak)
    4. Continue trailing as price moves in favor
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize profit protector
        
        Args:
            config: Optional config dict with:
                - breakeven_at: Profit % to move to BE (default 0.005 = 0.5%)
                - trail_at: Profit % to activate trailing (default 0.015 = 1.5%)
                - trail_distance: Distance behind peak (default 0.008 = 0.8%)
        """
        config = config or {}
        
        # Protection thresholds
        self.breakeven_threshold = config.get('breakeven_at', 0.005)   # +0.5%
        self.trail_activation = config.get('trail_at', 0.015)           # +1.5%
        self.trail_distance = config.get('trail_distance', 0.008)       # 0.8%
        
        # Don't close partials - let winners run
        self.partial_close_enabled = False
        
        logger.info(f"✅ Profit Protector initialized:")
        logger.info(f"   Break-even at: +{self.breakeven_threshold*100:.1f}%")
        logger.info(f"   Trail activation: +{self.trail_activation*100:.1f}%")
        logger.info(f"   Trail distance: {self.trail_distance*100:.1f}%")
    
    def calculate_profit_pct(self, position: Dict, current_price: float) -> float:
        """
        Calculate current profit percentage
        
        Args:
            position: Position dict with 'entry_price' and 'side'
            current_price: Current market price
        
        Returns:
            Profit % (positive = profit, negative = loss)
        """
        entry = position['entry_price']
        side = position['side']
        
        if side == 'BUY' or side.upper() == 'BUY':
            profit_pct = (current_price - entry) / entry
        else:  # SELL
            profit_pct = (entry - current_price) / entry
        
        return profit_pct
    
    def update_peak_price(self, position: Dict, current_price: float) -> float:
        """
        Track peak price for trailing stops
        
        Args:
            position: Position dict (will be modified)
            current_price: Current market price
        
        Returns:
            Updated peak price
        """
        side = position['side']
        
        if side == 'BUY' or side.upper() == 'BUY':
            # For longs, track highest price
            peak = position.get('peak_price', current_price)
            position['peak_price'] = max(peak, current_price)
        else:  # SELL
            # For shorts, track lowest price
            peak = position.get('peak_price', current_price)
            position['peak_price'] = min(peak, current_price)
        
        return position['peak_price']
    
    def calculate_breakeven_stop(self, position: Dict) -> float:
        """
        Calculate break-even stop loss
        
        Returns:
            Break-even price (same as entry)
        """
        return position['entry_price']
    
    def calculate_trailing_stop(self, position: Dict, peak_price: float) -> float:
        """
        Calculate trailing stop based on peak price
        
        Args:
            position: Position dict
            peak_price: Peak price reached
        
        Returns:
            Trailing stop level
        """
        side = position['side']
        
        if side == 'BUY' or side.upper() == 'BUY':
            # For longs, trail below peak
            trail_sl = peak_price * (1 - self.trail_distance)
        else:  # SELL
            # For shorts, trail above peak
            trail_sl = peak_price * (1 + self.trail_distance)
        
        return trail_sl
    
    def update_stops(self, position: Dict, current_price: float) -> Optional[float]:
        """
        Main function: Update stop loss for position based on profit
        
        Args:
            position: Position dict with:
                - entry_price
                - stop_loss (current)
                - side ('BUY' or 'SELL')
                - instrument
                - (peak_price - optional, will be added)
            current_price: Current market price
        
        Returns:
            New stop loss level, or None if no change
        """
        entry = position['entry_price']
        current_sl = position['stop_loss']
        side = position['side']
        instrument = position.get('instrument', 'UNKNOWN')
        
        # Calculate current profit
        profit_pct = self.calculate_profit_pct(position, current_price)
        
        # Update peak price tracking
        peak_price = self.update_peak_price(position, current_price)
        
        # Stage 1: Move to break-even at +0.5% profit
        if profit_pct >= self.breakeven_threshold:
            breakeven_sl = self.calculate_breakeven_stop(position)
            
            # Only move stop if it improves protection
            if side == 'BUY' or side.upper() == 'BUY':
                if breakeven_sl > current_sl:
                    logger.info(f"✅ {instrument}: Moving to break-even @ {breakeven_sl:.5f} "
                               f"(profit: +{profit_pct*100:.2f}%)")
                    return breakeven_sl
            else:  # SELL
                if breakeven_sl < current_sl:
                    logger.info(f"✅ {instrument}: Moving to break-even @ {breakeven_sl:.5f} "
                               f"(profit: +{profit_pct*100:.2f}%)")
                    return breakeven_sl
        
        # Stage 2: Activate trailing stop at +1.5% profit
        if profit_pct >= self.trail_activation:
            trail_sl = self.calculate_trailing_stop(position, peak_price)
            
            # Ensure trailing stop never goes below break-even
            breakeven = entry
            
            if side == 'BUY' or side.upper() == 'BUY':
                # For longs, take max of: current SL, trailing SL, break-even
                new_sl = max(current_sl, trail_sl, breakeven)
                
                if new_sl > current_sl:
                    logger.info(f"📈 {instrument}: Trailing stop → {new_sl:.5f} "
                               f"(peak: {peak_price:.5f}, profit: +{profit_pct*100:.2f}%)")
                    return new_sl
            
            else:  # SELL
                # For shorts, take min of: current SL, trailing SL, break-even
                new_sl = min(current_sl, trail_sl, breakeven)
                
                if new_sl < current_sl:
                    logger.info(f"📈 {instrument}: Trailing stop → {new_sl:.5f} "
                               f"(peak: {peak_price:.5f}, profit: +{profit_pct*100:.2f}%)")
                    return new_sl
        
        # No stop update needed
        return None
    
    def should_close_partial(self, position: Dict, current_price: float) -> Optional[float]:
        """
        Check if partial position should be closed
        
        Currently DISABLED (let winners run per user requirement 3b)
        
        Returns:
            Percentage to close (0.0 to 1.0), or None
        """
        if not self.partial_close_enabled:
            return None
        
        # If we ever enable this, it would be here
        # Example: Close 50% at +2% profit
        # profit_pct = self.calculate_profit_pct(position, current_price)
        # if profit_pct >= 0.02:
        #     return 0.5  # Close 50%
        
        return None
    
    def get_protection_stage(self, position: Dict, current_price: float) -> str:
        """
        Get current protection stage for logging/monitoring
        
        Returns:
            'INITIAL', 'BREAKEVEN', or 'TRAILING'
        """
        profit_pct = self.calculate_profit_pct(position, current_price)
        
        if profit_pct >= self.trail_activation:
            return 'TRAILING'
        elif profit_pct >= self.breakeven_threshold:
            return 'BREAKEVEN'
        else:
            return 'INITIAL'
    
    def get_status_summary(self, position: Dict, current_price: float) -> Dict:
        """
        Get detailed status for monitoring
        
        Returns:
            Status dict with profit, stage, peak, etc.
        """
        profit_pct = self.calculate_profit_pct(position, current_price)
        stage = self.get_protection_stage(position, current_price)
        peak = position.get('peak_price', current_price)
        
        return {
            'instrument': position.get('instrument', 'UNKNOWN'),
            'profit_pct': profit_pct,
            'profit_display': f"{profit_pct*100:+.2f}%",
            'stage': stage,
            'peak_price': peak,
            'current_sl': position['stop_loss'],
            'breakeven': position['entry_price'],
            'next_milestone': self._get_next_milestone(profit_pct)
        }
    
    def _get_next_milestone(self, current_profit_pct: float) -> str:
        """Get description of next protection milestone"""
        if current_profit_pct < self.breakeven_threshold:
            needed = (self.breakeven_threshold - current_profit_pct) * 100
            return f"+{needed:.1f}% to break-even"
        elif current_profit_pct < self.trail_activation:
            needed = (self.trail_activation - current_profit_pct) * 100
            return f"+{needed:.1f}% to trailing"
        else:
            return "Trailing active"


# Global instance
_profit_protector = None

def get_profit_protector(config: Optional[Dict] = None) -> ProfitProtector:
    """Get the global profit protector instance"""
    global _profit_protector
    if _profit_protector is None:
        _profit_protector = ProfitProtector(config)
    return _profit_protector




















