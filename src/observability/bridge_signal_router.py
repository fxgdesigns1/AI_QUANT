"""
Bridge signal router: fanout to multiple MT5 terminals with dedupe.
- Loads bridge_accounts.json for routing_rules and account config
- Writes signals to per-account signal files (signals_prop_02.jsonl, signals_citytraders.jsonl)
- File-based dedupe: logs/dedupe/<account_id>/<signal_id>.done prevents double execution
- Keeps backwards compat: logs/signals.jsonl when no fanout
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LOGS_BASE = os.path.expanduser("~/gcloud-system/logs")
SIGNALS_DEFAULT = os.path.join(LOGS_BASE, "signals.jsonl")
DEDUPE_BASE = os.path.join(LOGS_BASE, "dedupe")

_config_cache: Optional[Dict] = None
_config_lock = threading.Lock()


def _load_bridge_config() -> Dict:
    """Load bridge_accounts.json (cached)."""
    global _config_cache
    with _config_lock:
        if _config_cache is not None:
            return _config_cache
        cfg_path = Path(__file__).resolve().parents[2] / "configs" / "bridge_accounts.json"
        if not cfg_path.exists():
            _config_cache = {"accounts": [], "routing_rules": {}, "master_feed": {}}
            return _config_cache
        try:
            with open(cfg_path, "r") as f:
                _config_cache = json.load(f)
            return _config_cache
        except Exception as e:
            logger.warning(f"Failed to load bridge config: {e}")
            _config_cache = {"accounts": [], "routing_rules": {}, "master_feed": {}}
            return _config_cache


def _get_account_by_id(account_id: str) -> Optional[Dict]:
    cfg = _load_bridge_config()
    for a in cfg.get("accounts", []):
        if (a.get("id") or a.get("account_id")) == account_id:
            return a
    return None


def _get_fanout_targets() -> List[str]:
    """Return list of enabled account ids for fanout."""
    cfg = _load_bridge_config()
    rules = cfg.get("routing_rules") or cfg.get("fanout") or {}
    if not rules.get("fanout_enabled", rules.get("enabled", False)):
        return []
    targets = rules.get("fanout_targets") or rules.get("targets") or []
    accounts = {a.get("id") or a.get("account_id"): a for a in cfg.get("accounts", [])}
    return [t for t in targets if accounts.get(t, {}).get("enabled", False)]


def _signal_file_for_account(account_id: str) -> Optional[str]:
    """Return full path to signal file for account."""
    acc = _get_account_by_id(account_id)
    if not acc:
        return None
    fname = acc.get("mt5_signal_file") or "signals.jsonl"
    return os.path.join(LOGS_BASE, fname)


def _ensure_dedupe_dir(account_id: str) -> None:
    """Ensure dedupe dir exists so EA can write .done files when it processes."""
    dedupe_dir = os.path.join(DEDUPE_BASE, account_id)
    try:
        os.makedirs(dedupe_dir, exist_ok=True)
    except OSError as e:
        logger.warning(f"Dedupe dir failed for {account_id}: {e}")


def is_signal_processed(account_id: str, signal_id: str) -> bool:
    """Check if signal_id was already processed (EA wrote .done file)."""
    lock_path = os.path.join(DEDUPE_BASE, account_id, f"{signal_id}.done")
    return os.path.exists(lock_path)


def emit_signal(
    strategy: str,
    symbol: str,
    side: str,
    units: int,
    bridge_account: Optional[str] = None,
    signal_file_override: Optional[str] = None,
    fanout: bool = False,
    entry_type: str = "MARKET",
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    confidence: float = 0.0,
    execution_allowed: bool = False,
    meta: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Optional[str]:
    """
    Emit a signal to bridge account(s).
    - If fanout=True: write to all enabled fanout targets' signal files
    - If signal_file_override: write only to that file (for testing)
    - Else if bridge_account: write to that account's mt5_signal_file
    - Else: write to default signals.jsonl (backwards compat)
    Returns signal_id on success.
    """
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    signal_id = str(uuid.uuid4())

    signal_data = {
        "signal_id": signal_id,
        "timestamp_utc": timestamp_utc,
        "system": "ALPHA",
        "strategy": strategy,
        "symbol": symbol,
        "side": side,
        "units": units,
        "entry_type": entry_type,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": confidence,
        "execution_allowed": execution_allowed,
        "bridge_account": bridge_account,
        "account": kwargs.get("account", "unknown"),
        "regime": kwargs.get("regime", "unknown"),
        "session": kwargs.get("session", "unknown"),
        "news_state": kwargs.get("news_state", "unknown"),
        "block_reason": kwargs.get("block_reason"),
    }
    if meta:
        signal_data["meta"] = {k: v for k, v in meta.items() if k not in signal_data}

    json_line = json.dumps(signal_data)
    files_to_write: List[tuple[str, str]] = []  # (file_path, account_id)

    if signal_file_override:
        files_to_write.append((os.path.abspath(signal_file_override), "override"))
    elif fanout:
        targets = _get_fanout_targets()
        for acc_id in targets:
            path = _signal_file_for_account(acc_id)
            if path:
                files_to_write.append((path, acc_id))
        if not files_to_write:
            path = SIGNALS_DEFAULT
            files_to_write.append((path, "default"))
    elif bridge_account:
        path = _signal_file_for_account(bridge_account)
        if path:
            files_to_write.append((path, bridge_account))
        else:
            files_to_write.append((SIGNALS_DEFAULT, bridge_account))
    else:
        files_to_write.append((SIGNALS_DEFAULT, "default"))

    try:
        os.makedirs(LOGS_BASE, exist_ok=True)
        for file_path, acc_id in files_to_write:
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")
                if acc_id not in ("override", "default"):
                    _ensure_dedupe_dir(acc_id)
            except OSError as e:
                logger.error(f"Failed to write signal to {file_path}: {e}")
        return signal_id
    except Exception as e:
        logger.error(f"Bridge signal emit failed: {e}")
        return None
