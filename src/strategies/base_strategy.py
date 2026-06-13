from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    Enforces the presence of a stable strategy_id.
    """
    
    # Subclasses MUST override this
    STRATEGY_ID = "base_strategy"
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = True
        
        # PHASE 1: Require STRATEGY_ID to be set by subclass
        if not hasattr(self.__class__, 'STRATEGY_ID') or self.__class__.STRATEGY_ID == "base_strategy":
            raise RuntimeError(
                f"Strategy {self.__class__.__name__} must define STRATEGY_ID class constant. "
                f"Current value: {getattr(self.__class__, 'STRATEGY_ID', 'MISSING')}"
            )
        
        # PHASE 1: Set strategy_id from STRATEGY_ID constant
        strategy_id = self.__class__.STRATEGY_ID
        if not strategy_id or strategy_id.strip() == "":
            raise RuntimeError(
                f"Strategy {self.__class__.__name__} has empty STRATEGY_ID. "
                f"STRATEGY_ID must be a non-empty string."
            )
        
        self.strategy_id = strategy_id
        
        # Validate strategy_id is set correctly
        if not self.strategy_id or self.strategy_id == "base_strategy":
            raise RuntimeError(
                f"Strategy {self.__class__.__name__} strategy_id is invalid: '{self.strategy_id}'. "
                f"STRATEGY_ID must be set to a non-empty value other than 'base_strategy'."
            )
            
    @abstractmethod
    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Analyze market and return list of signals.
        """
        pass
        
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        return {
            'name': self.__class__.__name__,
            'id': self.strategy_id,
            'enabled': self.enabled,
            'config': self.config
        }
