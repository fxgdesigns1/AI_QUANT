#!/usr/bin/env python3
"""
Strategy Version Manager - Track Strategy Configuration Changes
Automatically detects and versions strategy parameter changes
"""

import os
import logging
import hashlib
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import threading

from .trade_database import get_trade_database

logger = logging.getLogger(__name__)


class StrategyVersionManager:
    """Manage strategy versioning and configuration tracking"""
    
    def __init__(self):
        """Initialize strategy version manager"""
        self.db = get_trade_database()
        self._version_cache = {}
        self._lock = threading.Lock()
        self._accounts_yaml_path = self._find_accounts_yaml()
        logger.info("✅ Strategy version manager initialized")
    
    def _find_accounts_yaml(self) -> Optional[str]:
        """Find accounts.yaml file"""
        # Try multiple possible locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '../../accounts.yaml'),
            os.path.join(os.path.dirname(__file__), '../../../accounts.yaml'),
            'accounts.yaml',
        ]
        
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                logger.info(f"✅ Found accounts.yaml: {abs_path}")
                return abs_path
        
        logger.warning("⚠️ accounts.yaml not found")
        return None
    
    def _compute_config_hash(self, config: Dict[str, Any]) -> str:
        """Compute hash of configuration for change detection"""
        # Create deterministic JSON string
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def detect_changes(self, strategy_id: str, current_config: Dict[str, Any]) -> Tuple[bool, int]:
        """
        Detect if strategy configuration has changed
        
        Returns:
            (has_changed, new_version)
        """
        with self._lock:
            # Compute hash of current config
            current_hash = self._compute_config_hash(current_config)
            
            # Get latest version from database
            latest_version = self.db.get_latest_strategy_version(strategy_id)
            
            if latest_version is None:
                # First time seeing this strategy
                new_version = 1
                return True, new_version
            
            # Check if hash has changed
            if latest_version['config_hash'] != current_hash:
                new_version = latest_version['version'] + 1
                return True, new_version
            
            # No change
            return False, latest_version['version']
    
    def create_version(self, strategy_id: str, config_snapshot: Dict[str, Any], 
                      description: str = "") -> int:
        """
        Create new version entry for strategy
        
        Returns:
            New version number
        """
        with self._lock:
            config_hash = self._compute_config_hash(config_snapshot)
            
            # Get latest version
            latest_version = self.db.get_latest_strategy_version(strategy_id)
            new_version = 1 if latest_version is None else latest_version['version'] + 1
            
            # Insert new version
            success = self.db.insert_strategy_version(
                strategy_id=strategy_id,
                version=new_version,
                parameters_snapshot=config_snapshot,
                config_hash=config_hash,
                description=description
            )
            
            if success:
                # Update cache
                self._version_cache[strategy_id] = new_version
                logger.info(f"✅ Created strategy version: {strategy_id} v{new_version}")
                return new_version
            else:
                # Return existing version if insert failed
                return latest_version['version'] if latest_version else 1
    
    def get_current_version(self, strategy_id: str) -> int:
        """Get current version number for strategy"""
        # Check cache first
        if strategy_id in self._version_cache:
            return self._version_cache[strategy_id]
        
        # Get from database
        latest_version = self.db.get_latest_strategy_version(strategy_id)
        if latest_version:
            version = latest_version['version']
            self._version_cache[strategy_id] = version
            return version
        
        return 1  # Default to version 1
    
    def get_version_history(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all versions for a strategy"""
        return self.db.get_strategy_versions(strategy_id)
    
    def compare_versions(self, strategy_id: str, version1: int, 
                        version2: int) -> Dict[str, Any]:
        """Compare two versions of a strategy"""
        versions = self.db.get_strategy_versions(strategy_id)
        
        v1_data = next((v for v in versions if v['version'] == version1), None)
        v2_data = next((v for v in versions if v['version'] == version2), None)
        
        if not v1_data or not v2_data:
            return {'error': 'Version not found'}
        
        # Extract parameter snapshots
        params1 = v1_data['parameters_snapshot']
        params2 = v2_data['parameters_snapshot']
        
        # Find differences
        differences = {}
        all_keys = set(params1.keys()) | set(params2.keys())
        
        for key in all_keys:
            val1 = params1.get(key)
            val2 = params2.get(key)
            
            if val1 != val2:
                differences[key] = {
                    'version1': val1,
                    'version2': val2
                }
        
        return {
            'version1': v1_data,
            'version2': v2_data,
            'differences': differences,
            'total_changes': len(differences)
        }
    
    def load_strategy_config_from_accounts(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Load strategy configuration from accounts.yaml"""
        if not self._accounts_yaml_path:
            return None
        
        try:
            with open(self._accounts_yaml_path, 'r') as f:
                accounts_data = yaml.safe_load(f)
            
            # Find account with this strategy
            for account in accounts_data.get('accounts', []):
                if account.get('strategy') == strategy_id:
                    # Extract relevant configuration
                    config = {
                        'strategy_id': strategy_id,
                        'instruments': account.get('instruments', []),
                        'risk_settings': account.get('risk_settings', {}),
                        'timeframe': account.get('timeframe', ''),
                        'description': account.get('description', ''),
                    }
                    return config
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to load strategy config: {e}")
            return None
    
    def auto_version_all_strategies(self) -> Dict[str, int]:
        """
        Automatically detect and version all strategies from accounts.yaml
        
        Returns:
            Dictionary mapping strategy_id to version number
        """
        if not self._accounts_yaml_path:
            logger.warning("⚠️ Cannot auto-version: accounts.yaml not found")
            return {}
        
        try:
            with open(self._accounts_yaml_path, 'r') as f:
                accounts_data = yaml.safe_load(f)
            
            versioned = {}
            
            for account in accounts_data.get('accounts', []):
                strategy_id = account.get('strategy')
                if not strategy_id:
                    continue
                
                # Extract configuration
                config = {
                    'strategy_id': strategy_id,
                    'instruments': account.get('instruments', []),
                    'risk_settings': account.get('risk_settings', {}),
                    'timeframe': account.get('timeframe', ''),
                    'description': account.get('description', ''),
                    'account_id': account.get('id', ''),
                    'account_name': account.get('name', ''),
                }
                
                # Check for changes
                has_changed, current_version = self.detect_changes(strategy_id, config)
                
                if has_changed:
                    # Create new version
                    description = f"Auto-detected from accounts.yaml on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    new_version = self.create_version(strategy_id, config, description)
                    versioned[strategy_id] = new_version
                else:
                    versioned[strategy_id] = current_version
            
            logger.info(f"✅ Auto-versioned {len(versioned)} strategies")
            return versioned
            
        except Exception as e:
            logger.error(f"❌ Failed to auto-version strategies: {e}")
            return {}
    
    def initialize_strategy_if_needed(self, strategy_id: str, 
                                     config: Optional[Dict[str, Any]] = None) -> int:
        """
        Initialize strategy version if it doesn't exist
        
        Returns:
            Current version number
        """
        latest_version = self.db.get_latest_strategy_version(strategy_id)
        
        if latest_version is None:
            # Strategy not versioned yet, create initial version
            if config is None:
                # Try to load from accounts.yaml
                config = self.load_strategy_config_from_accounts(strategy_id)
            
            if config is None:
                # Create minimal config
                config = {
                    'strategy_id': strategy_id,
                    'initialized_at': datetime.now().isoformat()
                }
            
            description = "Initial version"
            return self.create_version(strategy_id, config, description)
        
        return latest_version['version']
    
    def get_version_for_trade(self, strategy_id: str, 
                             config: Optional[Dict[str, Any]] = None) -> int:
        """
        Get appropriate version number for a new trade
        Auto-creates version if configuration has changed
        """
        if config is None:
            # Use cached version
            return self.get_current_version(strategy_id)
        
        # Check for changes
        has_changed, version = self.detect_changes(strategy_id, config)
        
        if has_changed:
            # Create new version
            description = f"Configuration updated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            return self.create_version(strategy_id, config, description)
        
        return version
    
    def get_version_performance_comparison(self, strategy_id: str) -> Dict[str, Any]:
        """
        Get performance comparison across all versions
        Requires metrics calculator integration
        """
        versions = self.get_version_history(strategy_id)
        
        if not versions:
            return {'error': 'No versions found'}
        
        # Get trades for each version from database
        version_performance = []
        
        for version_data in versions:
            version_num = version_data['version']
            
            # This would need integration with trade database and metrics calculator
            # For now, return basic structure
            version_performance.append({
                'version': version_num,
                'deployed_timestamp': version_data['deployed_timestamp'],
                'description': version_data.get('description', ''),
                'parameters': version_data['parameters_snapshot'],
                # Metrics would be calculated here
                'metrics': {}
            })
        
        return {
            'strategy_id': strategy_id,
            'total_versions': len(versions),
            'versions': version_performance
        }
    
    def export_version_history(self, strategy_id: str, 
                              output_path: Optional[str] = None) -> str:
        """Export version history to JSON file"""
        versions = self.get_version_history(strategy_id)
        
        export_data = {
            'strategy_id': strategy_id,
            'exported_at': datetime.now().isoformat(),
            'total_versions': len(versions),
            'versions': versions
        }
        
        if output_path is None:
            output_path = f"strategy_versions_{strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"✅ Version history exported: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Failed to export version history: {e}")
            return ""
    
    def clear_cache(self):
        """Clear version cache"""
        with self._lock:
            self._version_cache.clear()
            logger.info("✅ Version cache cleared")


# Singleton instance
_strategy_version_manager_instance = None
_strategy_version_manager_lock = threading.Lock()


def get_strategy_version_manager() -> StrategyVersionManager:
    """Get singleton strategy version manager instance"""
    global _strategy_version_manager_instance
    
    if _strategy_version_manager_instance is None:
        with _strategy_version_manager_lock:
            if _strategy_version_manager_instance is None:
                _strategy_version_manager_instance = StrategyVersionManager()
    
    return _strategy_version_manager_instance

