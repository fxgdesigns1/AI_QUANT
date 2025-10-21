#!/usr/bin/env python3
"""
Enhanced Strategy Manager API
Handles strategy switching, uploads, behavior controls, and configuration management
"""

import os
import logging
import copy
import json
import ast
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PendingChange:
    """Represents a pending configuration change"""
    change_type: str  # 'strategy_switch', 'toggle_account', 'edit_settings', 'upload_strategy', 'behavior_change'
    account_id: str
    old_value: Any
    new_value: Any
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BehaviorMode:
    """Strategy behavior mode configuration"""
    mode: str  # 'aggressive', 'normal', 'relaxed', 'paused', 'auto'
    risk_multiplier: float
    trade_frequency: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class UploadedStrategy:
    """Uploaded strategy metadata"""
    strategy_id: str
    filename: str
    code_hash: str
    upload_time: str
    backtest_results: Optional[Dict[str, Any]]
    validation_status: str
    performance_metrics: Dict[str, Any]


class StrategyManager:
    """
    Manages strategy configuration and switching operations
    
    Features:
    - Load/save configurations from accounts.yaml
    - Stage changes for preview before applying
    - Validate changes before applying
    - Track pending changes
    - Create automatic backups
    """
    
    def __init__(self):
        """Initialize strategy manager"""
        self.initialized = False
        self.read_only_mode = False
        self.init_error = None
        
        try:
            from ..core.yaml_manager import get_yaml_manager
            self.yaml_mgr = get_yaml_manager()
            
            # Check if YAML manager is in read-only mode
            if hasattr(self.yaml_mgr, 'read_only_mode'):
                self.read_only_mode = self.yaml_mgr.read_only_mode
            
            # Pending changes tracking
            self.pending_changes: Dict[str, PendingChange] = {}
            self.staged_config: Optional[Dict[str, Any]] = None
            
            # Behavior modes configuration
            self.behavior_modes = self._initialize_behavior_modes()
            
            self.initialized = True
            logger.info(f"✅ Enhanced Strategy Manager initialized (read-only: {self.read_only_mode})")
            
        except Exception as e:
            self.init_error = str(e)
            logger.error(f"❌ Strategy Manager initialization failed: {e}")
            logger.exception("Full traceback:")
            # Set defaults for graceful degradation
            self.pending_changes = {}
            self.staged_config = None
            self.behavior_modes = {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get strategy manager health status"""
        return {
            'initialized': self.initialized,
            'read_only_mode': self.read_only_mode,
            'init_error': self.init_error,
            'yaml_writable': hasattr(self.yaml_mgr, 'is_writable') and self.yaml_mgr.is_writable() if hasattr(self, 'yaml_mgr') else False
        }
    
    def get_current_config(self) -> Dict[str, Any]:
        """
        Get current configuration
        
        Returns:
            Dict with accounts, strategies, and global settings
        """
        try:
            if not self.initialized:
                return {
                    'success': False,
                    'error': f'Strategy manager not initialized: {self.init_error}',
                    'accounts': [],
                    'strategies': [],
                    'global_settings': {},
                    'health_status': self.get_health_status()
                }
            
            config = self.yaml_mgr.read_config()
            
            # Enrich with additional metadata
            accounts = config.get('accounts', [])
            strategies = config.get('strategies', {})
            
            # Build strategy list for UI
            strategy_list = []
            for strategy_id, strategy_info in strategies.items():
                strategy_list.append({
                    'id': strategy_id,
                    'name': strategy_id.replace('_', ' ').title(),
                    'description': strategy_info.get('description', ''),
                    'best_for': strategy_info.get('best_for', ''),
                    'timeframe': strategy_info.get('timeframe', '')
                })
            
            return {
                'accounts': accounts,
                'strategies': strategy_list,
                'available_strategy_ids': list(strategies.keys()),
                'global_settings': config.get('global_settings', {}),
                'pending_changes_count': len(self.pending_changes)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get current config: {e}")
            return {
                'accounts': [],
                'strategies': [],
                'available_strategy_ids': [],
                'global_settings': {},
                'pending_changes_count': 0,
                'error': str(e)
            }
    
    def stage_strategy_switch(self, account_id: str, new_strategy: str) -> Dict[str, Any]:
        """
        Stage a strategy switch (doesn't apply immediately)
        
        Args:
            account_id: Account to switch strategy for
            new_strategy: New strategy ID
            
        Returns:
            Dict with success status and details
        """
        try:
            # Get current config
            config = self.yaml_mgr.read_config()
            accounts = config.get('accounts', [])
            strategies = config.get('strategies', {})
            
            # Find account
            account = None
            account_index = None
            for i, acc in enumerate(accounts):
                if acc['id'] == account_id:
                    account = acc
                    account_index = i
                    break
            
            if not account:
                return {
                    'success': False,
                    'error': f'Account not found: {account_id}'
                }
            
            # Validate new strategy exists
            if new_strategy not in strategies:
                return {
                    'success': False,
                    'error': f'Strategy not found: {new_strategy}'
                }
            
            # Get old strategy
            old_strategy = account.get('strategy')
            
            if old_strategy == new_strategy:
                return {
                    'success': False,
                    'error': 'Account already using this strategy'
                }
            
            # Stage change
            change_id = f"switch_{account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.pending_changes[change_id] = PendingChange(
                change_type='strategy_switch',
                account_id=account_id,
                old_value=old_strategy,
                new_value=new_strategy,
                timestamp=datetime.now().isoformat()
            )
            
            # Update staged config
            if not self.staged_config:
                self.staged_config = copy.deepcopy(config)
            
            self.staged_config['accounts'][account_index]['strategy'] = new_strategy
            
            logger.info(f"📝 Staged strategy switch for {account_id}: {old_strategy} → {new_strategy}")
            
            return {
                'success': True,
                'change_id': change_id,
                'account_id': account_id,
                'account_name': account.get('display_name', account.get('name')),
                'old_strategy': old_strategy,
                'new_strategy': new_strategy,
                'pending_changes_count': len(self.pending_changes)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stage strategy switch: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stage_account_toggle(self, account_id: str, active: bool) -> Dict[str, Any]:
        """
        Stage account enable/disable (doesn't apply immediately)
        
        Args:
            account_id: Account to toggle
            active: True to enable, False to disable
            
        Returns:
            Dict with success status and details
        """
        try:
            # Get current config
            config = self.yaml_mgr.read_config()
            accounts = config.get('accounts', [])
            
            # Find account
            account = None
            account_index = None
            for i, acc in enumerate(accounts):
                if acc['id'] == account_id:
                    account = acc
                    account_index = i
                    break
            
            if not account:
                return {
                    'success': False,
                    'error': f'Account not found: {account_id}'
                }
            
            # Get current status
            old_active = account.get('active', True)
            
            if old_active == active:
                return {
                    'success': False,
                    'error': f'Account already {"active" if active else "inactive"}'
                }
            
            # Stage change
            change_id = f"toggle_{account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.pending_changes[change_id] = PendingChange(
                change_type='toggle_account',
                account_id=account_id,
                old_value=old_active,
                new_value=active,
                timestamp=datetime.now().isoformat()
            )
            
            # Update staged config
            if not self.staged_config:
                self.staged_config = copy.deepcopy(config)
            
            self.staged_config['accounts'][account_index]['active'] = active
            
            action = "enabled" if active else "disabled"
            logger.info(f"📝 Staged account toggle for {account_id}: {action}")
            
            return {
                'success': True,
                'change_id': change_id,
                'account_id': account_id,
                'account_name': account.get('display_name', account.get('name')),
                'old_active': old_active,
                'new_active': active,
                'pending_changes_count': len(self.pending_changes)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stage account toggle: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_pending_changes(self) -> Dict[str, Any]:
        """
        Get all pending changes for preview
        
        Returns:
            Dict with pending changes details
        """
        try:
            changes_list = []
            
            for change_id, change in self.pending_changes.items():
                change_dict = asdict(change)
                change_dict['change_id'] = change_id
                changes_list.append(change_dict)
            
            return {
                'success': True,
                'pending_changes': changes_list,
                'count': len(changes_list),
                'has_staged_config': self.staged_config is not None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get pending changes: {e}")
            return {
                'success': False,
                'error': str(e),
                'pending_changes': [],
                'count': 0
            }
    
    def clear_pending_changes(self) -> Dict[str, Any]:
        """
        Clear all pending changes (cancel)
        
        Returns:
            Dict with success status
        """
        try:
            count = len(self.pending_changes)
            self.pending_changes.clear()
            self.staged_config = None
            
            logger.info(f"🗑️ Cleared {count} pending changes")
            
            return {
                'success': True,
                'cleared_count': count
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to clear pending changes: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_staged_config(self) -> Dict[str, Any]:
        """
        Validate staged configuration before applying
        
        Returns:
            Dict with validation results
        """
        try:
            if not self.staged_config:
                return {
                    'valid': False,
                    'error': 'No staged configuration'
                }
            
            # Basic structure validation
            if 'accounts' not in self.staged_config:
                return {
                    'valid': False,
                    'error': 'Missing accounts section'
                }
            
            if not isinstance(self.staged_config['accounts'], list):
                return {
                    'valid': False,
                    'error': 'Accounts must be a list'
                }
            
            # Validate each account
            strategies = self.staged_config.get('strategies', {})
            
            for account in self.staged_config['accounts']:
                # Check required fields
                required_fields = ['id', 'name', 'strategy', 'instruments']
                for field in required_fields:
                    if field not in account:
                        return {
                            'valid': False,
                            'error': f'Account {account.get("id", "unknown")} missing field: {field}'
                        }
                
                # Check strategy exists
                strategy = account.get('strategy')
                if strategy not in strategies:
                    return {
                        'valid': False,
                        'error': f'Account {account["id"]} uses unknown strategy: {strategy}'
                    }
            
            logger.info("✅ Staged configuration validated successfully")
            
            return {
                'valid': True,
                'accounts_count': len(self.staged_config['accounts']),
                'changes_count': len(self.pending_changes)
            }
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def get_staged_config(self) -> Optional[Dict[str, Any]]:
        """Get the staged configuration"""
        return self.staged_config
    
    def has_pending_changes(self) -> bool:
        """Check if there are pending changes"""
        return len(self.pending_changes) > 0
    
    def _initialize_behavior_modes(self) -> Dict[str, BehaviorMode]:
        """Initialize behavior mode configurations"""
        return {
            'aggressive': BehaviorMode(
                mode='aggressive',
                risk_multiplier=1.5,
                trade_frequency='high',
                description='High risk, high frequency trading for maximum returns',
                parameters={
                    'max_risk_per_trade': 0.02,
                    'daily_trade_limit': 200,
                    'signal_threshold': 0.6,
                    'position_hold_time': 0.5  # hours
                }
            ),
            'normal': BehaviorMode(
                mode='normal',
                risk_multiplier=1.0,
                trade_frequency='medium',
                description='Balanced risk/reward with moderate frequency',
                parameters={
                    'max_risk_per_trade': 0.01,
                    'daily_trade_limit': 100,
                    'signal_threshold': 0.7,
                    'position_hold_time': 1.0  # hours
                }
            ),
            'relaxed': BehaviorMode(
                mode='relaxed',
                risk_multiplier=0.7,
                trade_frequency='low',
                description='Conservative approach with lower risk and frequency',
                parameters={
                    'max_risk_per_trade': 0.005,
                    'daily_trade_limit': 50,
                    'signal_threshold': 0.8,
                    'position_hold_time': 2.0  # hours
                }
            ),
            'paused': BehaviorMode(
                mode='paused',
                risk_multiplier=0.0,
                trade_frequency='none',
                description='Strategy paused - no new trades generated',
                parameters={
                    'max_risk_per_trade': 0.0,
                    'daily_trade_limit': 0,
                    'signal_threshold': 1.0,
                    'position_hold_time': 999.0  # hours
                }
            ),
            'auto': BehaviorMode(
                mode='auto',
                risk_multiplier=1.0,
                trade_frequency='adaptive',
                description='Automatically adjusts based on market conditions',
                parameters={
                    'max_risk_per_trade': 0.01,
                    'daily_trade_limit': 100,
                    'signal_threshold': 0.7,
                    'position_hold_time': 1.0,  # hours
                    'adaptive_risk': True,
                    'market_regime_detection': True
                }
            )
        }
    
    def get_behavior_modes(self) -> Dict[str, Any]:
        """Get available behavior modes"""
        return {
            mode_id: {
                'mode': mode.mode,
                'risk_multiplier': mode.risk_multiplier,
                'trade_frequency': mode.trade_frequency,
                'description': mode.description,
                'parameters': mode.parameters
            }
            for mode_id, mode in self.behavior_modes.items()
        }
    
    def stage_behavior_change(self, account_id: str, new_behavior: str) -> Dict[str, Any]:
        """Stage a behavior mode change"""
        try:
            if not self.initialized:
                return {
                    'success': False,
                    'error': f'Strategy manager not initialized: {self.init_error}'
                }
            
            if self.read_only_mode:
                return {
                    'success': False,
                    'error': 'Cannot change behavior modes: system is in read-only mode. Please update accounts.yaml locally and redeploy.',
                    'read_only_mode': True
                }
            
            if new_behavior not in self.behavior_modes:
                return {
                    'success': False,
                    'error': f'Unknown behavior mode: {new_behavior}'
                }
            
            # Get current config
            config = self.yaml_mgr.read_config()
            accounts = config.get('accounts', [])
            
            # Find account
            account = None
            account_index = None
            for i, acc in enumerate(accounts):
                if acc['id'] == account_id:
                    account = acc
                    account_index = i
                    break
            
            if not account:
                return {
                    'success': False,
                    'error': f'Account not found: {account_id}'
                }
            
            # Get current behavior mode
            current_behavior = account.get('behavior_mode', 'normal')
            
            if current_behavior == new_behavior:
                return {
                    'success': False,
                    'error': 'Account already using this behavior mode'
                }
            
            # Stage change
            change_id = f"behavior_{account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            behavior_mode = self.behavior_modes[new_behavior]
            
            self.pending_changes[change_id] = PendingChange(
                change_type='behavior_change',
                account_id=account_id,
                old_value=current_behavior,
                new_value=new_behavior,
                timestamp=datetime.now().isoformat(),
                metadata={
                    'behavior_mode': asdict(behavior_mode),
                    'updated_parameters': behavior_mode.parameters
                }
            )
            
            # Update staged config
            if not self.staged_config:
                self.staged_config = copy.deepcopy(config)
            
            self.staged_config['accounts'][account_index]['behavior_mode'] = new_behavior
            
            # Update risk settings based on behavior mode
            if 'risk_settings' not in self.staged_config['accounts'][account_index]:
                self.staged_config['accounts'][account_index]['risk_settings'] = {}
            
            behavior_params = behavior_mode.parameters
            self.staged_config['accounts'][account_index]['risk_settings'].update({
                'max_risk_per_trade': behavior_params.get('max_risk_per_trade', 0.01),
                'daily_trade_limit': behavior_params.get('daily_trade_limit', 100)
            })
            
            logger.info(f"📝 Staged behavior change for {account_id}: {current_behavior} → {new_behavior}")
            
            return {
                'success': True,
                'change_id': change_id,
                'account_id': account_id,
                'account_name': account.get('display_name', account.get('name')),
                'old_behavior': current_behavior,
                'new_behavior': new_behavior,
                'behavior_description': behavior_mode.description,
                'updated_parameters': behavior_mode.parameters,
                'pending_changes_count': len(self.pending_changes)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stage behavior change: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_strategy(self, strategy_file, backtest_results: Optional[Dict] = None) -> Dict[str, Any]:
        """Upload and validate a new strategy - PLACEHOLDER"""
        return {
            'success': False,
            'error': 'Strategy upload feature temporarily disabled for stability'
        }
    
    def _validate_strategy_code(self, code: str) -> Dict[str, Any]:
        """Validate uploaded strategy code"""
        try:
            # Parse Python code
            tree = ast.parse(code)
            
            # Check for required components
            required_methods = ['analyze_market', '__init__']
            class_name = None
            found_methods = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            found_methods.append(item.name)
            
            if not class_name:
                return {
                    'valid': False,
                    'error': 'No class definition found'
                }
            
            missing_methods = [method for method in required_methods if method not in found_methods]
            if missing_methods:
                return {
                    'valid': False,
                    'error': f'Missing required methods: {missing_methods}'
                }
            
            # Check for strategy function
            has_getter_function = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('get_'):
                    has_getter_function = True
                    break
            
            if not has_getter_function:
                return {
                    'valid': False,
                    'error': 'No getter function found (should be get_strategy_name())'
                }
            
            return {
                'valid': True,
                'class_name': class_name,
                'found_methods': found_methods,
                'has_getter_function': has_getter_function
            }
            
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f'Syntax error: {str(e)}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }
    
    def register_uploaded_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """Register uploaded strategy in accounts.yaml"""
        try:
            if strategy_id not in self.uploaded_strategies:
                return {
                    'success': False,
                    'error': f'Strategy not found: {strategy_id}'
                }
            
            uploaded_strategy = self.uploaded_strategies[strategy_id]
            
            # Read current config
            config = self.yaml_mgr.read_config()
            
            # Add to strategies section
            if 'strategies' not in config:
                config['strategies'] = {}
            
            config['strategies'][strategy_id] = {
                'class_name': uploaded_strategy.strategy_id.replace('-', '_').title() + 'Strategy',
                'module': f'src.strategies.uploaded.{strategy_id}',
                'function': f'get_{strategy_id.replace("-", "_")}_strategy',
                'description': f'Uploaded strategy from {uploaded_strategy.filename}',
                'best_for': 'Multiple instruments',
                'timeframe': 'Multiple',
                'uploaded': True,
                'upload_time': uploaded_strategy.upload_time,
                'performance_metrics': uploaded_strategy.performance_metrics
            }
            
            # Save config
            success = self.yaml_mgr.write_config(config, backup=True)
            
            if success:
                logger.info(f"✅ Registered uploaded strategy: {strategy_id}")
                return {
                    'success': True,
                    'strategy_id': strategy_id,
                    'message': 'Strategy registered successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save configuration'
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to register strategy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_uploaded_strategies(self) -> Dict[str, Any]:
        """Get list of uploaded strategies - PLACEHOLDER"""
        return {'uploaded_strategies': {}}


# Global instance
_strategy_manager = None


def get_strategy_manager() -> StrategyManager:
    """Get global strategy manager instance"""
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyManager()
    return _strategy_manager

