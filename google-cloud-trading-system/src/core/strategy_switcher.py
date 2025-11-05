#!/usr/bin/env python3
"""
Strategy Switcher - Handles strategy switching and scanner reloading
FIXED: Now properly reloads scanner after strategy changes
"""

import logging
import sys
import importlib
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def reload_scanner_after_strategy_switch():
    """Reload scanner with new strategy configuration from accounts.yaml"""
    try:
        from .simple_timer_scanner import get_simple_scanner
        
        # Clear singleton instance to force reload
        scanner_module = sys.modules.get('src.core.simple_timer_scanner')
        if scanner_module and hasattr(scanner_module, '_simple_scanner'):
            logger.info("🔄 Clearing scanner singleton for reload...")
            scanner_module._simple_scanner = None
        
        # Force reload of scanner module
        if 'src.core.simple_timer_scanner' in sys.modules:
            importlib.reload(sys.modules['src.core.simple_timer_scanner'])
        
        # Get new scanner instance (will reload from accounts.yaml)
        new_scanner = get_simple_scanner()
        
        if new_scanner and new_scanner.strategies:
            logger.info(f"✅ Scanner reloaded with {len(new_scanner.strategies)} strategies")
            return True
        else:
            logger.error("❌ Scanner reloaded but no strategies found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to reload scanner: {e}")
        import traceback
        traceback.print_exc()
        return False


def switch_strategy(account_id: str, new_strategy: str) -> Dict[str, any]:
    """
    Switch strategy for an account and reload scanner
    
    Args:
        account_id: Account ID to switch
        new_strategy: New strategy name
        
    Returns:
        Dict with success status and details
    """
    try:
        from .yaml_manager import get_yaml_manager
        
        yaml_mgr = get_yaml_manager()
        
        # Update accounts.yaml
        success = yaml_mgr.update_account_strategy(account_id, new_strategy)
        
        if not success:
            return {
                'success': False,
                'error': 'Failed to update accounts.yaml'
            }
        
        # Reload scanner with new configuration
        reload_success = reload_scanner_after_strategy_switch()
        
        if reload_success:
            logger.info(f"✅ Strategy switched: {account_id} → {new_strategy}")
            return {
                'success': True,
                'account_id': account_id,
                'new_strategy': new_strategy,
                'scanner_reloaded': True
            }
        else:
            return {
                'success': False,
                'error': 'Strategy updated but scanner reload failed',
                'account_id': account_id,
                'new_strategy': new_strategy
            }
            
    except Exception as e:
        logger.error(f"❌ Strategy switch failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def reload_config():
    """Reload configuration and scanner without changing strategies"""
    try:
        logger.info("🔄 Reloading configuration...")
        
        # Reload scanner (will re-read accounts.yaml)
        success = reload_scanner_after_strategy_switch()
        
        if success:
            logger.info("✅ Configuration reloaded successfully")
            return {
                'success': True,
                'message': 'Configuration reloaded'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to reload scanner'
            }
            
    except Exception as e:
        logger.error(f"❌ Config reload failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
