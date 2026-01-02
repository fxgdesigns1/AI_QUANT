#!/usr/bin/env python3
"""
Dynamic Account Manager - Config-Driven
Automatically discovers and manages accounts from accounts.yaml
NO CODE CHANGES needed to add/remove/modify accounts!
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .oanda_client import OandaClient, OandaAccount
from .config_loader import get_config_loader, AccountConfig as YAMLAccountConfig
from .paper_broker import PaperBroker

logger = logging.getLogger(__name__)


@dataclass
class AccountConfig:
    """Runtime account configuration"""
    account_id: str
    account_name: str
    display_name: str
    api_key: str
    environment: str
    strategy_name: str
    risk_settings: Dict[str, Any]
    instruments: List[str]
    active: bool
    priority: int


class DynamicAccountManager:
    """Production multi-account manager - FULLY AUTOMATIC"""
    
    def __init__(self):
        """Initialize account manager from YAML configuration"""
        self.accounts: Dict[str, Any] = {}  # Can be OandaClient or PaperBroker
        self.account_configs: Dict[str, AccountConfig] = {}
        self.strategy_mappings: Dict[str, str] = {}
        
        # Load from YAML
        self._load_from_yaml()
        
        # Initialize accounts
        self._initialize_accounts()
        
        logger.info("✅ Dynamic Account Manager initialized")
        logger.info(f"📊 Active accounts: {len(self.accounts)}")
        for account_id, config in self.account_configs.items():
            logger.info(f"   • {config.display_name}: {account_id[-3:]} - {config.strategy_name}")
    
    def _load_from_yaml(self):
        """Load ALL accounts directly from accounts.yaml
        
        NOTE: Environment variables should be loaded by runner_src/runner/main.py
        This method only reads from os.environ (no dotenv loading here).
        """
        import yaml
        
        try:
            # Get API credentials from environment (already loaded by runner)
            api_key = os.getenv('OANDA_API_KEY')
            environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
            
            # Paper-mode friendly: warn if missing but continue
            if not api_key:
                logger.info("ℹ️ OANDA_API_KEY not found - will use paper broker (no network calls)")
            else:
                logger.info("ℹ️ OANDA_API_KEY found in environment")
            
            # Load accounts.yaml DIRECTLY (no config_loader middleman)
            config_path = os.path.join(os.path.dirname(__file__), '../../accounts.yaml')
            # Resolve the absolute path
            config_path = os.path.abspath(config_path)
            logger.info(f"📂 Loading accounts from: {config_path}")
            
            # Check if file exists, if not try alternative paths
            if not os.path.exists(config_path):
                logger.warning(f"⚠️  File not found at {config_path}")
                # Debug: List files in /app directory
                try:
                    app_files = os.listdir('/app')
                    logger.info(f"📁 Files in /app: {app_files}")
                except Exception as e:
                    logger.warning(f"Could not list /app directory: {e}")
                
                # Try alternative paths
                alternative_paths = [
                    '/app/accounts.yaml',
                    os.path.join('/app', 'accounts.yaml'),
                    os.path.join(os.getcwd(), 'accounts.yaml')
                ]
                for alt_path in alternative_paths:
                    logger.info(f"🔍 Checking path: {alt_path}")
                    if os.path.exists(alt_path):
                        config_path = alt_path
                        logger.info(f"✅ Found accounts.yaml at: {config_path}")
                        break
                else:
                    logger.error(f"❌ accounts.yaml not found in any of the expected locations")
                    # List all files in current directory and /app
                    try:
                        cwd_files = os.listdir(os.getcwd())
                        logger.info(f"📁 Files in current directory ({os.getcwd()}): {cwd_files}")
                        # Check if accounts.yaml is in the list but not accessible
                        if 'accounts.yaml' in cwd_files:
                            logger.info("🔍 accounts.yaml exists in current directory, trying direct access")
                            config_path = 'accounts.yaml'
                        else:
                            # Try /app directory
                            app_files = os.listdir('/app')
                            logger.info(f"📁 Files in /app: {app_files}")
                            if 'accounts.yaml' in app_files:
                                logger.info("🔍 accounts.yaml exists in /app directory, trying direct access")
                                config_path = '/app/accounts.yaml'
                            else:
                                raise FileNotFoundError("accounts.yaml not found")
                    except Exception as e:
                        logger.warning(f"Could not list directories: {e}")
                        raise FileNotFoundError("accounts.yaml not found")
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            accounts_list = config_data.get('accounts', [])
            logger.info(f"📋 Found {len(accounts_list)} accounts in accounts.yaml")
            
            for account_data in accounts_list:
                # Only load active accounts
                if not account_data.get('active', False):
                    logger.info(f"⏭️  Skipping inactive: {account_data.get('name', 'Unknown')}")
                    continue
                
                account_id = account_data.get('id')
                if not account_id:
                    logger.warning(f"⚠️  Skipping account without ID")
                    continue
                
                config = AccountConfig(
                    account_id=account_id,
                    account_name=account_data.get('name', f'Account_{account_id[-3:]}'),
                    display_name=account_data.get('display_name', account_data.get('name', 'Unknown')),
                    api_key=api_key or '',  # Empty string if missing (broker calls will fail gracefully)
                    environment=environment,
                    strategy_name=account_data.get('strategy', 'unknown'),
                    risk_settings=account_data.get('risk_settings', {}),
                    instruments=account_data.get('instruments', []),
                    active=account_data.get('active', True),
                    priority=account_data.get('priority', 99)
                )
                
                self.account_configs[account_id] = config
                self.strategy_mappings[account_id] = account_data.get('strategy', 'unknown')
                
                logger.info(f"✅ Configured: {config.display_name} ({account_id[-3:]}) → {config.strategy_name}")
            
            logger.info(f"✅ Successfully loaded {len(self.account_configs)} active accounts from YAML")
            
        except Exception as e:
            logger.error(f"❌ Failed to load accounts.yaml: {e}")
            logger.exception("Full traceback:")
            # NO FALLBACK - if YAML fails, we should know about it
            raise Exception(f"CRITICAL: Cannot load accounts.yaml - system cannot start. Error: {e}")
    
    def _load_from_env_fallback(self):
        """Fallback: load from environment variables (backwards compatible)"""
        api_key = os.getenv('OANDA_API_KEY')
        environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
        
        # Account 1: Primary
        if os.getenv('PRIMARY_ACCOUNT'):
            config = AccountConfig(
                account_id=os.getenv('PRIMARY_ACCOUNT'),
                account_name="PRIMARY",
                display_name="🥇 Gold Scalping",
                api_key=api_key,
                environment=environment,
                strategy_name="gold_scalping",
                risk_settings={
                    'max_risk_per_trade': 0.02,
                    'max_portfolio_risk': 0.75,
                    'max_positions': 3,
                    'daily_trade_limit': 100
                },
                instruments=['XAU_USD'],
                active=True,
                priority=1
            )
            self.account_configs[config.account_id] = config
            self.strategy_mappings[config.account_id] = config.strategy_name
        
        # Account 2: Gold Scalp
        if os.getenv('GOLD_SCALP_ACCOUNT'):
            config = AccountConfig(
                account_id=os.getenv('GOLD_SCALP_ACCOUNT'),
                account_name="GOLD_SCALP",
                display_name="💱 Ultra Strict Fx",
                api_key=api_key,
                environment=environment,
                strategy_name="ultra_strict_forex",
                risk_settings={
                    'max_risk_per_trade': 0.015,
                    'max_portfolio_risk': 0.75,
                    'max_positions': 5,
                    'daily_trade_limit': 50
                },
                instruments=['GBP_USD', 'EUR_USD'],
                active=True,
                priority=2
            )
            self.account_configs[config.account_id] = config
            self.strategy_mappings[config.account_id] = config.strategy_name
        
        # Account 3: Strategy Alpha
        if os.getenv('STRATEGY_ALPHA_ACCOUNT'):
            config = AccountConfig(
                account_id=os.getenv('STRATEGY_ALPHA_ACCOUNT'),
                account_name="STRATEGY_ALPHA",
                display_name="📈 Momentum Trading",
                api_key=api_key,
                environment=environment,
                strategy_name="momentum_trading",
                risk_settings={
                    'max_risk_per_trade': 0.025,
                    'max_portfolio_risk': 0.75,
                    'max_positions': 7,
                    'daily_trade_limit': 100
                },
                instruments=['USD_JPY', 'USD_CAD', 'NZD_USD', 'GBP_USD'],
                active=True,
                priority=3
            )
            self.account_configs[config.account_id] = config
            self.strategy_mappings[config.account_id] = config.strategy_name
        
        logger.info(f"✅ Loaded {len(self.account_configs)} accounts from environment variables")
    
    def _initialize_accounts(self):
        """Initialize broker clients for each account
        
        In paper mode (TRADING_MODE=paper), uses PaperBroker by default unless
        PAPER_ALLOW_OANDA_NETWORK=true is set.
        
        In live mode, requires valid OANDA credentials and dual-confirm flags.
        """
        trading_mode = os.getenv('TRADING_MODE', 'paper').lower()
        allow_network = os.getenv('PAPER_ALLOW_OANDA_NETWORK', 'false').lower() == 'true'
        has_broker_creds = bool(os.getenv('OANDA_API_KEY'))
        
        # Determine broker type
        use_paper_broker = (
            trading_mode == 'paper' and not allow_network
        ) or (
            not has_broker_creds
        )
        
        if use_paper_broker:
            logger.info(f"📄 Using PAPER BROKER for all accounts (no network calls)")
            logger.info(f"   Set PAPER_ALLOW_OANDA_NETWORK=true to enable OANDA calls in paper mode")
        
        # Initialize broker clients
        for account_id, config in self.account_configs.items():
            if use_paper_broker:
                # Use PaperBroker (no network calls)
                try:
                    client = PaperBroker(
                        account_id=account_id,
                        currency=config.instruments[0].split('_')[1] if config.instruments else "USD",
                        initial_balance=10000.0
                    )
                    self.accounts[account_id] = client
                    logger.info(f"📄 Paper broker initialized: {config.display_name} ({account_id[-3:]})")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to initialize paper broker for {account_id}: {e}")
            else:
                # Use real OANDA client (requires credentials)
                if not config.api_key or not account_id:
                    logger.warning(f"⚠️ Skipping broker init for {config.display_name}: missing credentials")
                    continue
                
                try:
                    client = OandaClient(
                        api_key=config.api_key,
                        account_id=account_id,
                        environment=config.environment
                    )
                    
                    # Test connection
                    account_info = client.get_account_info()
                    
                    self.accounts[account_id] = client
                    
                    logger.info(f"✅ Connected: {config.display_name} - Balance: {account_info.balance} {account_info.currency}")
                    
                except Exception as e:
                    # In paper mode, fall back to paper broker on error
                    if trading_mode == 'paper':
                        logger.warning(f"⚠️ OANDA init failed for {account_id}, using paper broker: {e}")
                        try:
                            client = PaperBroker(
                                account_id=account_id,
                                currency=config.instruments[0].split('_')[1] if config.instruments else "USD",
                                initial_balance=10000.0
                            )
                            self.accounts[account_id] = client
                        except Exception as e2:
                            logger.warning(f"⚠️ Failed to initialize paper broker fallback: {e2}")
                    else:
                        # In live mode, log as warning but don't crash
                        logger.warning(f"⚠️ Failed to initialize broker for {account_id}: {e}")
    
    def get_account_client(self, account_id: str):
        """Get broker client for specific account (OandaClient or PaperBroker)"""
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
                'display_name': config.display_name,
                'strategy': config.strategy_name,
                'status': 'active',
                'balance': account_info.balance,
                'currency': account_info.currency,
                'unrealized_pl': account_info.unrealized_pl,
                'realized_pl': account_info.realized_pl,
                'open_trades': account_info.open_trade_count,
                'open_positions': account_info.open_position_count,
                'instruments': config.instruments,
                'risk_settings': config.risk_settings,
                'priority': config.priority
            }
        except Exception as e:
            logger.error(f"❌ Failed to get account status for {account_id}: {e}")
            return {
                'account_id': account_id,
                'status': 'error',
                'error': str(e)
            }


# Global instance
_dynamic_account_manager = None


def get_dynamic_account_manager() -> DynamicAccountManager:
    """Get global dynamic account manager instance"""
    global _dynamic_account_manager
    if _dynamic_account_manager is None:
        _dynamic_account_manager = DynamicAccountManager()
    return _dynamic_account_manager


# Alias for compatibility
def get_account_manager():
    """Get account manager (uses dynamic version)"""
    return get_dynamic_account_manager()

