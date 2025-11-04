"""
Trade Size Validator - Prevents Micro Trades
============================================

Enforces minimum trade sizes to prevent micro trades that slip through.
All trades must meet minimum size requirements before execution.
"""

import logging
from typing import Dict, Any, Optional
import yaml
import os

logger = logging.getLogger(__name__)

class TradeSizeValidator:
    """Validates trade sizes against minimum requirements"""
    
    def __init__(self, config_path: str = None):
        """Initialize with config from strategy_config.yaml"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'strategy_config.yaml')
        
        self.config_path = config_path
        self.min_trade_size = 10000  # Default minimum
        self.enforce_minimum = True
        self.micro_trade_alert = True
        self.min_profit_target = 1000  # Default minimum profit
        self.enforce_minimum_profit = True
        self.profit_scaling_enabled = True
        
        self._load_config()
        # Calibrate sensible minimums for practice accounts
        try:
            if os.getenv('OANDA_ENV', 'practice').lower() == 'practice':
                self.min_trade_size = int(os.getenv('PRACTICE_MIN_TRADE_SIZE', str(min(self.min_trade_size, 1000))))
                self.min_profit_target = float(os.getenv('PRACTICE_MIN_PROFIT_TARGET', '10'))
                logger.info(f"Practice mode: min_size={self.min_trade_size}, min_profit=${self.min_profit_target}")
        except Exception:
            pass
    
    def _load_config(self):
        """Load configuration from strategy_config.yaml"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            system_config = config.get('system', {})
            self.min_trade_size = system_config.get('min_trade_size', 10000)
            self.enforce_minimum = system_config.get('enforce_minimum_size', True)
            self.micro_trade_alert = system_config.get('micro_trade_alert', True)
            self.min_profit_target = system_config.get('min_profit_target', 1000)
            self.enforce_minimum_profit = system_config.get('enforce_minimum_profit', True)
            self.profit_scaling_enabled = system_config.get('profit_scaling_enabled', True)
            
            logger.info(f"Trade size validator initialized: min_size={self.min_trade_size}, enforce={self.enforce_minimum}")
            
        except Exception as e:
            logger.error(f"Failed to load trade size config: {e}")
            # Use defaults
    
    def validate_trade_size(self, instrument: str, units: int, strategy_name: str) -> Dict[str, Any]:
        """
        Validate trade size against minimum requirements
        
        Args:
            instrument: Trading instrument (e.g., 'EUR_USD')
            units: Number of units to trade
            strategy_name: Name of strategy requesting trade
            
        Returns:
            Dict with validation result:
            {
                'valid': bool,
                'reason': str,
                'min_required': int,
                'requested': int,
                'should_alert': bool
            }
        """
        result = {
            'valid': True,
            'reason': 'Trade size acceptable',
            'min_required': self.min_trade_size,
            'requested': abs(units),
            'should_alert': False
        }
        
        # Check if trade is below minimum
        if abs(units) < self.min_trade_size:
            result['valid'] = False
            result['reason'] = f"Trade size {abs(units)} below minimum {self.min_trade_size}"
            result['should_alert'] = self.micro_trade_alert
            
            logger.warning(f"MICRO TRADE REJECTED: {strategy_name} tried {units} units of {instrument} (min: {self.min_trade_size})")
            
            if self.micro_trade_alert:
                self._send_micro_trade_alert(instrument, units, strategy_name)
        
        return result
    
    def validate_profit_potential(self, instrument: str, units: int, take_profit_pips: float, strategy_name: str) -> Dict[str, Any]:
        """
        Validate profit potential against minimum requirements
        
        Args:
            instrument: Trading instrument (e.g., 'EUR_USD')
            units: Number of units to trade
            take_profit_pips: Take profit in pips
            strategy_name: Name of strategy requesting trade
            
        Returns:
            Dict with validation result:
            {
                'valid': bool,
                'reason': str,
                'min_required': float,
                'potential_profit': float,
                'should_alert': bool
            }
        """
        result = {
            'valid': True,
            'reason': 'Profit potential acceptable',
            'min_required': self.min_profit_target,
            'potential_profit': 0.0,
            'should_alert': False
        }
        
        # Calculate potential profit
        # For EUR/USD: 1 pip = $1 per 10,000 units
        pip_value = units / 10000
        potential_profit = pip_value * take_profit_pips
        
        result['potential_profit'] = potential_profit
        
        # Check if profit meets minimum
        if potential_profit < self.min_profit_target:
            result['valid'] = False
            result['reason'] = f"Profit potential ${potential_profit:.0f} below minimum ${self.min_profit_target}"
            result['should_alert'] = True
            
            logger.warning(f"LOW PROFIT TRADE REJECTED: {strategy_name} - {instrument} {units} units, {take_profit_pips} pips = ${potential_profit:.0f} (min: ${self.min_profit_target})")
            
            if result['should_alert']:
                self._send_low_profit_alert(instrument, units, take_profit_pips, potential_profit, strategy_name)
        
        return result
    
    def _send_micro_trade_alert(self, instrument: str, units: int, strategy_name: str):
        """Send alert about micro trade attempt"""
        try:
            from ..notifications.premium_telegram_notifier import PremiumTelegramNotifier
            
            notifier = PremiumTelegramNotifier()
            message = f"""🚨 **MICRO TRADE BLOCKED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **Strategy:** {strategy_name}
💱 **Instrument:** {instrument}
📊 **Units:** {units:,} (MIN: {self.min_trade_size:,})
🛡️ **Action:** Trade rejected

**System Protection Active** ✅
No micro trades allowed!"""
            
            notifier.send_alert(message, priority='HIGH')
            
        except Exception as e:
            logger.error(f"Failed to send micro trade alert: {e}")
    
    def _send_low_profit_alert(self, instrument: str, units: int, take_profit_pips: float, potential_profit: float, strategy_name: str):
        """Send alert about low profit trade attempt"""
        try:
            from ..notifications.premium_telegram_notifier import PremiumTelegramNotifier
            
            notifier = PremiumTelegramNotifier()
            message = f"""🚨 **LOW PROFIT TRADE BLOCKED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **Strategy:** {strategy_name}
💱 **Instrument:** {instrument}
📊 **Units:** {units:,}
🎯 **Take Profit:** {take_profit_pips} pips
💰 **Potential Profit:** ${potential_profit:.0f}
🛡️ **Minimum Required:** ${self.min_profit_target}

**System Protection Active** ✅
No trades below $1,000 profit allowed!"""
            
            notifier.send_alert(message, priority='HIGH')
            
        except Exception as e:
            logger.error(f"Failed to send low profit alert: {e}")
    
    def get_minimum_size(self) -> int:
        """Get current minimum trade size"""
        return self.min_trade_size
    
    def is_enforcement_enabled(self) -> bool:
        """Check if size enforcement is enabled"""
        return self.enforce_minimum
    
    def update_config(self, min_size: int = None, enforce: bool = None, alert: bool = None):
        """Update configuration dynamically"""
        if min_size is not None:
            self.min_trade_size = min_size
        if enforce is not None:
            self.enforce_minimum = enforce
        if alert is not None:
            self.micro_trade_alert = alert
        
        logger.info(f"Trade size validator updated: min={self.min_trade_size}, enforce={self.enforce_minimum}")

# Global instance
_trade_size_validator = None

def get_trade_size_validator() -> TradeSizeValidator:
    """Get global trade size validator instance"""
    global _trade_size_validator
    if _trade_size_validator is None:
        _trade_size_validator = TradeSizeValidator()
    return _trade_size_validator
