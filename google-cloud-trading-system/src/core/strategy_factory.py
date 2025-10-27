#!/usr/bin/env python3
"""
Strategy Factory - Hybrid auto-discovery + manual override system
Centralized strategy loading with explicit control and fallback auto-discovery
"""

import logging
import importlib
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Manual overrides for explicit control
STRATEGY_OVERRIDES = {
    'momentum_trading': {
        'module': 'src.strategies.momentum_trading',
        'class': 'MomentumTradingStrategy',
        'getter': 'get_momentum_trading_strategy'
    },
    'gold_scalping': {
        'module': 'src.strategies.gold_scalping_optimized',
        'class': 'GoldScalpingStrategy',
        'getter': 'get_gold_scalping_strategy'
    },
    'ultra_strict_forex': {
        'module': 'src.strategies.ultra_strict_forex_optimized',
        'class': 'UltraStrictForexStrategy',
        'getter': 'get_ultra_strict_forex_strategy'
    },
    'adaptive_trump_gold': {
        'module': 'src.strategies.adaptive_trump_gold_strategy',
        'getter': 'get_adaptive_trump_gold_strategy'
    },
    'champion_75wr': {
        'module': 'src.strategies.champion_75wr',
        'getter': 'get_champion_75wr_strategy'
    },
    'breakout': {
        'module': 'src.strategies.breakout_strategy',
        'class': 'BreakoutStrategy',
        'getter': 'get_breakout_strategy'
    },
    'scalping': {
        'module': 'src.strategies.scalping_strategy',
        'class': 'ScalpingStrategy',
        'getter': 'get_scalping_strategy'
    },
    'swing_trading': {
        'module': 'src.strategies.swing_strategy',
        'class': 'SwingStrategy',
        'getter': 'get_swing_strategy'
    },
    'all_weather_70wr': {
        'module': 'src.strategies.all_weather_70wr',
        'getter': 'get_all_weather_70wr_strategy'
    },
    'ultra_strict_v2': {
        'module': 'src.strategies.ultra_strict_v2',
        'getter': 'get_ultra_strict_v2_strategy'
    },
    'momentum_v2': {
        'module': 'src.strategies.momentum_v2',
        'getter': 'get_momentum_v2_strategy'
    }
}

