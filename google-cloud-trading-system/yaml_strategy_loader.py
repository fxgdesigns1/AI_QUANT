#!/usr/bin/env python3
"""
YAML Strategy Loader - Load strategy parameters from YAML
"""

import os
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class YAMLStrategyLoader:
    def __init__(self, config_file: str = 'ULTRA_TIGHT_CONFIG.yaml'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        try:
            config_path = os.path.join(os.path.dirname(__file__), self.config_file)
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Loaded config from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return {}
    
    def get_strategy_params(self, strategy_name: str) -> Dict[str, Any]:
        try:
            return self.config.get('strategies', {}).get(strategy_name, {})
        except Exception as e:
            logger.error(f"❌ Failed to get strategy params: {e}")
            return {}
    
    def get_trade_manager_params(self) -> Dict[str, Any]:
        return self.config.get('trade_manager', {})
    
    def get_risk_management_params(self, account: str) -> Dict[str, Any]:
        return self.config.get('risk_management', {}).get(account, {})
    
    def reload(self):
        self.config = self.load_config()
        logger.info("🔄 Configuration reloaded")

def get_yaml_loader(config_file: str = 'ULTRA_TIGHT_CONFIG.yaml') -> YAMLStrategyLoader:
    return YAMLStrategyLoader(config_file)
