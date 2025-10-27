#!/usr/bin/env python3
"""
Config Reloader - Hot reload mechanism for strategy configuration changes
Handles configuration file watching, hot-reload, and system restart signaling
"""

import os
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigReloader:
    """Manages hot-reload of strategy parameters and config change notifications"""
    
    def __init__(self):
        self.watch_thread = None
        self.is_watching = False
        self.last_modification_times = {}
        self.config_change_callbacks = []
        
        logger.info("✅ Config Reloader initialized")
    
    def start_watching(self, config_paths: List[Path]):
        """Start watching configuration files for changes"""
        if self.is_watching:
            logger.warning("⚠️ Already watching config files")
            return
        
        self.is_watching = True
        self.config_paths = config_paths
        
        # Initialize last modification times
        for path in config_paths:
            if path.exists():
                self.last_modification_times[str(path)] = path.stat().st_mtime
        
        # Start watch thread
        self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.watch_thread.start()
        
        logger.info(f"👀 Watching {len(config_paths)} config files")
    
    def stop_watching(self):
        """Stop watching configuration files"""
        self.is_watching = False
        if self.watch_thread:
            self.watch_thread.join(timeout=5.0)
        logger.info("⏹️ Stopped watching config files")
    
    def _watch_loop(self):
        """Background thread that watches for config file changes"""
        while self.is_watching:
            try:
                for config_path in self.config_paths:
                    if not config_path.exists():
                        continue
                    
                    path_str = str(config_path)
                    current_mtime = config_path.stat().st_mtime
                    last_mtime = self.last_modification_times.get(path_str)
                    
                    if last_mtime and current_mtime > last_mtime:
                        logger.info(f"📝 Config file changed: {config_path.name}")
                        self.last_modification_times[path_str] = current_mtime
                        self._handle_config_change(config_path)
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in watch loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _handle_config_change(self, config_path: Path):
        """Handle configuration file change"""
        try:
            change_info = {
                'file': config_path.name,
                'timestamp': datetime.now().isoformat()
            }
            
            # Notify all registered callbacks
            for callback in self.config_change_callbacks:
                try:
                    callback(change_info)
                except Exception as e:
                    logger.error(f"❌ Callback error: {e}")
            
            logger.info(f"✅ Notified {len(self.config_change_callbacks)} callbacks of config change")
            
        except Exception as e:
            logger.error(f"❌ Error handling config change: {e}")
    
    def register_callback(self, callback: Callable):
        """Register a callback for config change notifications"""
        self.config_change_callbacks.append(callback)
        logger.info(f"📝 Registered config change callback")
    
    def reload_strategy_params(self, strategy_name: str, params: Dict[str, Any]) -> bool:
        """
        Hot-reload strategy parameters without full restart
        
        This updates running strategies in memory without stopping them
        """
        try:
            logger.info(f"🔄 Hot-reloading parameters for strategy: {strategy_name}")
            
            # Import here to avoid circular imports
            from .strategy_manager import get_strategy_manager
            
            strategy_manager = get_strategy_manager()
            
            # Get the strategy instance
            if hasattr(strategy_manager, 'strategies') and strategy_name in strategy_manager.strategies:
                strategy_config = strategy_manager.strategies[strategy_name]
                
                # Update parameters on the running strategy
                if hasattr(strategy_config, 'strategy_instance'):
                    strategy_instance = strategy_config.strategy_instance
                    
                    # Update parameters dynamically
                    for key, value in params.items():
                        if hasattr(strategy_instance, key):
                            setattr(strategy_instance, key, value)
                            logger.info(f"  ✓ Updated {key} = {value}")
                    
                    logger.info(f"✅ Hot-reloaded parameters for {strategy_name}")
                    return True
                else:
                    logger.warning(f"⚠️ No strategy instance found for {strategy_name}")
                    return False
            else:
                logger.warning(f"⚠️ Strategy {strategy_name} not found in manager")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to hot-reload strategy params: {e}")
            return False
    
    def signal_full_restart(self, reason: str = "Configuration change"):
        """
        Signal that a full system restart is required
        
        This is used when changes require stopping and restarting the trading system
        """
        try:
            logger.warning(f"⚠️ Full restart required: {reason}")
            
            # Send notification to system components
            restart_info = {
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'restart_required': True
            }
            
            # Notify all callbacks
            for callback in self.config_change_callbacks:
                try:
                    callback(restart_info)
                except Exception as e:
                    logger.error(f"❌ Callback error: {e}")
            
            logger.info("✅ Full restart signal sent to system components")
            
        except Exception as e:
            logger.error(f"❌ Failed to signal full restart: {e}")
    
    def notify_all_components(self, change_type: str, affected_strategies: List[str], details: Dict[str, Any] = None):
        """
        Notify all system components of a configuration change
        
        Args:
            change_type: Type of change (e.g., 'param_update', 'strategy_switch', 'enable', 'disable')
            affected_strategies: List of strategy names affected
            details: Additional details about the change
        """
        try:
            notification = {
                'type': change_type,
                'strategies': affected_strategies,
                'timestamp': datetime.now().isoformat(),
                'details': details or {}
            }
            
            logger.info(f"📢 Notifying components of {change_type} for strategies: {', '.join(affected_strategies)}")
            
            # Notify all callbacks
            for callback in self.config_change_callbacks:
                try:
                    callback(notification)
                except Exception as e:
                    logger.error(f"❌ Callback error: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to notify components: {e}")


# Global instance
_config_reloader = None


def get_config_reloader() -> ConfigReloader:
    """Get global config reloader instance"""
    global _config_reloader
    if _config_reloader is None:
        _config_reloader = ConfigReloader()
    return _config_reloader