class StrategyFactory:
    """
    Strategy Factory with hybrid loading approach:
    1. Manual overrides for explicit control
    2. Auto-discovery fallback for flexibility
    3. Caching for performance
    """
    
    def __init__(self):
        self._strategy_cache = {}
        self._load_errors = {}
        logger.info("✅ Strategy Factory initialized")
    
    def get_strategy(self, strategy_name: str, account_config: Dict = None) -> Any:
        """
        Load strategy by name with hybrid approach
        
        Args:
            strategy_name: Name of strategy from accounts.yaml
            account_config: Account configuration dict
            
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If strategy cannot be loaded
        """
        # Check cache first
        if strategy_name in self._strategy_cache:
            logger.debug(f"📦 Using cached strategy: {strategy_name}")
            return self._strategy_cache[strategy_name]
        
        # Check manual overrides first
        if strategy_name in STRATEGY_OVERRIDES:
            logger.info(f"🔧 Loading strategy from override: {strategy_name}")
            strategy = self._load_from_override(strategy_name, account_config)
            if strategy:
                self._strategy_cache[strategy_name] = strategy
                logger.info(f"✅ Successfully loaded strategy: {strategy_name}")
                return strategy
        
        # Fall back to auto-discovery
        logger.info(f"🔍 Attempting auto-discovery for: {strategy_name}")
        strategy = self._auto_discover(strategy_name, account_config)
        if strategy:
            self._strategy_cache[strategy_name] = strategy
            logger.info(f"✅ Auto-discovered strategy: {strategy_name}")
            return strategy
        
        # Log error and raise
        error_msg = f"Strategy '{strategy_name}' not found"
        self._load_errors[strategy_name] = {
            'error': error_msg,
            'timestamp': datetime.now(),
            'account_config': account_config
        }
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    def _load_from_override(self, strategy_name: str, account_config: Dict = None) -> Optional[Any]:
        """Load strategy using manual override configuration"""
        try:
            override = STRATEGY_OVERRIDES[strategy_name]
            module_name = override['module']
            
            # Import module
            module = importlib.import_module(module_name)
            
            # Try getter function first (preferred)
            if 'getter' in override:
                getter_name = override['getter']
                if hasattr(module, getter_name):
                    getter_func = getattr(module, getter_name)
                    logger.debug(f"📞 Calling getter: {getter_name}")
                    return getter_func()
            
            # Fall back to class instantiation
            if 'class' in override:
                class_name = override['class']
                if hasattr(module, class_name):
                    strategy_class = getattr(module, class_name)
                    logger.debug(f"🏗️ Instantiating class: {class_name}")
                    
                    # Pass instruments if available in account config
                    instruments = None
                    if account_config and 'instruments' in account_config:
                        instruments = account_config['instruments']
                    
                    if instruments:
                        return strategy_class(instruments=instruments)
                    else:
                        return strategy_class()
            
            logger.warning(f"⚠️ Override config incomplete for {strategy_name}")
            return None
            
        except ImportError as e:
            logger.error(f"❌ Import error for {strategy_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading {strategy_name}: {e}")
            return None
    
    def _auto_discover(self, strategy_name: str, account_config: Dict = None) -> Optional[Any]:
        """
        Auto-discover strategy by common patterns
        
        This provides fallback loading for strategies not in overrides
        """
        try:
            # Common patterns to try
            patterns = [
                f'src.strategies.{strategy_name}',
                f'src.strategies.{strategy_name}_strategy',
                f'src.strategies.{strategy_name}_optimized',
                f'src.strategies.{strategy_name}_v2'
            ]
            
            for pattern in patterns:
                try:
                    module = importlib.import_module(pattern)
                    
                    # Look for common getter patterns
                    getter_patterns = [
                        f'get_{strategy_name}_strategy',
                        f'get_{strategy_name}',
                        f'get_{strategy_name.replace("_", "")}_strategy'
                    ]
                    
                    for getter_pattern in getter_patterns:
                        if hasattr(module, getter_pattern):
                            getter_func = getattr(module, getter_pattern)
                            logger.debug(f"🔍 Auto-discovered getter: {getter_pattern}")
                            return getter_func()
                    
                    # Look for common class patterns
                    class_patterns = [
                        f'{strategy_name.title().replace("_", "")}Strategy',
                        f'{strategy_name.replace("_", "").title()}Strategy',
                        f'{strategy_name.title()}Strategy'
                    ]
                    
                    for class_pattern in class_patterns:
                        if hasattr(module, class_pattern):
                            strategy_class = getattr(module, class_pattern)
                            logger.debug(f"🔍 Auto-discovered class: {class_pattern}")
                            
                            # Pass instruments if available
                            instruments = None
                            if account_config and 'instruments' in account_config:
                                instruments = account_config['instruments']
                            
                            if instruments:
                                return strategy_class(instruments=instruments)
                            else:
                                return strategy_class()
                
                except ImportError:
                    continue
            
            logger.debug(f"🔍 No auto-discovery patterns matched for {strategy_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Auto-discovery error for {strategy_name}: {e}")
            return None
    
    def get_loaded_strategies(self) -> List[str]:
        """Get list of currently loaded strategy names"""
        return list(self._strategy_cache.keys())
    
    def get_load_errors(self) -> Dict[str, Dict]:
        """Get dictionary of strategy loading errors"""
        return self._load_errors.copy()
    
    def clear_cache(self):
        """Clear strategy cache (useful for testing)"""
        self._strategy_cache.clear()
        logger.info("🧹 Strategy cache cleared")
    
    def preload_strategies(self, strategy_names: List[str], account_configs: Dict[str, Dict] = None):
        """
        Preload multiple strategies
        
        Args:
            strategy_names: List of strategy names to preload
            account_configs: Optional dict mapping strategy names to account configs
        """
        logger.info(f"📦 Preloading {len(strategy_names)} strategies")
        
        for strategy_name in strategy_names:
            try:
                account_config = account_configs.get(strategy_name) if account_configs else None
                self.get_strategy(strategy_name, account_config)
            except Exception as e:
                logger.warning(f"⚠️ Failed to preload {strategy_name}: {e}")
        
        logger.info(f"✅ Preloaded {len(self._strategy_cache)} strategies")

# Global factory instance
_strategy_factory = None

def get_strategy_factory() -> StrategyFactory:
    """Get global strategy factory instance"""
    global _strategy_factory
    if _strategy_factory is None:
        _strategy_factory = StrategyFactory()
    return _strategy_factory

def reset_strategy_factory():
    """Reset global strategy factory (useful for testing)"""
    global _strategy_factory
    _strategy_factory = None
