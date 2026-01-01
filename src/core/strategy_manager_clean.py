"""Clean strategy_manager shim (temporary) to deploy to VM."""
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class StrategyConfig:
    strategy_id: str = ""
    strategy_name: str = ""
    account_id: str = ""
    instruments: list = None
    max_daily_trades: int = 0


class AccountManagerShim:
    def get_account_info(self, account_id: str) -> Any:
        return None


class StrategyManagerShim:
    def __init__(self):
        self.strategies: Dict[str, StrategyConfig] = {}
        self.account_manager = AccountManagerShim()

    def get_strategy_performance_comparison(self):
        return {}

    def get_system_status(self):
        return {"running": False}


_singleton: Optional[StrategyManagerShim] = None


def get_strategy_manager() -> StrategyManagerShim:
    global _singleton
    if _singleton is None:
        _singleton = StrategyManagerShim()
    return _singleton


__all__ = ["get_strategy_manager", "StrategyConfig"]


