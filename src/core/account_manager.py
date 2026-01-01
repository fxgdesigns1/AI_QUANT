#!/usr/bin/env python3
"""
Account Management System - CORRECTED VERSION
Production-ready multi-account management for Google Cloud deployment
FIXED: Strategy mappings and risk settings aligned with dashboard
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .oanda_client import OandaClient, OandaAccount
from ..strategies.ultra_strict_forex import UltraStrictForexStrategy
from ..strategies.gold_scalping import GoldScalpingStrategy

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AccountConfig:
    """OANDA account configuration"""
    account_id: str
    account_name: str  # PRIMARY, GOLD_SCALP, STRATEGY_ALPHA
    api_key: str
    environment: str
    strategy_name: str
    risk_settings: Dict[str, Any]
    instruments: List[str]

class AccountManager:
    """Production multi-account management system - CORRECTED"""
    
    def __init__(self):
        """Initialize account manager with configurations"""
        self.accounts: Dict[str, OandaClient] = {}
        self.account_configs: Dict[str, AccountConfig] = {}
        self.strategy_mappings: Dict[str, str] = {}
        
        # Load account configurations
        self._load_account_configs()
        
        # Initialize accounts
        self._initialize_accounts()
        
        logger.info("✅ Account manager initialized")
        logger.info(f"📊 Active accounts: {len(self.accounts)}")
        for account_id, config in self.account_configs.items():
            logger.info(f"   • {config.account_name}: {account_id} - Strategy: {config.strategy_name}")
    
    def _load_account_configs(self):
        """Load account configurations from environment - CORRECTED MAPPINGS"""
        # Primary Account (Gold Scalping 5M) - CORRECTED
        primary_account = AccountConfig(
            account_id=os.getenv('PRIMARY_ACCOUNT'),
            account_name="PRIMARY",
            api_key=os.getenv('OANDA_API_KEY'),
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice'),
            strategy_name="gold_scalping",  # CORRECTED: Was ultra_strict_forex
            risk_settings={
                'max_risk_per_trade': float(os.getenv('PRIMARY_MAX_RISK_PER_TRADE', '0.02')),
                'max_portfolio_risk': float(os.getenv('PRIMARY_MAX_PORTFOLIO_RISK', '0.75')),  # CORRECTED: Was 0.10
                'max_positions': int(os.getenv('PRIMARY_MAX_POSITIONS', '5')),
                'daily_trade_limit': int(os.getenv('PRIMARY_DAILY_TRADE_LIMIT', '50'))
            },
            instruments=['XAU_USD']  # CORRECTED: Gold only for scalping
        )
        
        # Gold Scalping Account (Account 010) - Ultra Strict Forex Strategy - OPTIMIZED
        gold_account = AccountConfig(
            account_id=os.getenv('GOLD_SCALP_ACCOUNT'),
            account_name="GOLD_SCALP",
            api_key=os.getenv('OANDA_API_KEY'),
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice'),
            strategy_name="ultra_strict_forex",  # Account 010 uses Ultra Strict Forex
            risk_settings={
                'max_risk_per_trade': float(os.getenv('GOLD_MAX_RISK_PER_TRADE', '0.015')),
                'max_portfolio_risk': float(os.getenv('GOLD_MAX_PORTFOLIO_RISK', '0.75')),
                'max_positions': int(os.getenv('GOLD_MAX_POSITIONS', '50')),
                'daily_trade_limit': int(os.getenv('GOLD_DAILY_TRADE_LIMIT', '100'))
            },
            instruments=['GBP_USD']  # OPTIMIZED: Removed EUR/USD, USD/JPY, AUD/USD (all toxic on this strategy)
        )
        
        # Strategy Alpha Account (Combined Portfolio) - OPTIMIZED
        alpha_account = AccountConfig(
            account_id=os.getenv('STRATEGY_ALPHA_ACCOUNT'),
            account_name="STRATEGY_ALPHA",
            api_key=os.getenv('OANDA_API_KEY'),
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice'),
            strategy_name="momentum_trading",
            risk_settings={
                'max_risk_per_trade': float(os.getenv('ALPHA_MAX_RISK_PER_TRADE', '0.025')),
                'max_portfolio_risk': float(os.getenv('ALPHA_MAX_PORTFOLIO_RISK', '0.75')),
                'max_positions': int(os.getenv('ALPHA_MAX_POSITIONS', '50')),
                'daily_trade_limit': int(os.getenv('ALPHA_DAILY_TRADE_LIMIT', '100'))
            },
            instruments=['GBP_USD', 'USD_JPY', 'USD_CAD', 'NZD_USD']  # OPTIMIZED: Only 100% win rate pairs
        )
        
        # Store configurations
        for config in [primary_account, gold_account, alpha_account]:
            if config.account_id:
                self.account_configs[config.account_id] = config
                self.strategy_mappings[config.account_id] = config.strategy_name
    
    def _initialize_accounts(self):
        """Initialize OANDA clients for each account"""
        for account_id, config in self.account_configs.items():
            try:
                # Create OANDA client for account
                client = OandaClient(
                    api_key=config.api_key,
                    account_id=account_id,
                    environment=config.environment
                )
                
                # Test connection
                if client.is_connected():
                    self.accounts[account_id] = client
                    logger.info(f"✅ Account connected: {config.account_name} ({account_id})")
                else:
                    logger.error(f"❌ Failed to connect account: {config.account_name} ({account_id})")
                    
            except Exception as e:
                logger.error(f"❌ Account initialization error: {config.account_name} ({account_id}) - {e}")
    
    def get_account_client(self, account_id: str) -> Optional[OandaClient]:
        """Get OANDA client for specific account"""
        return self.accounts.get(account_id)
    
    def get_account_config(self, account_id: str) -> Optional[AccountConfig]:
        """Get configuration for specific account"""
        return self.account_configs.get(account_id)
    
    def get_strategy_name(self, account_id: str) -> Optional[str]:
        """Get strategy name for specific account"""
        return self.strategy_mappings.get(account_id)
    
    def get_active_accounts(self) -> List[str]:
        """Get list of active account IDs"""
        return list(self.accounts.keys())
    
    def get_account_status(self, account_id: str) -> Dict[str, Any]:
        """Get current status of specific account"""
        try:
            client = self.get_account_client(account_id)
            config = self.get_account_config(account_id)
            
            if not client or not config:
                return {
                    'account_id': account_id,
                    'status': 'inactive',
                    'error': 'Account not initialized'
                }
            
            # Get account info
            account_info = client.get_account_info()
            
            return {
                'account_id': account_id,
                'account_name': config.account_name,
                'strategy': config.strategy_name,
                'status': 'active',
                'balance': account_info.balance,
                'currency': account_info.currency,
                'unrealized_pl': account_info.unrealized_pl,
                'realized_pl': account_info.realized_pl,
                'margin_used': account_info.margin_used,
                'margin_available': account_info.margin_available,
                'open_trades': account_info.open_trade_count,
                'open_positions': account_info.open_position_count,
                'risk_settings': config.risk_settings,
                'instruments': config.instruments,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Account status error: {account_id} - {e}")
            return {
                'account_id': account_id,
                'status': 'error',
                'error': str(e)
            }
    
    def get_all_accounts_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current status of all accounts"""
        return {
            account_id: self.get_account_status(account_id)
            for account_id in self.get_active_accounts()
        }
    
    def get_account_info(self, account_id: str = None):
        """Get account information for specific account or first available"""
        try:
            if account_id:
                client = self.get_account_client(account_id)
                if client:
                    return client.get_account_info()
            else:
                # Return first available account info
                for client in self.accounts.values():
                    return client.get_account_info()
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get account info: {e}")
            return None
    
    def get_accounts_for_strategy_isolation(self) -> Dict[str, Dict[str, Any]]:
        """Get accounts organized for strategy isolation"""
        isolation_data = {}
        
        for account_id, config in self.account_configs.items():
            client = self.accounts.get(account_id)
            if not client:
                continue
            
            try:
                account_info = client.get_account_info()
                if not account_info:
                    continue
                
                isolation_data[account_id] = {
                    'account_id': account_id,
                    'account_name': config.account_name,
                    'strategy_name': config.strategy_name,
                    'instruments': config.instruments,
                    'risk_settings': config.risk_settings,
                    'balance': account_info.balance,
                    'margin_used': account_info.margin_used,
                    'margin_available': account_info.margin_available,
                    'open_positions': account_info.open_position_count,
                    'unrealized_pl': account_info.unrealized_pl,
                    'realized_pl': account_info.realized_pl,
                    'isolation_status': 'active',
                    'last_update': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Failed to get isolation data for {account_id}: {e}")
                isolation_data[account_id] = {
                    'account_id': account_id,
                    'account_name': config.account_name,
                    'strategy_name': config.strategy_name,
                    'isolation_status': 'error',
                    'error': str(e)
                }
        
        return isolation_data
    
    def validate_strategy_isolation(self) -> Dict[str, Any]:
        """Validate that strategies are properly isolated across accounts"""
        try:
            validation_results = {
                'timestamp': datetime.now().isoformat(),
                'isolation_valid': True,
                'account_assignments': {},
                'conflicts': [],
                'recommendations': []
            }
            
            # Check account assignments
            for account_id, config in self.account_configs.items():
                validation_results['account_assignments'][account_id] = {
                    'account_name': config.account_name,
                    'strategy': config.strategy_name,
                    'instruments': config.instruments,
                    'risk_settings': config.risk_settings
                }
            
            # Check for conflicts (same strategy on multiple accounts)
            strategy_accounts = {}
            for account_id, config in self.account_configs.items():
                strategy = config.strategy_name
                if strategy not in strategy_accounts:
                    strategy_accounts[strategy] = []
                strategy_accounts[strategy].append(account_id)
            
            for strategy, accounts in strategy_accounts.items():
                if len(accounts) > 1:
                    validation_results['conflicts'].append({
                        'type': 'strategy_duplication',
                        'strategy': strategy,
                        'accounts': accounts,
                        'message': f"Strategy '{strategy}' assigned to multiple accounts"
                    })
                    validation_results['isolation_valid'] = False
            
            # Check for instrument conflicts
            instrument_accounts = {}
            for account_id, config in self.account_configs.items():
                for instrument in config.instruments:
                    if instrument not in instrument_accounts:
                        instrument_accounts[instrument] = []
                    instrument_accounts[instrument].append(account_id)
            
            for instrument, accounts in instrument_accounts.items():
                if len(accounts) > 1:
                    validation_results['conflicts'].append({
                        'type': 'instrument_overlap',
                        'instrument': instrument,
                        'accounts': accounts,
                        'message': f"Instrument '{instrument}' traded on multiple accounts"
                    })
                    # Note: This might be intentional for diversification
            
            # Generate recommendations
            if not validation_results['isolation_valid']:
                validation_results['recommendations'].append(
                    "Consider assigning unique strategies to each account for better isolation"
                )
            
            if len(instrument_accounts) > 0:
                validation_results['recommendations'].append(
                    "Monitor instrument overlap to ensure proper risk management"
                )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Strategy isolation validation failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'isolation_valid': False,
                'error': str(e)
            }

# Global account manager instance
account_manager = AccountManager()

def get_account_manager() -> AccountManager:
    """Get the global account manager instance"""
    return account_manager
