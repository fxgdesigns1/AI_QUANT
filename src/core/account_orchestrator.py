from typing import Any, Dict, Callable, Optional

from .order_manager import TradeSignal, OrderManager, get_order_manager
from datetime import datetime


class AccountOrchestrator:
    """
    Lightweight per-account orchestrator.
    - Maintains a separate OrderManager per account_id.
    - If a signal carries an account_id that has been registered, routes to that manager.
    - Falls back to a default shared OrderManager when account_id is missing or unregistered.
    """

    def __init__(self) -> None:
        self._managers: Dict[str, OrderManager] = {}
        self._default_manager: OrderManager = get_order_manager()
        self._executors: Dict[str, Callable[[Any], Any]] = {}

    def register_account(self, account_id: str, accounts: Any = None, executor: Optional[Callable[[Any], Any]] = None) -> None:
        """Register a new account context with its own OrderManager.

        If an executor callable is provided, it will be called for routed signals
        instead of the raw OrderManager.place_order. This allows upstream systems
        to keep their execution checks while centralizing routing.
        """
        self._managers[account_id] = get_order_manager(accounts)
        if executor:
            self._executors[account_id] = executor

    def route_signal(self, signal: TradeSignal):
        """Route a TradeSignal to the appropriate per-account OrderManager."""
        # Prefer executor callback if registered for this account.
        if signal.account_id and signal.account_id in self._executors:
            try:
                return self._executors[signal.account_id](signal_to_dict(signal))
            except Exception:
                # Fall back to manager if executor fails
                pass

        if signal.account_id and signal.account_id in self._managers:
            manager = self._managers[signal.account_id]
        else:
            manager = self._default_manager
        return manager.place_order(signal)


def signal_to_dict(signal: TradeSignal) -> Dict[str, Any]:
    """Convert TradeSignal dataclass to a plain dict compatible with existing execute_trade()."""
    return {
        'instrument': signal.instrument,
        'side': signal.side.value if hasattr(signal.side, 'value') else str(signal.side),
        'entry_price': signal.entry_price,
        'stop_loss': signal.stop_loss,
        'take_profit': signal.take_profit,
        'confidence': signal.confidence,
        'strategy': getattr(signal, 'strategy_name', None),
        'timestamp': getattr(signal, 'timestamp', None),
        'account_id': getattr(signal, 'account_id', None),
    }


def route_signal_dict(signal: Dict[str, Any]):
    """Route a plain signal dict using account_id (if present) to the registered executor or manager."""
    account_id = signal.get('account_id') or signal.get('account') or signal.get('acct') or None
    # If executor present for account, call it directly (executors expect dict)
    if account_id and account_id in _global_account_orchestrator._executors:
        try:
            return _global_account_orchestrator._executors[account_id](signal)
        except Exception:
            pass
    # Fallback: if manager exists, convert dict to TradeSignal and route
    if account_id and account_id in _global_account_orchestrator._managers:
        manager = _global_account_orchestrator._managers[account_id]
        # Build minimal TradeSignal for manager.place_order compatibility if needed
        ts = TradeSignal(
            instrument=signal.get('instrument'),
            side=signal.get('side'),
            units=signal.get('units', 0),
            entry_price=signal.get('entry_price', 0.0),
            stop_loss=signal.get('stop_loss', 0.0),
            take_profit=signal.get('take_profit', 0.0),
            confidence=signal.get('confidence', 0.0),
            timestamp=signal.get('timestamp') or datetime.utcnow(),
            strategy_name=signal.get('strategy') or signal.get('strategy_name'),
            account_id=account_id
        )
        return manager.place_order(ts)
    # Final fallback: try default manager
    try:
        default_mgr = _global_account_orchestrator._default_manager
        ts = TradeSignal(
            instrument=signal.get('instrument'),
            side=signal.get('side'),
            units=signal.get('units', 0),
            entry_price=signal.get('entry_price', 0.0),
            stop_loss=signal.get('stop_loss', 0.0),
            take_profit=signal.get('take_profit', 0.0),
            confidence=signal.get('confidence', 0.0),
            timestamp=signal.get('timestamp') or datetime.utcnow(),
            strategy_name=signal.get('strategy') or signal.get('strategy_name'),
            account_id=account_id
        )
        return default_mgr.place_order(ts)
    except Exception:
        return None


# Simple singleton instance to be imported by downstream code
_global_account_orchestrator = AccountOrchestrator()

def get_account_orchestrator() -> AccountOrchestrator:
    """Accessor for the global account orchestrator."""
    return _global_account_orchestrator


