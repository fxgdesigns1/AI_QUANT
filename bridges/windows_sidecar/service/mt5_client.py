"""MT5 client wrapper for Windows Sidecar (read-only)."""
import time
from typing import Any, Optional
from .config import MT5_TERMINAL_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

_mt5 = None
_init_ok = False
_last_error = (None, None)


def get_mt5():
    """Lazy import MetaTrader5."""
    global _mt5
    if _mt5 is None:
        try:
            import MetaTrader5 as _mt5_mod
            _mt5 = _mt5_mod
        except ImportError:
            return None
    return _mt5


def initialize_mt5() -> tuple[bool, Optional[int], Optional[str]]:
    """Initialize MT5 connection. Returns (ok, error_code, error_message)."""
    global _init_ok, _last_error
    mt5 = get_mt5()
    if not mt5:
        _last_error = (None, "MetaTrader5 package not installed")
        return False, None, _last_error[1]

    path = MT5_TERMINAL_PATH or None
    login = MT5_LOGIN or 0
    password = MT5_PASSWORD or ""
    server = MT5_SERVER or ""

    ok = mt5.initialize(path=path, login=login, password=password, server=server)
    if not ok:
        err = mt5.last_error()
        _last_error = (err[0], err[1] if err else "Unknown MT5 init error")
        return False, _last_error[0], _last_error[1]
    _init_ok = True
    return True, None, None


def account_info() -> Optional[Any]:
    """Get account info. Returns None if unavailable."""
    mt5 = get_mt5()
    if not mt5 or not _init_ok:
        return None
    return mt5.account_info()


def positions_get(symbol: Optional[str] = None) -> list:
    """Get positions (all or for symbol)."""
    mt5 = get_mt5()
    if not mt5 or not _init_ok:
        return []
    r = mt5.positions_get(symbol=symbol)
    return list(r) if r else []


def orders_get(symbol: Optional[str] = None) -> list:
    """Get orders."""
    mt5 = get_mt5()
    if not mt5 or not _init_ok:
        return []
    r = mt5.orders_get(symbol=symbol)
    return list(r) if r else []


def symbol_info_tick(symbol: str) -> Optional[Any]:
    """Get tick for symbol."""
    mt5 = get_mt5()
    if not mt5 or not _init_ok:
        return None
    return mt5.symbol_info_tick(symbol)


def _find_broker_symbol_variant(base_symbol: str, mt5) -> Optional[str]:
    """If exact symbol not found, search for broker variant (e.g. EURUSDm, EURUSD.a).
    Returns shortest match to prefer closest variant (EURUSDm over EURUSD_MICRO)."""
    all_syms = mt5.symbols_get()
    if not all_syms:
        return None
    base_upper = base_symbol.upper()
    candidates = []
    for s in all_syms:
        name = getattr(s, "name", None) or ""
        nu = name.upper()
        if base_upper in nu and nu.startswith(base_upper[:3]):
            candidates.append(name)
    return min(candidates, key=len) if candidates else None


def symbol_info_tick_with_auto_select(symbol: str) -> tuple[Optional[Any], Optional[str], Optional[str], Optional[str]]:
    """Get tick for symbol. If tick is None, try symbol_select(symbol, True) then retry.
    If exact symbol not found, try broker variant (e.g. EURUSDm).
    Returns (tick, failure_bucket, recommended_fix, broker_symbol_actual). Read-only safe."""
    global _init_ok
    mt5 = get_mt5()
    if not mt5:
        return None, "mt5_not_initialized", "MetaTrader5 package not installed", None
    if not _init_ok:
        ok, _, _ = initialize_mt5()
        if not ok:
            return None, "mt5_not_initialized", "Ensure MT5 is running and sidecar initialized", None

    tick = mt5.symbol_info_tick(symbol)
    if tick and (tick.bid or tick.ask or tick.last):
        return tick, None, None, None

    # Symbol may not be in Market Watch - try symbol_select (read-only safe)
    info = mt5.symbol_info(symbol)
    if not info:
        broker_variant = _find_broker_symbol_variant(symbol, mt5)
        if broker_variant and broker_variant != symbol:
            return None, "symbol_name_mismatch", (
                f"Broker uses '{broker_variant}', not '{symbol}'. "
                f"Query /symbols/{broker_variant}/tick or add {broker_variant} to Market Watch."
            ), broker_variant
        err = mt5.last_error()
        return None, "symbol_not_found", f"Symbol {symbol} does not exist on broker. last_error={err}", None

    selected = getattr(info, "select", getattr(info, "selected", False))
    if not selected:
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)

    if not tick:
        err = mt5.last_error()
        return None, "no_tick_data", f"Tick unavailable for {symbol}. last_error={err}. Ensure symbol in Market Watch.", None
    if not tick.bid and not tick.ask:
        return tick, "no_tick_data", "Tick returned but bid/ask zero. Market may be closed or symbol inactive.", None
    return tick, None, None, None


def symbol_info(symbol: str) -> Optional[Any]:
    """Get symbol spec."""
    mt5 = get_mt5()
    if not mt5 or not _init_ok:
        return None
    return mt5.symbol_info(symbol)


def last_error() -> tuple[Optional[int], Optional[str]]:
    """Return last MT5 error."""
    return _last_error
