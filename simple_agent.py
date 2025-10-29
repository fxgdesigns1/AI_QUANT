#!/usr/bin/env python3
"""
Simplified AI Agent Controller for Demo Account
Runs on port 8081 with basic metrics endpoint
"""
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any
from flask import Flask, jsonify

# Simple telegram notification function
def send_message(message: str) -> None:
    """Send message to Telegram (placeholder)"""
    print(f"📱 Telegram: {message}")

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
        send_message(f"🤖 Agent started for demo account {self.account_id}")

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
                # Simulate agent activity
                self._actions_count += 1
                self._queue_depth = max(0, self._queue_depth + (1 if self._actions_count % 5 == 0 else -1))
                self._latest_summary = f"Running iteration {self._actions_count}"

                # Simulate anomaly detection
                if self._actions_count % 20 == 0:
                    self._anomalies += 1
                    self._last_error = f"Simulated anomaly at {datetime.utcnow().isoformat()}"
                    send_message(f"⚠️ Anomaly detected for agent {self.account_id}: {self._last_error}")

                time.sleep(10) # Simulate work
                backoff_seconds = 5 # Reset backoff on success

            except Exception as e:
                self._last_error = str(e)
                self._restarts += 1
                send_message(f"❌ Agent for {self.account_id} crashed. Restarting. Error: {e}")
                time.sleep(backoff_seconds)
                backoff_seconds = min(60, backoff_seconds * 2) # Exponential backoff

    def get_metrics(self) -> Dict[str, Any]:
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        return {
            "account_id": self.account_id,
            "status": "running" if self._running else "stopped",
            "uptime_seconds": round(uptime, 2),
            "uptime_human": str(timedelta(seconds=int(uptime))),
            "last_heartbeat": self._last_heartbeat.isoformat(),
            "restarts": self._restarts,
            "actions_count": self._actions_count,
            "anomalies_detected": self._anomalies,
            "queue_depth": self._queue_depth,
            "last_error": self._last_error,
            "latest_summary": self._latest_summary,
            "timestamp": datetime.utcnow().isoformat()
        }

# Flask app
app = Flask(__name__)

# Initialize agent controller
demo_account = os.getenv('AGENT_DEMO_ACCOUNT_ID', '101-004-30719775-008')
agent_controller = AgentController(demo_account)
agent_controller.start()

@app.route('/api/agent_metrics')
def get_agent_metrics():
    """Get agent metrics"""
    return jsonify(agent_controller.get_metrics())

@app.route('/')
def index():
    """Simple status page"""
    metrics = agent_controller.get_metrics()
    return f"""
    <h1>AI Trading Agent Status</h1>
    <p><strong>Account:</strong> {metrics['account_id']}</p>
    <p><strong>Status:</strong> {metrics['status']}</p>
    <p><strong>Uptime:</strong> {metrics['uptime_human']}</p>
    <p><strong>Actions:</strong> {metrics['actions_count']}</p>
    <p><strong>Restarts:</strong> {metrics['restarts']}</p>
    <p><strong>Anomalies:</strong> {metrics['anomalies_detected']}</p>
    <p><strong>Last Update:</strong> {metrics['timestamp']}</p>
    <p><a href="/api/agent_metrics">JSON API</a></p>
    """

if __name__ == '__main__':
    print("🤖 Starting AI Trading Agent Controller...")
    print(f"📊 Demo Account: {demo_account}")
    print("🌐 Server starting on port 8081...")
    app.run(host='0.0.0.0', port=8081, debug=False)
