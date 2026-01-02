# src/core/execution_gate.py

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v.strip() if v is not None else default


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class GateDecision:
    mode: str  # "paper" | "live"
    allowed: bool
    reason: str


class ExecutionGate:
    """Centralized execution gate.

    SAFE by default:
      - Paper mode unless explicit dual-enable for live.
      - Kill switch hard-blocks.

    Env vars:
      - TRADING_MODE=paper|live (default: paper)
      - LIVE_TRADING=true (must be true to allow live)
      - LIVE_TRADING_CONFIRM=true (second toggle)
      - KILL_SWITCH=true (blocks everything)
      - RUN_ID (optional) - propagated into logs
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or _env_str("RUN_ID", "") or f"run_{uuid.uuid4().hex[:12]}"

    def decision(self) -> GateDecision:
        if _env_bool("KILL_SWITCH", False):
            return GateDecision(mode="paper", allowed=False, reason="KILL_SWITCH=true")

        mode = _env_str("TRADING_MODE", "paper").lower()
        if mode not in ("paper", "live"):
            mode = "paper"

        if mode == "live":
            a = _env_bool("LIVE_TRADING", False)
            b = _env_bool("LIVE_TRADING_CONFIRM", False)
            if not (a and b):
                return GateDecision(mode="paper", allowed=True, reason="live_requested_but_not_dual_enabled")
            return GateDecision(mode="live", allowed=True, reason="live_dual_enabled")

        return GateDecision(mode="paper", allowed=True, reason="paper_default")

    def _log(self, event: str, payload: Dict[str, Any]) -> None:
        rec = {
            "ts_ms": _now_ms(),
            "run_id": self.run_id,
            "event": event,
            **payload,
        }
        print(json.dumps(rec, sort_keys=True))

    def place_market_order(
        self,
        *,
        instrument: str,
        units: int,
        account_id: str,
        exec_fn: Callable[[], Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Any:
        meta = meta or {}
        d = self.decision()

        self._log(
            "execution_gate_decision",
            {
                "mode": d.mode,
                "allowed": d.allowed,
                "reason": d.reason,
                "instrument": instrument,
                "units": units,
                "account_id": account_id,
                "meta": meta,
            },
        )

        if not d.allowed:
            raise RuntimeError(f"Execution blocked by gate: {d.reason}")

        if d.mode != "live":
            # Paper: do NOT execute broker call; return a simulated result
            sim = {
                "ok": True,
                "paper": True,
                "instrument": instrument,
                "units": units,
                "account_id": account_id,
                "run_id": self.run_id,
                "ts_ms": _now_ms(),
                "meta": meta,
            }
            self._log("paper_order_simulated", sim)
            return sim

        # Live: execute
        try:
            result = exec_fn()
            self._log(
                "live_order_executed",
                {
                    "instrument": instrument,
                    "units": units,
                    "account_id": account_id,
                    "meta": meta,
                    "result_type": type(result).__name__,
                },
            )
            return result
        except Exception as e:
            self._log(
                "live_order_failed",
                {
                    "instrument": instrument,
                    "units": units,
                    "account_id": account_id,
                    "meta": meta,
                    "error": repr(e),
                },
            )
            raise
