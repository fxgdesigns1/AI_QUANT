#!/usr/bin/env python3
"""
Configuration Loader - YAML-Based Dynamic System
Loads accounts, strategies, and settings from accounts.yaml
Makes system infinitely scalable without code changes
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AccountConfig:
    """Account configuration from YAML"""
    id: str
    name: str
    display_name: str
    strategy: str
    description: str
    instruments: List[str]
    risk_settings: Dict[str, Any]
    active: bool
    priority: int
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.id:
            raise ValueError("Account ID is required")
        if not self.strategy:
            raise ValueError("Strategy is required")
        if not self.instruments:
            raise ValueError("At least one instrument is required")


@dataclass
class StrategyConfig:
    """Strategy configuration from YAML"""
    id: str
    class_name: str
    module: str
    function: str
    description: str
    best_for: str
    timeframe: str


class ConfigLoader:
    """Loads and validates YAML configuration"""
    
    def __init__(self, config_file: str = "accounts.yaml"):
        """Initialize config loader"""
        self.config_file = config_file
        self.config_path = self._find_config_file()
        self.accounts: List[AccountConfig] = []
        self.strategies: Dict[str, StrategyConfig] = {}
        self.global_settings: Dict[str, Any] = {}
        
        if self.config_path:
            self._load_config()
            logger.info(f"✅ Configuration loaded from {self.config_path}")
            logger.info(f"   Accounts: {len(self.accounts)}")
            logger.info(f"   Strategies: {len(self.strategies)}")
        else:
            logger.warning(f"⚠️ Config file {config_file} not found - using fallback")
    
    def _find_config_file(self) -> Optional[Path]:
        """Find accounts.yaml in various locations"""
        possible_paths = [
            Path(self.config_file),
            Path(__file__).parent.parent.parent / self.config_file,
            Path.cwd() / self.config_file,
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def _load_config(self):
        """Load YAML configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load accounts
            accounts_data = config.get('accounts', [])
            for acc_data in accounts_data:
                try:
                    account = AccountConfig(
                        id=acc_data['id'],
                        name=acc_data.get('name', f"Account {acc_data['id'][-3:]}"),
                        display_name=acc_data.get('display_name', acc_data.get('name', 'Trading Bot')),
                        strategy=acc_data['strategy'],
                        description=acc_data.get('description', ''),
                        instruments=acc_data.get('instruments', []),
                        risk_settings=acc_data.get('risk_settings', {}),
                        active=acc_data.get('active', True),
                        priority=acc_data.get('priority', 999)
                    )
                    
                    if account.active:
                        self.accounts.append(account)
                        logger.info(f"✅ Loaded account: {account.display_name} ({account.id})")
                    else:
                        logger.info(f"⏸️  Skipped inactive account: {account.display_name}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to load account {acc_data.get('id', 'unknown')}: {e}")
            
            # Load strategies
            strategies_data = config.get('strategies', {})
            for strategy_id, strategy_data in strategies_data.items():
                try:
                    strategy = StrategyConfig(
                        id=strategy_id,
                        class_name=strategy_data.get('class_name', ''),
                        module=strategy_data.get('module', ''),
                        function=strategy_data.get('function', ''),
                        description=strategy_data.get('description', ''),
                        best_for=strategy_data.get('best_for', ''),
                        timeframe=strategy_data.get('timeframe', '')
                    )
                    self.strategies[strategy_id] = strategy
                    logger.info(f"✅ Registered strategy: {strategy_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to load strategy {strategy_id}: {e}")
            
            # Load global settings
            self.global_settings = config.get('global_settings', {})
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
    
    def get_active_accounts(self) -> List[AccountConfig]:
        """Get all active accounts, sorted by priority"""
        return sorted(self.accounts, key=lambda x: x.priority)
    
    def get_account_by_id(self, account_id: str) -> Optional[AccountConfig]:
        """Get specific account configuration"""
        for account in self.accounts:
            if account.id == account_id:
                return account
        return None
    
    def get_strategy_config(self, strategy_id: str) -> Optional[StrategyConfig]:
        """Get strategy configuration"""
        return self.strategies.get(strategy_id)
    
    def get_all_strategies(self) -> Dict[str, StrategyConfig]:
        """Get all registered strategies"""
        return self.strategies
    
    def get_global_setting(self, key: str, default: Any = None) -> Any:
        """Get global setting value"""
        return self.global_settings.get(key, default)
    
    def reload(self):
        """Reload configuration from file"""
        self.accounts = []
        self.strategies = {}
        self.global_settings = {}
        self._load_config()
        logger.info("🔄 Configuration reloaded")


# Global instance
_config_loader = None


def get_config_loader() -> ConfigLoader:
    """Get global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def reload_config():
    """Reload configuration from file"""
    global _config_loader
    if _config_loader:
        _config_loader.reload()
    else:
        _config_loader = ConfigLoader()


