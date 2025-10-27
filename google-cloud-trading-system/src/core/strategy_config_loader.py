"""
Strategy Configuration Loader - SINGLE SOURCE OF TRUTH
This module ensures there is only ONE way to change strategy configuration
"""

import yaml
import os
from typing import Dict, List, Any
from pathlib import Path

class StrategyConfigLoader:
    """Single source of truth for all strategy configuration"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent / "STRATEGY_CONFIG_MASTER.yaml"
        self._config = None
        self._last_modified = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from master file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Master config file not found: {self.config_path}")
        
        # Check if file was modified
        current_modified = os.path.getmtime(self.config_path)
        if self._last_modified != current_modified:
            self._last_modified = current_modified
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        
        return self._config
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for a specific strategy"""
        config = self.load_config()
        if strategy_name not in config['strategies']:
            raise ValueError(f"Strategy '{strategy_name}' not found in master config")
        return config['strategies'][strategy_name]
    
    def get_account_config(self, account_id: str) -> Dict[str, Any]:
        """Get configuration for a specific account"""
        config = self.load_config()
        for account in config['accounts']:
            if account['id'] == account_id:
                strategy_name = account['strategy']
                strategy_config = self.get_strategy_config(strategy_name)
                return {
                    'account_id': account_id,
                    'name': account['name'],
                    'strategy': strategy_name,
                    'active': account['active'],
                    **strategy_config
                }
        raise ValueError(f"Account '{account_id}' not found in master config")
    
    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Get all account configurations"""
        config = self.load_config()
        accounts = []
        for account in config['accounts']:
            if account['active']:
                strategy_name = account['strategy']
                strategy_config = self.get_strategy_config(strategy_name)
                accounts.append({
                    'account_id': account['id'],
                    'name': account['name'],
                    'strategy': strategy_name,
                    'active': account['active'],
                    **strategy_config
                })
        return accounts
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        config = self.load_config()
        
        validation_rules = config.get('validation', {})
        
        for strategy_name, strategy_config in config['strategies'].items():
            # Check risk limits
            max_portfolio_risk = strategy_config['risk_settings']['max_portfolio_risk']
            if max_portfolio_risk > validation_rules.get('max_portfolio_risk_limit', 0.50):
                errors.append(f"{strategy_name}: max_portfolio_risk {max_portfolio_risk} exceeds limit")
            
            risk_per_trade = strategy_config['risk_settings']['max_risk_per_trade']
            if risk_per_trade < validation_rules.get('min_risk_per_trade', 0.005):
                errors.append(f"{strategy_name}: max_risk_per_trade {risk_per_trade} below minimum")
            
            if risk_per_trade > validation_rules.get('max_risk_per_trade', 0.02):
                errors.append(f"{strategy_name}: max_risk_per_trade {risk_per_trade} exceeds maximum")
        
        return errors

# Global instance - SINGLE SOURCE OF TRUTH
_config_loader = None

def get_strategy_config_loader() -> StrategyConfigLoader:
    """Get the global strategy configuration loader"""
    global _config_loader
    if _config_loader is None:
        _config_loader = StrategyConfigLoader()
    return _config_loader

def get_strategy_config(strategy_name: str) -> Dict[str, Any]:
    """Get strategy configuration - ONLY WAY TO ACCESS CONFIG"""
    return get_strategy_config_loader().get_strategy_config(strategy_name)

def get_account_config(account_id: str) -> Dict[str, Any]:
    """Get account configuration - ONLY WAY TO ACCESS CONFIG"""
    return get_strategy_config_loader().get_account_config(account_id)

def get_all_accounts() -> List[Dict[str, Any]]:
    """Get all account configurations - ONLY WAY TO ACCESS CONFIG"""
    return get_strategy_config_loader().get_all_accounts()

def validate_all_configs() -> List[str]:
    """Validate all configurations - ONLY WAY TO VALIDATE CONFIG"""
    return get_strategy_config_loader().validate_config()
