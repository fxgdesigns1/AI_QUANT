#!/usr/bin/env python3
"""
Strategy Manager - Modular Strategy Configuration System
Allows easy tweaking of individual strategies without code changes
Includes lock mechanism to finalize perfected strategies
"""

import yaml
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StrategyConfig:
    strategy_id: str
    strategy_name: str
    account_name: str
    enabled: bool
    locked: bool
    instruments: List[str]
    risk_per_trade: float
    max_positions: int
    max_daily_trades: int
    # Add other fields from YAML as needed
    lot_size: int

class StrategyManager:
    """Manage and configure strategies modularly"""

    def __init__(self, config_file: str = "strategy_config.yaml"):
        """Initialize strategy manager"""
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.locked_strategies: list = []
        self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load strategy configuration from YAML"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)

            # Check for locked strategies
            self.locked_strategies = [
                name for name, config in self.config.items()
                if isinstance(config, dict) and config.get('locked', False)
            ]

            if self.locked_strategies:
                logger.warning(f"🔒 LOCKED STRATEGIES (read-only): {', '.join(self.locked_strategies)}")

            logger.info(f"✅ Strategy config loaded from {self.config_file}")
            return self.config

        except FileNotFoundError:
            logger.error(f"❌ Config file not found: {self.config_file}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parsing error: {e}")
            return {}

    @property
    def strategies(self) -> Dict[str, Any]:
        """Backward-compatible alias used by MultiStrategyExecutor."""
        return self.config
    def get_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific strategy"""
        config = self.config.get(strategy_name)

        if not config:
            logger.warning(f"⚠️ Strategy '{strategy_name}' not found in config")
            return None

        if not config.get('enabled', True):
            logger.info(f"⏸️ Strategy '{strategy_name}' is disabled")
            return None

        return config

    def update_strategy_parameter(
        self,
        strategy_name: str,
        section: str,
        parameter: str,
        value: Any
    ) -> bool:
        """
        Update a single parameter for a strategy
        """
        if strategy_name in self.locked_strategies:
            logger.error(f"🔒 BLOCKED: Strategy '{strategy_name}' is LOCKED and cannot be modified!")
            logger.error(f"    To modify, set 'locked: false' in {self.config_file}")
            return False

        if strategy_name not in self.config:
            logger.error(f"❌ Strategy '{strategy_name}' not found")
            return False

        try:
            old_value = self.config[strategy_name][section][parameter]
            self.config[strategy_name][section][parameter] = value
            self._save_config()
            logger.info(f"✅ Updated {strategy_name}.{section}.{parameter}: {old_value} → {value}")
            self._log_change(strategy_name, section, parameter, old_value, value)
            return True
        except KeyError as e:
            logger.error(f"❌ Invalid parameter path: {section}.{parameter}")
            return False

    def lock_strategy(self, strategy_name: str) -> bool:
        """Lock a strategy to prevent further changes"""
        if strategy_name not in self.config:
            logger.error(f"❌ Strategy '{strategy_name}' not found")
            return False
        
        self.config[strategy_name]['locked'] = True
        self.locked_strategies.append(strategy_name)
        self._save_config()
        
        logger.info(f"🔒 Strategy '{strategy_name}' is now LOCKED")
        logger.info(f"    No further changes allowed until unlocked")
        
        return True

    def unlock_strategy(self, strategy_name: str) -> bool:
        """Unlock a strategy to allow changes"""
        if strategy_name not in self.config:
            logger.error(f"❌ Strategy '{strategy_name}' not found")
            return False
        
        self.config[strategy_name]['locked'] = False
        if strategy_name in self.locked_strategies:
            self.locked_strategies.remove(strategy_name)
        self._save_config()
        
        logger.info(f"🔓 Strategy '{strategy_name}' is now UNLOCKED")
        
        return True

    def disable_strategy(self, strategy_name: str) -> bool:
        """Disable a strategy (stops trading but keeps config)"""
        if strategy_name in self.locked_strategies:
            logger.error(f"🔒 Cannot disable locked strategy '{strategy_name}'")
            return False
        
        if strategy_name not in self.config:
            logger.error(f"❌ Strategy '{strategy_name}' not found")
            return False
        
        self.config[strategy_name]['enabled'] = False
        self._save_config()
        
        logger.warning(f"⏸️ Strategy '{strategy_name}' DISABLED")
        
        return True

    def enable_strategy(self, strategy_name: str) -> bool:
        """Enable a strategy"""
        if strategy_name not in self.config:
            logger.error(f"❌ Strategy '{strategy_name}' not found")
            return False
        
        self.config[strategy_name]['enabled'] = True
        self._save_config()
        
        logger.info(f"▶️ Strategy '{strategy_name}' ENABLED")
        
        return True

    def _save_config(self):
        """Save configuration to YAML file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"💾 Config saved to {self.config_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save config: {e}")

    def _log_change(self, strategy: str, section: str, parameter: str, old_value: Any, new_value: Any):
        """Log strategy changes to file"""
        log_file = "strategy_changes.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = (
            f"[{timestamp}] {strategy}.{section}.{parameter}: "
            f"{old_value} → {new_value}\n"
        )
        
        with open(log_file, 'a') as f:
            f.write(log_entry)

    def get_status_report(self) -> str:
        """Get detailed status report of all strategies"""
        report = "\n" + "="*60 + "\n"
        report += "🎯 STRATEGY STATUS REPORT\n"
        report += "="*60 + "\n\n"
        
        for strategy_name, config in self.config.items():
            if strategy_name == 'system' or not isinstance(config, dict):
                continue
            
            locked = "🔒 LOCKED" if config.get('locked', False) else "🔓 Unlocked"
            enabled = "▶️ ENABLED" if config.get('enabled', True) else "⏸️ DISABLED"
            account = config.get('account', 'N/A')
            
            report += f"Strategy: {strategy_name.upper()}\n"
            report += f"  Status: {enabled} | {locked}\n"
            report += f"  Account: {account}\n"
            
            if 'parameters' in config:
                report += f"  Lot Size: {config['parameters'].get('lot_size', 'N/A')}\n"
                report += f"  Max Trades/Day: {config['parameters'].get('max_trades_per_day', 'N/A')}\n"
            
            if 'risk' in config:
                report += f"  Stop Loss: {config['risk'].get('stop_loss_pct', 'N/A')*100:.2f}%\n"
                report += f"  Take Profit: {config['risk'].get('take_profit_pct', 'N/A')*100:.2f}%\n"
            
            report += "\n"
        
        report += "="*60 + "\n"
        
        return report

# --- Singleton ---
_strategy_manager_instance: Optional[StrategyManager] = None

def get_strategy_manager(config_file: str = "strategy_config.yaml") -> StrategyManager:
    """Get the singleton instance of the StrategyManager."""
    global _strategy_manager_instance
    if _strategy_manager_instance is None:
        _strategy_manager_instance = StrategyManager(config_file=config_file)
    return _strategy_manager_instance

__all__ = ["get_strategy_manager", "StrategyConfig"] # Export StrategyConfig

