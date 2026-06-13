"""Maintenance-only MT5 control actions (Windows MetaTrader5 Python API).

All functions return structured dicts; callers must enforce SIDECAR_ENABLE_WRITE_ACTIONS.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from .config import SIDECAR_CONTROL_AUDIT_LOG_PATH
from .mt5_client import get_mt5, initialize_mt5


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _audit(record: dict[str, Any]) -> None:
    record = {**record, "ts_utc": record.get("ts_utc") or _utc_now()}
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    path = (SIDECAR_CONTROL_AUDIT_LOG_PATH or "").strip()
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)


def _ensure_mt5() -> tuple[Any | None, dict[str, Any]]:
    mt5 = get_mt5()
    if not mt5:
        return None, {
            "action": "mt5_init",
            "attempted": False,
            "success": False,
            "mt5_retcodes": [],
            "messages": ["MetaTrader5 package not installed"],
            "ts_utc": _utc_now(),
        }
    ok, code, msg = initialize_mt5()
    if not ok:
        return None, {
            "action": "mt5_init",
            "attempted": True,
            "success": False,
            "mt5_retcodes": [code] if code is not None else [],
            "messages": [msg or "MT5 initialize failed"],
            "ts_utc": _utc_now(),
        }
    return mt5, {}


def _resolve_filling(mt5, symbol: str) -> int:
    """Map symbol filling_mode bitmask to ORDER_FILLING_* (SYMBOL_FILLING_* not exposed on all mt5 builds)."""
    info = mt5.symbol_info(symbol)
    if not info:
        return mt5.ORDER_FILLING_IOC
    fm = int(getattr(info, "filling_mode", 0) or 0)
    # MQL5: SYMBOL_FILLING_FOK=1, IOC=2, RETURN=4
    _fo_k, _ioc, _ret = 1, 2, 4
    if fm & _fo_k:
        return mt5.ORDER_FILLING_FOK
    if fm & _ioc:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def _order_send_result_dict(r: Any) -> tuple[int | None, str]:
    if r is None:
        return None, "order_send returned None"
    ret = getattr(r, "retcode", None)
    comment = getattr(r, "comment", None) or ""
    return (int(ret) if ret is not None else None, comment or str(r))


def close_position(ticket: int, record_audit: bool = True) -> dict[str, Any]:
    action = "close_position"
    ts = _utc_now()
    mt5, err = _ensure_mt5()
    if not mt5:
        out = {**err, "action": action, "attempted": False, "tickets_touched": []}
        if record_audit:
            _audit({"audit_kind": "control_action", **out})
        return out

    attempted = True
    tickets_touched: list[int] = []
    retcodes: list[int] = []
    messages: list[str] = []

    if hasattr(mt5, "ClosePosition"):
        r = mt5.ClosePosition(int(ticket))
        rc, msg = _order_send_result_dict(r)
        if rc is not None:
            retcodes.append(rc)
        messages.append(msg)
        tickets_touched.append(int(ticket))
        ok = r is not None and getattr(r, "retcode", None) == mt5.TRADE_RETCODE_DONE
        out = {
            "action": action,
            "attempted": attempted,
            "success": ok,
            "tickets_touched": tickets_touched,
            "mt5_retcodes": retcodes,
            "messages": messages,
            "ts_utc": ts,
        }
        if record_audit:
            _audit({"audit_kind": "control_action", **out})
        return out

    positions = mt5.positions_get(ticket=int(ticket))
    if not positions:
        out = {
            "action": action,
            "attempted": attempted,
            "success": True,
            "tickets_touched": [],
            "mt5_retcodes": [],
            "messages": [f"No open position for ticket {ticket}"],
            "ts_utc": ts,
        }
        if record_audit:
            _audit({"audit_kind": "control_action", **out})
        return out

    pos = positions[0]
    tick = mt5.symbol_info_tick(pos.symbol)
    if not tick:
        err_t = mt5.last_error()
        out = {
            "action": action,
            "attempted": attempted,
            "success": False,
            "tickets_touched": [],
            "mt5_retcodes": [err_t[0]] if err_t and err_t[0] is not None else [],
            "messages": [f"No tick for {pos.symbol}: {err_t}"],
            "ts_utc": ts,
        }
        if record_audit:
            _audit({"audit_kind": "control_action", **out})
        return out

    if pos.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = float(tick.bid)
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = float(tick.ask)

    filling = _resolve_filling(mt5, pos.symbol)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": float(pos.volume),
        "type": order_type,
        "position": int(ticket),
        "price": price,
        "deviation": 50,
        "magic": int(getattr(pos, "magic", 0) or 0),
        "comment": "windows_sidecar_control",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }
    r = mt5.order_send(request)
    rc, msg = _order_send_result_dict(r)
    if rc is not None:
        retcodes.append(rc)
    messages.append(msg)
    tickets_touched.append(int(ticket))
    ok = r is not None and getattr(r, "retcode", None) == mt5.TRADE_RETCODE_DONE
    out = {
        "action": action,
        "attempted": attempted,
        "success": ok,
        "tickets_touched": tickets_touched,
        "mt5_retcodes": retcodes,
        "messages": messages,
        "ts_utc": ts,
    }
    if record_audit:
        _audit({"audit_kind": "control_action", **out})
    return out


def close_all_positions() -> dict[str, Any]:
    action = "close_all_positions"
    ts = _utc_now()
    mt5, err = _ensure_mt5()
    if not mt5:
        out = {**err, "action": action, "tickets_touched": [], "orders_touched": []}
        _audit({"audit_kind": "control_action", **out})
        return out

    tickets_touched: list[int] = []
    retcodes: list[int] = []
    messages: list[str] = []
    attempted = True
    poses = list(mt5.positions_get() or [])
    if not poses:
        out = {
            "action": action,
            "attempted": attempted,
            "success": True,
            "tickets_touched": [],
            "mt5_retcodes": [],
            "messages": ["No open positions"],
            "ts_utc": ts,
        }
        _audit({"audit_kind": "control_action", **out})
        return out

    poses_sorted = sorted(poses, key=lambda p: int(getattr(p, "ticket", 0)))
    all_ok = True
    for pos in poses_sorted:
        t = int(pos.ticket)
        sub = close_position(t, record_audit=False)
        tickets_touched.extend(sub.get("tickets_touched") or [])
        retcodes.extend(sub.get("mt5_retcodes") or [])
        messages.extend(sub.get("messages") or [])
        if not sub.get("success"):
            all_ok = False
        time.sleep(0.05)

    out = {
        "action": action,
        "attempted": attempted,
        "success": all_ok,
        "tickets_touched": tickets_touched,
        "mt5_retcodes": retcodes,
        "messages": messages,
        "ts_utc": _utc_now(),
    }
    _audit({"audit_kind": "control_action", **out})
    return out


def cancel_order(ticket: int, record_audit: bool = True) -> dict[str, Any]:
    action = "cancel_order"
    ts = _utc_now()
    mt5, err = _ensure_mt5()
    if not mt5:
        out = {
            **err,
            "action": action,
            "attempted": False,
            "orders_touched": [],
        }
        if record_audit:
            _audit({"audit_kind": "control_action", **out})
        return out

    attempted = True
    orders_touched: list[int] = []
    retcodes: list[int] = []
    messages: list[str] = []

    existing = mt5.orders_get(ticket=int(ticket))
    if not existing:
        out = {
            "action": action,
            "attempted": attempted,
            "success": True,
            "orders_touched": [],
            "mt5_retcodes": [],
            "messages": [f"No pending order for ticket {ticket}"],
            "ts_utc": ts,
        }
        if record_audit:
            _audit({"audit_kind": "control_action", **out})
        return out

    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": int(ticket),
    }
    r = mt5.order_send(request)
    rc, msg = _order_send_result_dict(r)
    if rc is not None:
        retcodes.append(rc)
    messages.append(msg)
    orders_touched.append(int(ticket))
    ok = r is not None and getattr(r, "retcode", None) == mt5.TRADE_RETCODE_DONE

    out = {
        "action": action,
        "attempted": attempted,
        "success": ok,
        "orders_touched": orders_touched,
        "mt5_retcodes": retcodes,
        "messages": messages,
        "ts_utc": ts,
    }
    if record_audit:
        _audit({"audit_kind": "control_action", **out})
    return out


def cancel_all_orders() -> dict[str, Any]:
    action = "cancel_all_orders"
    ts = _utc_now()
    mt5, err = _ensure_mt5()
    if not mt5:
        out = {**err, "action": action, "orders_touched": []}
        _audit({"audit_kind": "control_action", **out})
        return out

    orders_touched: list[int] = []
    retcodes: list[int] = []
    messages: list[str] = []
    attempted = True
    ords = list(mt5.orders_get() or [])
    if not ords:
        out = {
            "action": action,
            "attempted": attempted,
            "success": True,
            "orders_touched": [],
            "mt5_retcodes": [],
            "messages": ["No pending orders"],
            "ts_utc": ts,
        }
        _audit({"audit_kind": "control_action", **out})
        return out

    ords_sorted = sorted(ords, key=lambda o: int(getattr(o, "ticket", 0)))
    all_ok = True
    for o in ords_sorted:
        t = int(o.ticket)
        sub = cancel_order(t, record_audit=False)
        orders_touched.extend(sub.get("orders_touched") or [])
        retcodes.extend(sub.get("mt5_retcodes") or [])
        messages.extend(sub.get("messages") or [])
        if not sub.get("success"):
            all_ok = False
        time.sleep(0.05)

    out = {
        "action": action,
        "attempted": attempted,
        "success": all_ok,
        "orders_touched": orders_touched,
        "mt5_retcodes": retcodes,
        "messages": messages,
        "ts_utc": _utc_now(),
    }
    _audit({"audit_kind": "control_action", **out})
    return out


def flatten_all() -> dict[str, Any]:
    """Close all positions first, then cancel all pending orders (deterministic order)."""
    pos_phase = close_all_positions()
    ord_phase = cancel_all_orders()
    success = bool(pos_phase.get("success")) and bool(ord_phase.get("success"))
    out: dict[str, Any] = {
        "action": "flatten_all",
        "attempted": True,
        "success": success,
        "tickets_touched": list(pos_phase.get("tickets_touched") or []),
        "orders_touched": list(ord_phase.get("orders_touched") or []),
        "mt5_retcodes": list(pos_phase.get("mt5_retcodes") or [])
        + list(ord_phase.get("mt5_retcodes") or []),
        "messages": list(pos_phase.get("messages") or []) + list(ord_phase.get("messages") or []),
        "positions_phase": pos_phase,
        "orders_phase": ord_phase,
        "ts_utc": _utc_now(),
    }
    _audit({"audit_kind": "control_action", **out})
    return out