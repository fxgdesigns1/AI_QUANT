#!/usr/bin/env python3
"""
Professional Position Sizing Calculator
Calculates proper lot sizes based on account balance, risk percentage, and ATR
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PositionSize:
    """Position sizing result"""
    units: int
    risk_amount: float
    risk_percentage: float
    stop_distance_pips: float
    value_per_pip: float
    max_loss: float

class PositionSizer:
    """Professional position sizing calculator"""
    
    # Pip values for different instrument types
    PIP_VALUES = {
        'JPY_PAIRS': 0.01,      # For XXX_JPY pairs
        'STANDARD': 0.0001,      # For most forex pairs
        'XAU': 0.01,            # For gold
        'XAG': 0.001,           # For silver
        'INDICES': 1.0          # For indices
    }
    
    # Standard units per lot
    STANDARD_LOT = 100000
    MINI_LOT = 10000
    MICRO_LOT = 1000
    
    def __init__(self):
        """Initialize position sizer"""
        self.min_units = 1000  # Minimum position size
        self.max_units = 1000000  # Maximum position size (10 lots)
        
    def get_pip_value(self, instrument: str) -> float:
        """Get pip value for instrument"""
        if '_JPY' in instrument or 'JPY_' in instrument:
            return self.PIP_VALUES['JPY_PAIRS']
        elif 'XAU' in instrument:
            return self.PIP_VALUES['XAU']
        elif 'XAG' in instrument:
            return self.PIP_VALUES['XAG']
        else:
            return self.PIP_VALUES['STANDARD']
    
    def calculate_stop_distance_pips(self, entry_price: float, stop_loss: float, instrument: str) -> float:
        """Calculate stop distance in pips"""
        pip_value = self.get_pip_value(instrument)
        distance = abs(entry_price - stop_loss) / pip_value
        return distance
    
    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        entry_price: float,
        stop_loss: float,
        instrument: str,
        max_leverage: float = 50.0,
        signal_strength: float = 0.5
    ) -> PositionSize:
        """
        Calculate optimal position size based on risk management
        
        Args:
            account_balance: Current account balance
            risk_percent: Base risk percentage (will be scaled by signal_strength)
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            instrument: Trading instrument
            max_leverage: Maximum leverage allowed
            signal_strength: Signal confidence 0.0-1.0 (scales risk from 0.3% to max)
            
        Returns:
            PositionSize object with calculated values
        """
        try:
            # SMART DYNAMIC RISK SCALING BASED ON SIGNAL STRENGTH
            # 80%+ confidence = FULL 1% risk
            # Below 80% = Sliding scale from 0.3% to 1%
            
            min_risk = 0.3  # Floor: 0.3% for weakest signals
            max_risk = risk_percent  # Ceiling: max risk (1%)
            confidence_threshold = 0.8  # 80% threshold for full risk
            
            if signal_strength >= confidence_threshold:
                # 80%+ confidence: Use FULL max risk (1%)
                scaled_risk = max_risk
            else:
                # Below 80%: Sliding scale from 0.3% to 1%
                # Formula: risk = 0.3 + (signal/0.8) × 0.7
                scale_factor = signal_strength / confidence_threshold
                scaled_risk = min_risk + (scale_factor * (max_risk - min_risk))
            
            # Ensure within bounds
            scaled_risk = max(min_risk, min(scaled_risk, max_risk))
            
            logger.info(f"📊 Signal Strength: {signal_strength*100:.0f}% → Risk: {scaled_risk:.2f}%")
            
            # Calculate risk amount in account currency using scaled risk
            risk_amount = account_balance * (scaled_risk / 100.0)
            
            # Calculate stop distance
            stop_distance = abs(entry_price - stop_loss)
            
            if stop_distance == 0:
                logger.error(f"❌ Stop distance is zero for {instrument}")
                return self._minimum_position(risk_amount, risk_percent)
            
            # Calculate pip value
            pip_value = self.get_pip_value(instrument)
            stop_distance_pips = stop_distance / pip_value
            
            # Calculate position size
            # Formula: Position Size = (Risk Amount) / (Stop Distance in price)
            position_size_raw = risk_amount / stop_distance
            
            # Convert to units
            units = int(position_size_raw)
            
            # Apply leverage limits
            max_units_by_leverage = int((account_balance * max_leverage) / entry_price)
            if units > max_units_by_leverage:
                logger.warning(f"⚠️ Position size limited by leverage: {units} -> {max_units_by_leverage}")
                units = max_units_by_leverage
            
            # Apply min/max limits
            units = max(self.min_units, min(units, self.max_units))
            
            # Calculate actual risk with final position size
            actual_max_loss = units * stop_distance
            actual_risk_pct = (actual_max_loss / account_balance) * 100
            value_per_pip = units * pip_value
            
            result = PositionSize(
                units=units,
                risk_amount=risk_amount,
                risk_percentage=actual_risk_pct,
                stop_distance_pips=stop_distance_pips,
                value_per_pip=value_per_pip,
                max_loss=actual_max_loss
            )
            
            logger.info(f"📊 Position sizing for {instrument}:")
            logger.info(f"   Balance: ${account_balance:,.2f}")
            logger.info(f"   Risk: {risk_percent}% = ${risk_amount:,.2f}")
            logger.info(f"   Entry: {entry_price}")
            logger.info(f"   Stop: {stop_loss}")
            logger.info(f"   Distance: {stop_distance_pips:.1f} pips")
            logger.info(f"   Position: {units:,} units (${units * entry_price:,.2f})")
            logger.info(f"   Max Loss: ${actual_max_loss:,.2f} ({actual_risk_pct:.2f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return self._minimum_position(account_balance * (risk_percent / 100.0), risk_percent)
    
    def _minimum_position(self, risk_amount: float, risk_percent: float) -> PositionSize:
        """Return minimum position size"""
        return PositionSize(
            units=self.min_units,
            risk_amount=risk_amount,
            risk_percentage=risk_percent,
            stop_distance_pips=10.0,
            value_per_pip=0.1,
            max_loss=risk_amount
        )
    
    def calculate_lot_size(self, units: int) -> Dict[str, float]:
        """Convert units to lot sizes"""
        standard_lots = units / self.STANDARD_LOT
        mini_lots = units / self.MINI_LOT
        micro_lots = units / self.MICRO_LOT
        
        return {
            'units': units,
            'standard_lots': round(standard_lots, 2),
            'mini_lots': round(mini_lots, 1),
            'micro_lots': round(micro_lots, 0)
        }
    
    def validate_position_size(
        self,
        units: int,
        account_balance: float,
        entry_price: float,
        max_risk_percent: float = 3.0
    ) -> bool:
        """Validate if position size is within acceptable limits"""
        position_value = units * entry_price
        position_percent = (position_value / account_balance) * 100
        
        # Check if position size is too large
        if position_percent > (max_risk_percent * 10):  # Max 30% of account for 3% risk
            logger.warning(f"⚠️ Position size too large: {position_percent:.1f}% of account")
            return False
        
        # Check minimum
        if units < self.min_units:
            logger.warning(f"⚠️ Position size too small: {units} < {self.min_units}")
            return False
        
        return True

# Global instance
_position_sizer = None

def get_position_sizer() -> PositionSizer:
    """Get global position sizer instance"""
    global _position_sizer
    if _position_sizer is None:
        _position_sizer = PositionSizer()
    return _position_sizer





