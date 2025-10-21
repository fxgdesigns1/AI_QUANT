#!/usr/bin/env python3
"""
Advanced Risk Management System
Implements position limits, correlation checks, spread filters, and time filters
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

@dataclass
class RiskLimits:
    """Risk management limits"""
    max_concurrent_positions: int = 15
    max_margin_usage_pct: float = 40.0
    min_signal_strength: float = 0.7
    max_spread_pips: float = 3.0
    max_correlated_pairs: int = 2
    min_margin_available_pct: float = 30.0

class RiskManager:
    """Advanced risk management for trading system"""
    
    # Correlated pairs mapping
    CORRELATION_GROUPS = {
        'EUR_PAIRS': ['EUR_USD', 'EUR_JPY', 'EUR_GBP', 'EUR_AUD', 'EUR_CAD'],
        'GBP_PAIRS': ['GBP_USD', 'GBP_JPY', 'EUR_GBP', 'GBP_AUD', 'GBP_CAD'],
        'JPY_PAIRS': ['USD_JPY', 'EUR_JPY', 'GBP_JPY', 'AUD_JPY', 'CAD_JPY'],
        'USD_PAIRS': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD'],
        'COMMODITY': ['XAU_USD', 'XAG_USD', 'USD_CAD', 'AUD_USD', 'NZD_USD']
    }
    
    # Trading sessions (UTC)
    LONDON_SESSION = (time(7, 0), time(16, 0))   # 07:00-16:00 UTC
    NY_SESSION = (time(13, 0), time(21, 0))      # 13:00-21:00 UTC
    TOKYO_SESSION = (time(23, 0), time(8, 0))    # 23:00-08:00 UTC (crosses midnight)
    
    def __init__(self, limits: Optional[RiskLimits] = None):
        """Initialize risk manager with limits"""
        self.limits = limits or RiskLimits()
        logger.info(f"✅ Risk Manager initialized:")
        logger.info(f"   Max positions: {self.limits.max_concurrent_positions}")
        logger.info(f"   Max margin: {self.limits.max_margin_usage_pct}%")
        logger.info(f"   Min signal: {self.limits.min_signal_strength}")
        logger.info(f"   Max spread: {self.limits.max_spread_pips} pips")
    
    def can_open_position(
        self,
        instrument: str,
        current_positions: int,
        open_instruments: List[str],
        signal_strength: float,
        spread_pips: float,
        margin_used_pct: float,
        account_balance: float
    ) -> tuple[bool, str]:
        """
        Check if we can open a new position
        
        Returns:
            (can_open: bool, reason: str)
        """
        
        # Check 1: Maximum concurrent positions
        if current_positions >= self.limits.max_concurrent_positions:
            return False, f"Max positions reached ({current_positions}/{self.limits.max_concurrent_positions})"
        
        # Check 2: Signal strength
        if signal_strength < self.limits.min_signal_strength:
            return False, f"Signal too weak ({signal_strength:.2f} < {self.limits.min_signal_strength})"
        
        # Check 3: Spread filter
        if spread_pips > self.limits.max_spread_pips:
            return False, f"Spread too wide ({spread_pips:.1f} > {self.limits.max_spread_pips} pips)"
        
        # Check 4: Margin usage
        if margin_used_pct >= self.limits.max_margin_usage_pct:
            return False, f"Margin limit reached ({margin_used_pct:.1f}% >= {self.limits.max_margin_usage_pct}%)"
        
        # Check 5: Trading hours
        if not self.is_trading_hours():
            return False, "Outside trading hours (London/NY sessions only)"
        
        # Check 6: Correlation check
        correlated_count = self._count_correlated_pairs(instrument, open_instruments)
        if correlated_count >= self.limits.max_correlated_pairs:
            return False, f"Too many correlated pairs ({correlated_count}/{self.limits.max_correlated_pairs})"
        
        # Check 7: Margin available
        margin_available_pct = 100 - margin_used_pct
        if margin_available_pct < self.limits.min_margin_available_pct:
            return False, f"Insufficient margin available ({margin_available_pct:.1f}% < {self.limits.min_margin_available_pct}%)"
        
        return True, "All checks passed"
    
    def _count_correlated_pairs(self, instrument: str, open_instruments: List[str]) -> int:
        """Count how many correlated pairs are already open"""
        correlated_count = 0
        
        # Find which correlation groups this instrument belongs to
        instrument_groups = []
        for group_name, pairs in self.CORRELATION_GROUPS.items():
            if instrument in pairs:
                instrument_groups.append(group_name)
        
        # Count open positions in same groups
        for open_inst in open_instruments:
            for group_name in instrument_groups:
                if open_inst in self.CORRELATION_GROUPS.get(group_name, []):
                    correlated_count += 1
                    break  # Count each instrument once
        
        return correlated_count
    
    def is_trading_hours(self, current_time: Optional[datetime] = None) -> bool:
        """Check if current time is within trading hours (London or NY sessions)"""
        if current_time is None:
            current_time = datetime.utcnow()
        
        current_hour_minute = current_time.time()
        
        # Check London session (07:00-16:00 UTC)
        if self.LONDON_SESSION[0] <= current_hour_minute <= self.LONDON_SESSION[1]:
            return True
        
        # Check NY session (13:00-21:00 UTC)
        if self.NY_SESSION[0] <= current_hour_minute <= self.NY_SESSION[1]:
            return True
        
        return False
    
    def get_session_name(self, current_time: Optional[datetime] = None) -> str:
        """Get current trading session name"""
        if current_time is None:
            current_time = datetime.utcnow()
        
        current_hour_minute = current_time.time()
        
        # Check sessions
        if self.LONDON_SESSION[0] <= current_hour_minute <= self.LONDON_SESSION[1]:
            if self.NY_SESSION[0] <= current_hour_minute <= self.NY_SESSION[1]:
                return "LONDON+NY (Peak Liquidity)"
            return "LONDON"
        
        if self.NY_SESSION[0] <= current_hour_minute <= self.NY_SESSION[1]:
            return "NEW YORK"
        
        # Tokyo session crosses midnight, handle specially
        if current_hour_minute >= self.TOKYO_SESSION[0] or current_hour_minute <= self.TOKYO_SESSION[1]:
            return "TOKYO (Low Liquidity)"
        
        return "OFF HOURS"
    
    def calculate_spread_pips(self, bid: float, ask: float, instrument: str) -> float:
        """Calculate spread in pips for any instrument"""
        spread = ask - bid
        
        # JPY pairs have different pip value
        if '_JPY' in instrument or 'JPY_' in instrument:
            return spread * 100  # 0.01 = 1 pip for JPY
        elif 'XAU' in instrument or 'XAG' in instrument:
            return spread * 10  # Gold/Silver pip calculation
        else:
            return spread * 10000  # 0.0001 = 1 pip for standard pairs
    
    def should_move_to_breakeven(
        self,
        entry_price: float,
        current_price: float,
        take_profit: float,
        side: str
    ) -> bool:
        """Check if stop should be moved to break-even"""
        
        if side.upper() == 'BUY':
            profit_target = take_profit - entry_price
            current_profit = current_price - entry_price
        else:  # SELL
            profit_target = entry_price - take_profit
            current_profit = entry_price - current_price
        
        # Move to breakeven when 50% to target
        if profit_target > 0:
            progress = current_profit / profit_target
            return progress >= 0.5
        
        return False
    
    def get_risk_status(
        self,
        current_positions: int,
        margin_used_pct: float,
        daily_trades: int,
        unrealized_pl: float,
        account_balance: float
    ) -> Dict:
        """Get comprehensive risk status"""
        
        # Calculate risk level
        risk_level = "LOW"
        risk_score = 0
        
        # Position count risk
        position_pct = (current_positions / self.limits.max_concurrent_positions) * 100
        if position_pct > 80:
            risk_score += 3
        elif position_pct > 60:
            risk_score += 2
        elif position_pct > 40:
            risk_score += 1
        
        # Margin risk
        if margin_used_pct > 35:
            risk_score += 3
        elif margin_used_pct > 25:
            risk_score += 2
        elif margin_used_pct > 15:
            risk_score += 1
        
        # P&L risk
        pl_pct = (unrealized_pl / account_balance) * 100
        if pl_pct < -3:
            risk_score += 3
        elif pl_pct < -2:
            risk_score += 2
        elif pl_pct < -1:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 6:
            risk_level = "HIGH"
        elif risk_score >= 3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'positions': current_positions,
            'positions_limit': self.limits.max_concurrent_positions,
            'positions_pct': position_pct,
            'margin_used_pct': margin_used_pct,
            'margin_limit_pct': self.limits.max_margin_usage_pct,
            'daily_trades': daily_trades,
            'unrealized_pl': unrealized_pl,
            'pl_pct': pl_pct,
            'can_trade': risk_level != "HIGH" and position_pct < 90
        }
    
    def get_correlated_pairs(self, instrument: str) -> Set[str]:
        """Get all pairs correlated with given instrument"""
        correlated = set()
        
        for group_name, pairs in self.CORRELATION_GROUPS.items():
            if instrument in pairs:
                correlated.update(pairs)
        
        # Remove the instrument itself
        correlated.discard(instrument)
        
        return correlated

# Global instance
_risk_manager = None

def get_risk_manager() -> RiskManager:
    """Get global risk manager instance"""
    global _risk_manager
    if _risk_manager is None:
        # Load custom limits from environment if available
        limits = RiskLimits(
            max_concurrent_positions=int(os.getenv('MAX_POSITIONS', '15')),
            max_margin_usage_pct=float(os.getenv('MAX_MARGIN_PCT', '40.0')),
            min_signal_strength=float(os.getenv('MIN_SIGNAL_STRENGTH', '0.7')),
            max_spread_pips=float(os.getenv('MAX_SPREAD_PIPS', '3.0')),
            max_correlated_pairs=int(os.getenv('MAX_CORRELATED', '2'))
        )
        _risk_manager = RiskManager(limits)
    return _risk_manager





