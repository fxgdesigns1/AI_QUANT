#!/usr/bin/env python3
"""
Account 001 Trade Validator
Enforces strict rules to prevent counter-trend trades and emotional trading
Created: October 8, 2025 after SHORT trade mistake
"""

import logging
from typing import Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Account001Validator:
    """
    Validates ALL trades on Account 001 before execution
    Prevents counter-trend, emotional, and compensation trades
    """
    
    def __init__(self):
        """Initialize validator with strict rules"""
        self.account_id = "101-004-30719775-001"
        self.allowed_instrument = "XAU_USD"
        self.allowed_direction = "LONG"
        self.max_position_size = 400
        self.max_concurrent_positions = 3
        self.max_total_units = 900
        
        # Entry zones (LONG only)
        self.entry_zones = [
            (3925, 3930),  # Strong support
            (3945, 3950),  # Primary support
            (3960, 3965),  # Breakout zone
            (3980, 3995),  # Minor dips
            (4000, 4010),  # Small pullbacks (extended)
        ]
        
        # Risk management
        self.min_stop_loss = 15  # $15 minimum
        self.max_stop_loss = 25  # $25 maximum
        self.min_take_profit = 25  # $25 minimum
        self.min_risk_reward = 1.5  # 1:1.5 minimum
        
        logger.info("✅ Account 001 Validator initialized with strict rules")
    
    def validate_trade(
        self,
        instrument: str,
        direction: str,
        units: int,
        entry_price: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        current_positions: int,
        total_units_open: int
    ) -> Tuple[bool, str]:
        """
        Validate trade against Account 001 rules
        
        Returns:
            (is_valid, reason)
        """
        
        # Rule 1: Instrument check
        if instrument != self.allowed_instrument:
            return False, f"❌ BLOCKED: Only {self.allowed_instrument} allowed on Account 001. Got: {instrument}"
        
        # Rule 2: Direction check (CRITICAL - prevents counter-trend)
        if direction != self.allowed_direction:
            return False, f"❌ BLOCKED: Only {self.allowed_direction} trades allowed. Got: {direction}. Gold Trump Strategy is BULLISH!"
        
        # Rule 3: Position size check
        if abs(units) > self.max_position_size:
            return False, f"❌ BLOCKED: Position size {abs(units)} exceeds maximum {self.max_position_size} units"
        
        # Rule 4: Concurrent positions check
        if current_positions >= self.max_concurrent_positions:
            return False, f"❌ BLOCKED: Already have {current_positions} positions. Maximum {self.max_concurrent_positions} allowed"
        
        # Rule 5: Total exposure check
        if total_units_open + abs(units) > self.max_total_units:
            return False, f"❌ BLOCKED: Total exposure would be {total_units_open + abs(units)}. Maximum {self.max_total_units} units allowed"
        
        # Rule 6: Entry zone check (must be in defined zones)
        in_entry_zone = False
        for zone_low, zone_high in self.entry_zones:
            if zone_low <= entry_price <= zone_high:
                in_entry_zone = True
                break
        
        if not in_entry_zone:
            zones_str = ", ".join([f"${low}-${high}" for low, high in self.entry_zones])
            return False, f"❌ BLOCKED: Entry price ${entry_price:.2f} outside entry zones: {zones_str}. Wait for dip!"
        
        # Rule 7: Stop loss mandatory
        if stop_loss is None:
            return False, "❌ BLOCKED: Stop loss is mandatory on Account 001. No naked positions!"
        
        # Rule 8: Take profit mandatory
        if take_profit is None:
            return False, "❌ BLOCKED: Take profit is mandatory on Account 001. Must define exit!"
        
        # Rule 9: Stop loss size check (for LONG)
        if direction == "LONG":
            sl_distance = abs(entry_price - stop_loss)
            if sl_distance < self.min_stop_loss:
                return False, f"❌ BLOCKED: Stop loss too tight (${sl_distance:.2f}). Minimum ${self.min_stop_loss}"
            if sl_distance > self.max_stop_loss:
                return False, f"❌ BLOCKED: Stop loss too wide (${sl_distance:.2f}). Maximum ${self.max_stop_loss}"
        
        # Rule 10: Take profit size check (for LONG)
        if direction == "LONG":
            tp_distance = abs(take_profit - entry_price)
            if tp_distance < self.min_take_profit:
                return False, f"❌ BLOCKED: Take profit too small (${tp_distance:.2f}). Minimum ${self.min_take_profit}"
        
        # Rule 11: Risk:Reward check
        if direction == "LONG" and stop_loss and take_profit:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            rr_ratio = reward / risk if risk > 0 else 0
            
            if rr_ratio < self.min_risk_reward:
                return False, f"❌ BLOCKED: Risk:Reward {rr_ratio:.2f} below minimum {self.min_risk_reward}"
        
        # Rule 12: Trading hours check (London/NY sessions)
        current_hour = datetime.utcnow().hour
        
        # London: 8am-12pm GMT = 8-12 UTC
        # NY: 1pm-4pm GMT = 13-16 UTC
        london_session = 8 <= current_hour < 12
        ny_session = 13 <= current_hour < 16
        
        if not (london_session or ny_session):
            return False, f"❌ BLOCKED: Outside trading hours. London: 8am-12pm GMT, NY: 1pm-4pm GMT. Current: {current_hour}:00 UTC"
        
        # All checks passed!
        logger.info(f"✅ Trade validated: {direction} {abs(units)} {instrument} @ ${entry_price:.2f}")
        logger.info(f"   SL: ${stop_loss:.2f}, TP: ${take_profit:.2f}")
        
        return True, "✅ Trade passes all validation rules"
    
    def check_for_emotional_trading(self, reason: str) -> Tuple[bool, str]:
        """
        Check if trade reason suggests emotional/compensation trading
        
        Returns:
            (is_emotional, warning)
        """
        emotional_keywords = [
            "compensat", "make up", "missed", "catch up",
            "panic", "fomo", "chase", "revenge",
            "too high", "pullback", "reversal", "counter"
        ]
        
        reason_lower = reason.lower()
        
        for keyword in emotional_keywords:
            if keyword in reason_lower:
                return True, f"⚠️ WARNING: Trade reason contains '{keyword}' - suggests emotional trading!"
        
        return False, "✅ Trade reason appears rational"
    
    def get_current_strategy_bias(self) -> str:
        """
        Returns current strategy bias for Account 001
        Always BULLISH for Gold Trump Week
        """
        return "BULLISH - Gold Trump Strategy: Buy dips, target $4,050-$4,100"
    
    def suggest_entry_zones(self, current_price: float) -> str:
        """
        Suggest appropriate entry zones based on current price
        """
        suggestions = []
        
        for zone_low, zone_high in self.entry_zones:
            if current_price > zone_high:
                distance = current_price - zone_high
                suggestions.append(f"${zone_low}-${zone_high} (${distance:.2f} below current)")
        
        if suggestions:
            return "Wait for dip to: " + ", ".join(suggestions)
        else:
            return f"Price ${current_price:.2f} is at/below entry zones. Monitor for LONG setup."


