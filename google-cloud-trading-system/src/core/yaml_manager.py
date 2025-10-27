#!/usr/bin/env python3
"""
YAML Manager - Safe Read/Write Operations
Handles all YAML file updates with validation and backup
"""

import os
import yaml
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class YAMLManager:
    """Safe YAML file management with backup and validation"""
    
    def __init__(self, yaml_file: str = "accounts.yaml"):
        """Initialize YAML manager"""
        self.yaml_file = yaml_file
        self.read_only_mode = False
        self.yaml_path = self._find_yaml_file()
        
        # Check if filesystem is writable
        self._check_filesystem_writability()
        
        # Use /tmp for backups on App Engine (read-only filesystem)
        try:
            if not self.read_only_mode:
                self.backup_dir = Path(os.path.dirname(self.yaml_path or '.')) / "config_backups"
                self.backup_dir.mkdir(exist_ok=True)
            else:
                # Fallback to /tmp for App Engine
                self.backup_dir = Path("/tmp") / "config_backups"
                self.backup_dir.mkdir(exist_ok=True)
                logger.warning(f"⚠️ Using /tmp for backups (read-only filesystem)")
        except OSError as e:
            logger.error(f"❌ Failed to create backup directory: {e}")
            self.read_only_mode = True
            self.backup_dir = None
        
        # Cache config in memory for read-only mode
        self._cached_config = None
        
        # Strategy config path (separate file)
        self.strategy_config_path = self._find_strategy_config_file()
        
        logger.info(f"✅ YAML Manager initialized: {self.yaml_path} (read-only: {self.read_only_mode})")
    
    def _check_filesystem_writability(self):
        """Check if filesystem is writable"""
        try:
            # Try to create a test file in the current directory
            test_file = Path("test_write_permission.tmp")
            test_file.touch()
            test_file.unlink()  # Clean up
            self.read_only_mode = False
        except (OSError, PermissionError):
            self.read_only_mode = True
            logger.warning("⚠️ Filesystem is read-only - YAML operations will be limited")
    
    def is_writable(self) -> bool:
        """Check if filesystem is writable"""
        return not self.read_only_mode
    
    def _find_yaml_file(self) -> Optional[Path]:
        """Find accounts.yaml file"""
        possible_paths = [
            Path(self.yaml_file),
            Path(__file__).parent.parent.parent / self.yaml_file,
            Path.cwd() / self.yaml_file,
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Create default if not found
        default_path = Path(__file__).parent.parent.parent / self.yaml_file
        logger.warning(f"⚠️ YAML file not found, will create at: {default_path}")
        return default_path
    
    def read_config(self) -> Dict[str, Any]:
        """Read YAML configuration"""
        try:
            # Return cached config if available in read-only mode
            if self.read_only_mode and self._cached_config:
                return self._cached_config
            
            if not self.yaml_path or not self.yaml_path.exists():
                logger.warning("⚠️ YAML file doesn't exist yet")
                default_config = {'accounts': [], 'strategies': {}, 'global_settings': {}}
                if self.read_only_mode:
                    self._cached_config = default_config
                return default_config
            
            with open(self.yaml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            result = config or {'accounts': [], 'strategies': {}, 'global_settings': {}}
            
            # Cache in read-only mode
            if self.read_only_mode:
                self._cached_config = result
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to read YAML: {e}")
            default_config = {'accounts': [], 'strategies': {}, 'global_settings': {}}
            if self.read_only_mode:
                self._cached_config = default_config
            return default_config
    
    def write_config(self, config: Dict[str, Any], backup: bool = True) -> bool:
        """
        Write YAML configuration with backup
        
        Args:
            config: Configuration dictionary
            backup: Create backup before writing
        
        Returns:
            bool: Success status
        """
        try:
            # Check if filesystem is writable
            if self.read_only_mode:
                logger.error("❌ Cannot write config: filesystem is read-only")
                return False
            
            # Validate config structure
            if not self._validate_config(config):
                raise ValueError("Invalid configuration structure")
            
            # Create backup if file exists
            if backup and self.yaml_path.exists():
                self._create_backup()
            
            # Write to temporary file first
            temp_path = self.yaml_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
            
            # Verify written file can be read
            with open(temp_path, 'r') as f:
                verification = yaml.safe_load(f)
            
            if not verification:
                raise ValueError("Written YAML file is invalid")
            
            # Move temp to actual
            shutil.move(str(temp_path), str(self.yaml_path))
            
            logger.info(f"✅ YAML configuration written successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to write YAML: {e}")
            # Clean up temp file
            temp_path = self.yaml_path.with_suffix('.tmp')
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def _create_backup(self):
        """Create timestamped backup of YAML file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"accounts_backup_{timestamp}.yaml"
            
            shutil.copy2(self.yaml_path, backup_file)
            
            logger.info(f"💾 Backup created: {backup_file.name}")
            
            # Keep only last 10 backups
            backups = sorted(self.backup_dir.glob('accounts_backup_*.yaml'))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
                    logger.info(f"🗑️ Removed old backup: {old_backup.name}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Backup creation failed: {e}")
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure"""
        try:
            # Check required keys
            if 'accounts' not in config:
                logger.error("❌ Missing 'accounts' key")
                return False
            
            if not isinstance(config['accounts'], list):
                logger.error("❌ 'accounts' must be a list")
                return False
            
            # Validate each account
            for account in config['accounts']:
                if not isinstance(account, dict):
                    logger.error("❌ Account must be a dictionary")
                    return False
                
                required_fields = ['id', 'name', 'strategy', 'instruments']
                for field in required_fields:
                    if field not in account:
                        logger.error(f"❌ Account missing required field: {field}")
                        return False
            
            logger.info("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            return False
    
    def add_account(self, account_data: Dict[str, Any]) -> bool:
        """Add new account to YAML"""
        try:
            config = self.read_config()
            
            # Check if account ID already exists
            existing_ids = [acc['id'] for acc in config['accounts']]
            if account_data['id'] in existing_ids:
                logger.error(f"❌ Account ID already exists: {account_data['id']}")
                return False
            
            # Add account
            config['accounts'].append(account_data)
            
            # Write updated config
            return self.write_config(config)
            
        except Exception as e:
            logger.error(f"❌ Failed to add account: {e}")
            return False
    
    def edit_account(self, account_id: str, updates: Dict[str, Any]) -> bool:
        """Edit existing account in YAML"""
        try:
            config = self.read_config()
            
            # Find account
            account_index = None
            for i, acc in enumerate(config['accounts']):
                if acc['id'] == account_id:
                    account_index = i
                    break
            
            if account_index is None:
                logger.error(f"❌ Account not found: {account_id}")
                return False
            
            # Update account (merge updates)
            for key, value in updates.items():
                if key == 'risk_settings':
                    # Merge risk settings
                    if 'risk_settings' not in config['accounts'][account_index]:
                        config['accounts'][account_index]['risk_settings'] = {}
                    config['accounts'][account_index]['risk_settings'].update(value)
                else:
                    config['accounts'][account_index][key] = value
            
            # Write updated config
            return self.write_config(config)
            
        except Exception as e:
            logger.error(f"❌ Failed to edit account: {e}")
            return False
    
    def delete_account(self, account_id: str) -> bool:
        """Delete account from YAML"""
        try:
            config = self.read_config()
            
            # Filter out account
            original_count = len(config['accounts'])
            config['accounts'] = [acc for acc in config['accounts'] if acc['id'] != account_id]
            
            if len(config['accounts']) == original_count:
                logger.error(f"❌ Account not found: {account_id}")
                return False
            
            # Write updated config
            return self.write_config(config)
            
        except Exception as e:
            logger.error(f"❌ Failed to delete account: {e}")
            return False
    
    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts from YAML"""
        config = self.read_config()
        return config.get('accounts', [])
    
    def get_all_strategies(self) -> Dict[str, Any]:
        """Get all strategies from YAML"""
        config = self.read_config()
        return config.get('strategies', {})

    def _find_strategy_config_file(self) -> Optional[Path]:
        """Find strategy_config.yaml file"""
        possible_paths = [
            Path("strategy_config.yaml"),
            Path(__file__).parent.parent.parent / "strategy_config.yaml",
            Path.cwd() / "strategy_config.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def read_strategy_config(self) -> Dict[str, Any]:
        """Read strategy configuration from strategy_config.yaml"""
        try:
            if not self.strategy_config_path or not self.strategy_config_path.exists():
                logger.warning("⚠️ strategy_config.yaml not found")
                return {}
            
            with open(self.strategy_config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            return config or {}
            
        except Exception as e:
            logger.error(f"❌ Failed to read strategy config: {e}")
            return {}
    
    def write_strategy_config(self, config: Dict[str, Any], backup: bool = True) -> bool:
        """Write strategy configuration with backup"""
        try:
            if self.read_only_mode:
                logger.error("❌ Cannot write strategy config: filesystem is read-only")
                return False
            
            if not self.strategy_config_path:
                logger.error("❌ strategy_config.yaml path not found")
                return False
            
            # Create backup
            if backup and self.strategy_config_path.exists():
                self._create_strategy_config_backup()
            
            # Write to temporary file first
            temp_path = self.strategy_config_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
            
            # Verify written file
            with open(temp_path, 'r') as f:
                verification = yaml.safe_load(f)
            
            if not verification:
                raise ValueError("Written strategy config is invalid")
            
            # Move temp to actual
            shutil.move(str(temp_path), str(self.strategy_config_path))
            
            logger.info("✅ Strategy configuration written successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to write strategy config: {e}")
            temp_path = self.strategy_config_path.with_suffix('.tmp')
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def _create_strategy_config_backup(self):
        """Create timestamped backup of strategy_config.yaml"""
        try:
            if not self.backup_dir:
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"strategy_config_backup_{timestamp}.yaml"
            
            shutil.copy2(self.strategy_config_path, backup_file)
            logger.info(f"💾 Strategy config backup created: {backup_file.name}")
            
        except Exception as e:
            logger.warning(f"⚠️ Strategy config backup creation failed: {e}")
    
    def update_strategy_params(self, strategy_name: str, param_updates: Dict[str, Any]) -> bool:
        """Update specific parameters for a strategy"""
        try:
            config = self.read_strategy_config()
            
            if strategy_name not in config:
                logger.error(f"❌ Strategy not found: {strategy_name}")
                return False
            
            # Deep merge the updates
            strategy_config = config[strategy_name]
            self._deep_update(strategy_config, param_updates)
            
            # Write updated config
            return self.write_strategy_config(config)
            
        except Exception as e:
            logger.error(f"❌ Failed to update strategy params: {e}")
            return False
    
    def _deep_update(self, base_dict: Dict, updates: Dict):
        """Deep merge two dictionaries"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def enable_strategy(self, strategy_name: str) -> bool:
        """Enable a strategy"""
        return self.update_strategy_params(strategy_name, {'enabled': True})
    
    def disable_strategy(self, strategy_name: str) -> bool:
        """Disable a strategy"""
        return self.update_strategy_params(strategy_name, {'enabled': False})
    
    def switch_account_strategy(self, account_id: str, new_strategy_name: str) -> bool:
        """Switch an account's strategy (updates accounts.yaml)"""
        try:
            # Read accounts config
            config = self.read_config()
            
            # Find account
            account_found = False
            for account in config['accounts']:
                if account['id'] == account_id:
                    old_strategy = account.get('strategy')
                    account['strategy'] = new_strategy_name
                    account_found = True
                    logger.info(f"🔄 Switched account {account_id} from {old_strategy} to {new_strategy_name}")
                    break
            
            if not account_found:
                logger.error(f"❌ Account not found: {account_id}")
                return False
            
            # Write updated config
            return self.write_config(config)
            
        except Exception as e:
            logger.error(f"❌ Failed to switch account strategy: {e}")
            return False


# Global instance
_yaml_manager = None


def get_yaml_manager() -> YAMLManager:
    """Get global YAML manager instance"""
    global _yaml_manager
    if _yaml_manager is None:
        _yaml_manager = YAMLManager()
    return _yaml_manager


