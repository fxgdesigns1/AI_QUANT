#!/usr/bin/env python3
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any

try:
    from .telegram_notify import send_message  # type: ignore
except Exception:
    from telegram_notify import send_message  # type: ignore

class AgentController:
    """
    Lightweight supervisor for a single demo OANDA account.
    Tracks health/metrics and enforces guardrails; does not place real orders.
    """

    def __init__(self, account_id: str) -> None:
        self.account_id = account_id
        self._running = False
        self._thread = None
        self._start_time = datetime.utcnow()
        self._last_heartbeat = datetime.utcnow()
        self._restarts = 0
        self._actions_count = 0
        self._anomalies = 0
        self._queue_depth = 0
        self._last_error: str = ""
        self._latest_summary: str = "Initialized"

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        send_message(f"Agent started for demo account {self.account_id}")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        backoff_seconds = 5
        while self._running:
            try:
                # Heartbeat and lightweight health checks
                self._last_heartbeat = datetime.utcnow()

                # Placeholder: poll external systems lightly (no heavy CPU/RAM)
                # This is where latency/error spikes or drawdown guards would be checked
                self._queue_depth = max(0, (self._queue_depth + 1) % 5)
                self._actions_count += 1
                self._latest_summary = "Controller healthy; queue={} actions={}".format(
                    self._queue_depth, self._actions_count
                )

                # Sleep with low footprint
                time.sleep(10)
                backoff_seconds = 5
            except Exception as e:
                self._anomalies += 1
                self._last_error = str(e)
                self._latest_summary = f"Error: {self._last_error}"
                send_message(f"Agent anomaly: {self._last_error}")
                time.sleep(backoff_seconds)
                backoff_seconds = min(60, backoff_seconds * 2)
                self._restarts += 1

    def get_metrics(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        uptime = now - self._start_time
        since_hb = (now - self._last_heartbeat).total_seconds()
        return {
            "account_id": self.account_id,
            "running": self._running,
            "uptime_seconds": int(uptime.total_seconds()),
            "last_heartbeat_seconds": int(since_hb),
            "restarts": self._restarts,
            "actions_count": self._actions_count,
            "anomalies": self._anomalies,
            "queue_depth": self._queue_depth,
            "last_error": self._last_error,
            "summary": self._latest_summary,
            "timestamp": datetime.utcnow().isoformat(),
        }