def get_account_001_validator():
    """Get singleton validator instance"""
    global _validator_instance
    if '_validator_instance' not in globals():
        _validator_instance = Account001Validator()
    return _validator_instance


# Example usage and test
if __name__ == '__main__':
    validator = Account001Validator()
    
    print("\n" + "="*80)
    print("ACCOUNT 001 VALIDATOR TESTS")
    print("="*80)
    
    # Test 1: Valid LONG trade
    print("\n✅ Test 1: Valid LONG trade")
    valid, reason = validator.validate_trade(
        instrument="XAU_USD",
        direction="LONG",
        units=300,
        entry_price=3990.0,
        stop_loss=3975.0,
        take_profit=4040.0,
        current_positions=0,
        total_units_open=0
    )
    print(f"   Result: {reason}")
    
    # Test 2: SHORT trade (should be blocked!)
    print("\n❌ Test 2: SHORT trade (BLOCKED)")
    valid, reason = validator.validate_trade(
        instrument="XAU_USD",
        direction="SHORT",
        units=-300,
        entry_price=4030.0,
        stop_loss=4050.0,
        take_profit=4001.0,
        current_positions=0,
        total_units_open=0
    )
    print(f"   Result: {reason}")
    
    # Test 3: Entry too high (should be blocked!)
    print("\n❌ Test 3: Entry too high (BLOCKED)")
    valid, reason = validator.validate_trade(
        instrument="XAU_USD",
        direction="LONG",
        units=300,
        entry_price=4050.0,  # Too high!
        stop_loss=4030.0,
        take_profit=4100.0,
        current_positions=0,
        total_units_open=0
    )
    print(f"   Result: {reason}")
    
    # Test 4: No stop loss (should be blocked!)
    print("\n❌ Test 4: No stop loss (BLOCKED)")
    valid, reason = validator.validate_trade(
        instrument="XAU_USD",
        direction="LONG",
        units=300,
        entry_price=3990.0,
        stop_loss=None,  # Missing!
        take_profit=4040.0,
        current_positions=0,
        total_units_open=0
    )
    print(f"   Result: {reason}")
    
    # Test 5: Emotional trading check
    print("\n⚠️ Test 5: Emotional trading check")
    is_emotional, warning = validator.check_for_emotional_trading(
        "Entering SHORT to compensate for missed trades this morning"
    )
    print(f"   Result: {warning}")
    
    print("\n" + "="*80)
    print("✅ All tests completed")
    print("="*80)




