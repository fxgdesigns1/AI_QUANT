from typing import Dict, Any, List, Tuple

class PolicyViolation(Exception):
    pass


def summarize_market(data_feed, accounts: List[str]) -> Dict[str, Any]:
    summary = {}
    for account_id in accounts:
        try:
            market = data_feed.get_market_data(account_id)
            if not market:
                continue
            for instrument, md in market.items():
                key = f"{account_id}:{instrument}"
                summary[key] = {
                    'bid': md.bid,
                    'ask': md.ask,
                    'spread': md.spread,
                    'timestamp': md.timestamp,
                    'is_live': md.is_live,
                    'volatility_score': getattr(md, 'volatility_score', None),
                    'last_update_age': getattr(md, 'last_update_age', None),
                    'regime': getattr(md, 'regime', None)
                }
        except Exception:
            continue
    return summary


def get_positions_preview(order_manager, account_id: str) -> List[Dict[str, Any]]:
    positions: List[Dict[str, Any]] = []
    try:
        trades = order_manager.get_trades(account_id)
        for t in trades or []:
            if getattr(t, 'status', None) == 'OPEN':
                positions.append({
                    'instrument': t.instrument,
                    'side': getattr(t.side, 'value', t.side),
                    'units': t.units,
                    'entry_price': t.entry_price,
                    'unrealized_pl': t.unrealized_pl
                })
    except Exception:
        pass
    return positions


def compute_portfolio_exposure(account_manager, order_manager, accounts: List[str]) -> Tuple[float, int]:
    total_balance = 0.0
    total_margin_used = 0.0
    total_positions = 0
    for account_id in accounts:
        try:
            status = account_manager.get_account_status(account_id) or {}
            total_balance += float(status.get('balance', 0.0))
            daily = order_manager.get_daily_stats(account_id) or {}
            total_margin_used += float(daily.get('margin_used', 0.0))
            total_positions += int(daily.get('open_positions', 0))
        except Exception:
            continue
    exposure = (total_margin_used / total_balance) if total_balance else 0.0
    return exposure, total_positions


def enforce_policy(account_manager, order_manager, accounts: List[str], max_exposure: float = 0.10, max_positions: int = 5) -> None:
    exposure, positions = compute_portfolio_exposure(account_manager, order_manager, accounts)
    if exposure > max_exposure:
        raise PolicyViolation(f"Portfolio exposure {exposure:.3f} exceeds cap {max_exposure:.3f}")
    if positions > max_positions:
        raise PolicyViolation(f"Open positions {positions} exceed cap {max_positions}")


def preview_close_positions(order_manager, account_id: str, instrument: str, side: str = 'buy') -> Dict[str, Any]:
    matched: List[Dict[str, Any]] = []
    try:
        trades = order_manager.get_trades(account_id)
        for t in trades or []:
            if getattr(t, 'status', None) == 'OPEN' and t.instrument.replace('_', '').lower() in [instrument.replace('_', '').lower()] and getattr(t.side, 'value', t.side).lower() == side.lower():
                matched.append({
                    'trade_id': getattr(t, 'id', None),
                    'instrument': t.instrument,
                    'side': getattr(t.side, 'value', t.side),
                    'units': t.units,
                    'entry_price': t.entry_price
                })
    except Exception:
        pass
    return {
        'instrument': instrument,
        'side': side,
        'positions_matched': len(matched),
        'orders_preview': matched
    }
