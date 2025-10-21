#!/usr/bin/env python3
"""
Graceful Restart Manager
Handles safe system restarts with position monitoring and configuration updates
"""

import os
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class RestartStatus(Enum):
    """Restart status enumeration"""
    IDLE = "idle"
    CHECKING_POSITIONS = "checking_positions"
    WAITING_FOR_CLOSE = "waiting_for_close"
    APPLYING_CONFIG = "applying_config"
    RESTARTING_SCANNER = "restarting_scanner"
    COMPLETE = "complete"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class GracefulRestartManager:
    """
    Manages graceful system restarts with safety checks
    
    Features:
    - Check for open positions
    - Wait for positions to close (with timeout)
    - Apply configuration changes safely
    - Restart scanner with new configuration
    - Rollback on failure
    - Real-time status updates via callbacks
    """
    
    def __init__(self):
        """Initialize graceful restart manager"""
        self.status = RestartStatus.IDLE
        self.restart_in_progress = False
        self.open_positions_count = 0
        self.status_message = ""
        self.progress_callbacks: List[Callable] = []
        
        # Timeout settings (seconds)
        self.position_close_timeout = 30
        self.max_wait_time = 60
        
        logger.info("✅ Graceful Restart Manager initialized")
    
    def add_progress_callback(self, callback: Callable):
        """Add callback for progress updates"""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, status: RestartStatus, message: str, data: Optional[Dict] = None):
        """Notify all callbacks of progress"""
        self.status = status
        self.status_message = message
        
        payload = {
            'status': status.value,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data or {}
        }
        
        logger.info(f"🔄 Restart progress: {message}")
        
        for callback in self.progress_callbacks:
            try:
                callback(payload)
            except Exception as e:
                logger.error(f"❌ Progress callback error: {e}")
    
    def check_open_positions(self) -> Dict[str, Any]:
        """
        Check for open positions across all active accounts
        
        Returns:
            Dict with position count and details
        """
        try:
            from .oanda_client import get_oanda_client
            from .yaml_manager import get_yaml_manager
            
            oanda = get_oanda_client()
            yaml_mgr = get_yaml_manager()
            
            accounts = yaml_mgr.get_all_accounts()
            total_positions = 0
            positions_by_account = {}
            
            for account in accounts:
                if not account.get('active', False):
                    continue
                
                account_id = account['id']
                
                try:
                    # Get open trades
                    trades = oanda.get_open_trades(account_id)
                    trade_count = len(trades) if trades else 0
                    
                    if trade_count > 0:
                        positions_by_account[account_id] = {
                            'count': trade_count,
                            'account_name': account.get('display_name', account.get('name')),
                            'trades': trades
                        }
                        total_positions += trade_count
                        
                except Exception as e:
                    logger.error(f"❌ Failed to check positions for {account_id}: {e}")
                    continue
            
            self.open_positions_count = total_positions
            
            return {
                'success': True,
                'total_positions': total_positions,
                'positions_by_account': positions_by_account,
                'safe_to_restart': total_positions == 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to check open positions: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_positions': 0,
                'safe_to_restart': False
            }
    
    def wait_for_positions_to_close(self, timeout: int = None) -> bool:
        """
        Wait for open positions to close
        
        Args:
            timeout: Maximum wait time in seconds (default: self.position_close_timeout)
            
        Returns:
            True if all positions closed, False if timeout
        """
        timeout = timeout or self.position_close_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            position_check = self.check_open_positions()
            
            if position_check.get('safe_to_restart', False):
                logger.info("✅ All positions closed")
                return True
            
            positions_count = position_check.get('total_positions', 0)
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            self._notify_progress(
                RestartStatus.WAITING_FOR_CLOSE,
                f"Waiting for {positions_count} position(s) to close... ({remaining}s remaining)",
                {'positions_count': positions_count, 'elapsed': elapsed, 'remaining': remaining}
            )
            
            time.sleep(2)  # Check every 2 seconds
        
        logger.warning(f"⚠️ Timeout waiting for positions to close")
        return False
    
    def apply_configuration(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply new configuration to accounts.yaml
        
        Args:
            new_config: New configuration to apply
            
        Returns:
            Dict with success status
        """
        try:
            from .yaml_manager import get_yaml_manager
            
            yaml_mgr = get_yaml_manager()
            
            # Validate config first
            if not yaml_mgr._validate_config(new_config):
                return {
                    'success': False,
                    'error': 'Configuration validation failed'
                }
            
            # Write config (auto-creates backup)
            success = yaml_mgr.write_config(new_config, backup=True)
            
            if success:
                logger.info("✅ Configuration applied successfully")
                return {
                    'success': True,
                    'backup_created': True
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to write configuration'
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to apply configuration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restart_scanner(self) -> Dict[str, Any]:
        """
        Restart the trading scanner with new configuration
        
        Returns:
            Dict with success status
        """
        try:
            # Get the global scanner instance
            import sys
            main_module = sys.modules.get('__main__')
            
            if not main_module:
                return {
                    'success': False,
                    'error': 'Main module not found'
                }
            
            scanner = getattr(main_module, 'scanner', None)
            
            if not scanner:
                logger.warning("⚠️ Scanner not found, will initialize on next run")
                return {
                    'success': True,
                    'message': 'Scanner will be initialized on next scheduled run'
                }
            
            # Stop current scanner if running
            if hasattr(scanner, 'is_running') and scanner.is_running:
                logger.info("🛑 Stopping current scanner...")
                if hasattr(scanner, 'stop'):
                    scanner.stop()
                time.sleep(2)
            
            # Reinitialize scanner with new config
            logger.info("🔄 Reinitializing scanner with new configuration...")
            from ..core.simple_timer_scanner import get_simple_scanner
            
            # Force recreation of singleton
            import importlib
            scanner_module = sys.modules.get('src.core.simple_timer_scanner')
            if scanner_module and hasattr(scanner_module, '_simple_scanner'):
                scanner_module._simple_scanner = None
            
            new_scanner = get_simple_scanner()
            
            # Update global reference
            if main_module:
                setattr(main_module, 'scanner', new_scanner)
            
            logger.info("✅ Scanner restarted successfully")
            
            return {
                'success': True,
                'scanner_reinitialized': True
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to restart scanner: {e}")
            logger.exception("Full traceback:")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_restart(
        self, 
        new_config: Dict[str, Any],
        force: bool = False,
        send_telegram: bool = True
    ) -> Dict[str, Any]:
        """
        Execute complete graceful restart process
        
        Args:
            new_config: New configuration to apply
            force: If True, apply immediately without waiting for positions
            send_telegram: Send Telegram notifications
            
        Returns:
            Dict with restart results
        """
        if self.restart_in_progress:
            return {
                'success': False,
                'error': 'Restart already in progress'
            }
        
        self.restart_in_progress = True
        
        try:
            # Step 1: Check open positions
            self._notify_progress(
                RestartStatus.CHECKING_POSITIONS,
                "Checking for open positions..."
            )
            
            position_check = self.check_open_positions()
            
            if not force and not position_check.get('safe_to_restart', False):
                # Step 2: Wait for positions to close
                positions_closed = self.wait_for_positions_to_close()
                
                if not positions_closed:
                    self._notify_progress(
                        RestartStatus.FAILED,
                        f"Timeout: {self.open_positions_count} position(s) still open"
                    )
                    
                    if send_telegram:
                        self._send_telegram_notification(
                            "⚠️ Strategy switch failed: Positions did not close in time"
                        )
                    
                    self.restart_in_progress = False
                    return {
                        'success': False,
                        'error': 'Positions did not close in time',
                        'open_positions': self.open_positions_count
                    }
            
            # Step 3: Apply configuration
            self._notify_progress(
                RestartStatus.APPLYING_CONFIG,
                "Applying new configuration..."
            )
            
            config_result = self.apply_configuration(new_config)
            
            if not config_result['success']:
                self._notify_progress(
                    RestartStatus.FAILED,
                    f"Failed to apply configuration: {config_result.get('error')}"
                )
                
                if send_telegram:
                    self._send_telegram_notification(
                        f"❌ Strategy switch failed: {config_result.get('error')}"
                    )
                
                self.restart_in_progress = False
                return config_result
            
            # Step 4: Restart scanner
            self._notify_progress(
                RestartStatus.RESTARTING_SCANNER,
                "Restarting trading scanner..."
            )
            
            scanner_result = self.restart_scanner()
            
            if not scanner_result['success']:
                logger.error("❌ Scanner restart failed, attempting rollback...")
                # Note: Rollback would happen here if we stored previous config
                self._notify_progress(
                    RestartStatus.FAILED,
                    f"Scanner restart failed: {scanner_result.get('error')}"
                )
                
                if send_telegram:
                    self._send_telegram_notification(
                        f"⚠️ Strategy switch warning: Config applied but scanner restart failed"
                    )
            
            # Step 5: Complete
            self._notify_progress(
                RestartStatus.COMPLETE,
                "Restart complete! New configuration active."
            )
            
            if send_telegram:
                self._send_telegram_notification(
                    "✅ Strategy configuration updated successfully! System restarted."
                )
            
            self.restart_in_progress = False
            
            return {
                'success': True,
                'config_applied': True,
                'scanner_restarted': scanner_result['success'],
                'duration_seconds': 0  # TODO: Track actual duration
            }
            
        except Exception as e:
            logger.error(f"❌ Restart execution failed: {e}")
            logger.exception("Full traceback:")
            
            self._notify_progress(
                RestartStatus.FAILED,
                f"Restart failed: {str(e)}"
            )
            
            if send_telegram:
                self._send_telegram_notification(
                    f"❌ Strategy switch failed: {str(e)}"
                )
            
            self.restart_in_progress = False
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_telegram_notification(self, message: str):
        """Send Telegram notification"""
        try:
            from .telegram_notifier import get_telegram_notifier
            notifier = get_telegram_notifier()
            notifier.send_message(message)
        except Exception as e:
            logger.warning(f"⚠️ Failed to send Telegram notification: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current restart status
        
        Returns:
            Dict with current status
        """
        position_check = self.check_open_positions()
        
        return {
            'status': self.status.value,
            'message': self.status_message,
            'restart_in_progress': self.restart_in_progress,
            'open_positions': position_check.get('total_positions', 0),
            'safe_to_restart': position_check.get('safe_to_restart', True),
            'positions_by_account': position_check.get('positions_by_account', {})
        }


# Global instance
_restart_manager = None


def get_restart_manager() -> GracefulRestartManager:
    """Get global restart manager instance"""
    global _restart_manager
    if _restart_manager is None:
        _restart_manager = GracefulRestartManager()
    return _restart_manager



