#!/usr/bin/env python3
"""
STRATEGY SWITCHER - Smooth strategy transitions
Handles strategy switching without system disruption
"""
import os
import sys
import yaml
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StrategySwitcher:
    def __init__(self, config_path: str = 'accounts.yaml'):
        self.config_path = config_path
        self.config = None
        self.load_config()
    
    def load_config(self):
        """Load accounts configuration"""
        config_paths = [
            self.config_path,
            '/workspace/google-cloud-trading-system/accounts.yaml',
            '/workspace/accounts.yaml'
        ]
        
        for path in config_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r') as f:
                        self.config = yaml.safe_load(f)
                    logger.info(f"✓ Loaded config from {path}")
                    return
                except Exception as e:
                    logger.error(f"Error loading {path}: {e}")
        
        # Create default config if none exists
        if not self.config:
            logger.warning("No accounts.yaml found - creating default")
            self.config = {
                'accounts': [
                    {
                        'id': '101-004-30719775-008',
                        'name': 'Account 008',
                        'strategy': 'momentum_trading',
                        'active': True,
                        'trading_pairs': ['EUR_USD', 'GBP_USD', 'XAU_USD']
                    }
                ]
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info(f"✓ Saved config to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get_account_strategy(self, account_id: str) -> Optional[str]:
        """Get current strategy for an account"""
        for account in self.config.get('accounts', []):
            if account.get('id') == account_id:
                return account.get('strategy')
        return None
    
    def switch_strategy(self, account_id: str, new_strategy: str, save: bool = True) -> bool:
        """Switch strategy for an account"""
        logger.info(f"🔄 Switching strategy for {account_id[-3:]} to {new_strategy}")
        
        # Find account
        account_found = False
        for account in self.config.get('accounts', []):
            if account.get('id') == account_id:
                old_strategy = account.get('strategy', 'unknown')
                account['strategy'] = new_strategy
                account['last_switch'] = datetime.now().isoformat()
                account_found = True
                logger.info(f"✓ Strategy changed: {old_strategy} → {new_strategy}")
                break
        
        if not account_found:
            logger.error(f"❌ Account {account_id} not found in config")
            return False
        
        if save:
            if self.save_config():
                logger.info("✅ Strategy switch complete - config saved")
                return True
            else:
                logger.error("❌ Failed to save config")
                return False
        
        return True
    
    def list_strategies(self) -> Dict[str, list]:
        """List all accounts and their strategies"""
        accounts_by_strategy = {}
        
        for account in self.config.get('accounts', []):
            strategy = account.get('strategy', 'unknown')
            if strategy not in accounts_by_strategy:
                accounts_by_strategy[strategy] = []
            accounts_by_strategy[strategy].append({
                'id': account.get('id'),
                'name': account.get('name', 'Unknown'),
                'active': account.get('active', False)
            })
        
        return accounts_by_strategy
    
    def graceful_restart_required(self) -> bool:
        """Check if graceful restart is needed after strategy switch"""
        # Strategy switching may require system restart
        # Check if system supports hot-reload
        return True  # Default: restart required
    
    def get_restart_command(self) -> str:
        """Get command to restart system after strategy switch"""
        return """
# To apply strategy changes, restart the trading system:
cd /workspace
pkill -f ai_trading_system.py  # Stop current instance
python3 START_TRADING_SYSTEM.py  # Start with new strategy
"""

if __name__ == "__main__":
    switcher = StrategySwitcher()
    
    # Example usage
    print("Current strategies:")
    strategies = switcher.list_strategies()
    for strategy, accounts in strategies.items():
        print(f"\n{strategy}:")
        for acc in accounts:
            status = "ACTIVE" if acc['active'] else "INACTIVE"
            print(f"  • {acc['name']} ({acc['id'][-3:]}): {status}")
    
    # Example: Switch strategy
    # switcher.switch_strategy('101-004-30719775-008', 'gold_scalping')
