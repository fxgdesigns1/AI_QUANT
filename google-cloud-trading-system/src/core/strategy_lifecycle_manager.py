#!/usr/bin/env python3
"""
Strategy Lifecycle Manager
Handles loading, stopping, restarting, and hot-reloading strategies
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .yaml_manager import get_yaml_manager, YAMLManager
from .strategy_factory import get_strategy_factory

logger = logging.getLogger(__name__)


class StrategyLifecycleManager:
    """Manage strategy lifecycle operations"""
    
    def __init__(self):
        """Initialize strategy lifecycle manager"""
        self.yaml_mgr = get_yaml_manager()
        self.strategy_factory = get_strategy_factory()
        
        # Track running strategies
        self.active_strategies = {}  # account_id -> strategy_instance
        
        logger.info("✅ Strategy Lifecycle Manager initialized")
    
    def load_strategy(self, account_id: str, strategy_name: str, validate: bool = True) -> Dict[str, Any]:
        """
        Load a strategy on an account
        
        Args:
            account_id: Account to load strategy on
            strategy_name: Strategy to load
            validate: Whether to validate strategy before loading
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Validate strategy if requested
            if validate:
                is_valid = self.yaml_mgr.validate_strategy_instruments(account_id, strategy_name)
                if not is_valid:
                    return {
                        'success': False,
                        'error': 'Strategy validation failed',
                        'account_id': account_id,
                        'strategy_name': strategy_name
                    }
            
            # Get account configuration
            accounts = self.yaml_mgr.get_all_accounts()
            account_config = None
            for acc in accounts:
                if acc['id'] == account_id:
                    account_config = acc
                    break
            
            if not account_config:
                return {
                    'success': False,
                    'error': f'Account not found: {account_id}',
                    'account_id': account_id
                }
            
            # Update strategy in YAML
            success = self.yaml_mgr.update_account_strategy(account_id, strategy_name)
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to update account strategy in YAML',
                    'account_id': account_id
                }
            
            # Try to load strategy instance
            try:
                strategy_instance = self.strategy_factory.get_strategy(
                    strategy_name,
                    account_config=account_config
                )
                self.active_strategies[account_id] = strategy_instance
                
                logger.info(f"✅ Strategy '{strategy_name}' loaded on account {account_id}")
                
                return {
                    'success': True,
                    'message': f'Strategy {strategy_name} loaded successfully',
                    'account_id': account_id,
                    'strategy_name': strategy_name,
                    'timestamp': datetime.now().isoformat()
                }
            
            except Exception as e:
                logger.error(f"⚠️ Strategy loaded in YAML but failed to instantiate: {e}")
                return {
                    'success': True,  # YAML update succeeded
                    'message': f'Strategy updated in config, will load on next scan',
                    'account_id': account_id,
                    'strategy_name': strategy_name,
                    'warning': f'Strategy instantiation failed: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to load strategy: {e}")
            return {
                'success': False,
                'error': str(e),
                'account_id': account_id,
                'strategy_name': strategy_name
            }
    
    def stop_strategy(self, account_id: str) -> Dict[str, Any]:
        """
        Stop a strategy on an account (set active: false)
        
        Args:
            account_id: Account to stop strategy on
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Deactivate account in YAML
            success = self.yaml_mgr.toggle_account(account_id, active=False)
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to toggle account in YAML',
                    'account_id': account_id
                }
            
            # Remove from active strategies
            if account_id in self.active_strategies:
                del self.active_strategies[account_id]
            
            logger.info(f"🛑 Strategy stopped on account {account_id}")
            
            return {
                'success': True,
                'message': f'Strategy stopped successfully on account {account_id}',
                'account_id': account_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stop strategy: {e}")
            return {
                'success': False,
                'error': str(e),
                'account_id': account_id
            }
    
    def restart_strategy(self, account_id: str) -> Dict[str, Any]:
        """
        Restart a strategy on an account (reactivate)
        
        Args:
            account_id: Account to restart strategy on
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Reactivate account in YAML
            success = self.yaml_mgr.toggle_account(account_id, active=True)
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to reactivate account in YAML',
                    'account_id': account_id
                }
            
            # Get account info
            accounts = self.yaml_mgr.get_all_accounts()
            account_config = None
            for acc in accounts:
                if acc['id'] == account_id:
                    account_config = acc
                    break
            
            if account_config:
                strategy_name = account_config.get('strategy')
                if strategy_name:
                    try:
                        strategy_instance = self.strategy_factory.get_strategy(
                            strategy_name,
                            account_config=account_config
                        )
                        self.active_strategies[account_id] = strategy_instance
                    except Exception as e:
                        logger.warning(f"⚠️ Strategy instantiation failed during restart: {e}")
            
            logger.info(f"🔄 Strategy restarted on account {account_id}")
            
            return {
                'success': True,
                'message': f'Strategy restarted successfully on account {account_id}',
                'account_id': account_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to restart strategy: {e}")
            return {
                'success': False,
                'error': str(e),
                'account_id': account_id
            }
    
    def reload_strategy(self, account_id: str, strategy_name: str = None) -> Dict[str, Any]:
        """
        Hot-reload a strategy configuration without stopping
        
        Args:
            account_id: Account to reload strategy for
            strategy_name: Optional strategy name (uses account's current strategy if not provided)
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Get account info
            accounts = self.yaml_mgr.get_all_accounts()
            account_config = None
            for acc in accounts:
                if acc['id'] == account_id:
                    account_config = acc
                    break
            
            if not account_config:
                return {
                    'success': False,
                    'error': f'Account not found: {account_id}',
                    'account_id': account_id
                }
            
            # Use provided strategy or account's current strategy
            if not strategy_name:
                strategy_name = account_config.get('strategy')
            
            if not strategy_name:
                return {
                    'success': False,
                    'error': 'No strategy specified and account has no strategy',
                    'account_id': account_id
                }
            
            # Reload strategy instance
            try:
                strategy_instance = self.strategy_factory.get_strategy(
                    strategy_name,
                    account_config=account_config
                )
                self.active_strategies[account_id] = strategy_instance
                
                logger.info(f"🔄 Strategy {strategy_name} reloaded on account {account_id}")
                
                return {
                    'success': True,
                    'message': f'Strategy {strategy_name} reloaded successfully',
                    'account_id': account_id,
                    'strategy_name': strategy_name,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Strategy reload failed: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'account_id': account_id,
                    'strategy_name': strategy_name
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to reload strategy: {e}")
            return {
                'success': False,
                'error': str(e),
                'account_id': account_id
            }
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """
        Get list of all available strategies
        
        Returns:
            List of strategy information dictionaries
        """
        try:
            strategies = self.strategy_factory.list_all_strategies()
            
            strategy_list = []
            for strategy_name in strategies:
                strategy_list.append({
                    'name': strategy_name,
                    'display_name': strategy_name.replace('_', ' ').title(),
                    'description': self._get_strategy_description(strategy_name),
                    'best_for': self._get_strategy_best_for(strategy_name)
                })
            
            return strategy_list
            
        except Exception as e:
            logger.error(f"❌ Failed to list strategies: {e}")
            return []
    
    def get_active_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of active strategies per account
        
        Returns:
            Dictionary mapping account_id to strategy info
        """
        try:
            accounts = self.yaml_mgr.get_all_accounts()
            active = {}
            
            for account in accounts:
                if account.get('active', False):
                    active[account['id']] = {
                        'account_id': account['id'],
                        'account_name': account.get('name', 'Unknown'),
                        'strategy': account.get('strategy'),
                        'instruments': account.get('instruments', []),
                        'active': True
                    }
            
            return active
            
        except Exception as e:
            logger.error(f"❌ Failed to get active strategies: {e}")
            return {}
    
    def _get_strategy_description(self, strategy_name: str) -> str:
        """Get human-readable description for strategy"""
        descriptions = {
            'momentum_trading': 'Follows strong price trends with moving averages and momentum indicators',
            'gold_scalping': 'High-frequency scalping for Gold (XAU/USD) with tight spreads',
            'breakout': 'Trades breakouts from consolidation zones',
            'scalping': 'Quick in-and-out trades on short timeframes',
            'swing_trading': 'Medium-term trades holding for days to weeks',
            'mean_reversion': 'Fades extreme price movements expecting reversion to average',
            'trend_following': 'Follows established trends with trailing stops',
            'rsi_divergence': 'Uses RSI divergence patterns for entries',
            'fibonacci': 'Trades from Fibonacci retracement levels',
            'ultra_strict_forex': 'Very selective forex entries with high confidence threshold'
        }
        return descriptions.get(strategy_name, 'Trading strategy')
    
    def _get_strategy_best_for(self, strategy_name: str) -> str:
        """Get instruments best suited for strategy"""
        recommendations = {
            'momentum_trading': 'EUR/USD, GBP/USD, USD/JPY',
            'gold_scalping': 'XAU/USD',
            'breakout': 'EUR/USD, GBP/USD, USD/JPY',
            'scalping': 'Major pairs with tight spreads',
            'swing_trading': 'EUR/USD, GBP/USD, XAU/USD',
            'mean_reversion': 'Range-bound markets',
            'trend_following': 'Strong trending pairs',
            'rsi_divergence': 'EUR/USD, GBP/USD',
            'fibonacci': 'All major pairs',
            'ultra_strict_forex': 'Major forex pairs'
        }
        return recommendations.get(strategy_name, 'Major instruments')


# Global instance
_strategy_lifecycle_manager = None


def get_strategy_lifecycle_manager() -> StrategyLifecycleManager:
    """Get global strategy lifecycle manager instance"""
    global _strategy_lifecycle_manager
    if _strategy_lifecycle_manager is None:
        _strategy_lifecycle_manager = StrategyLifecycleManager()
    return _strategy_lifecycle_manager

