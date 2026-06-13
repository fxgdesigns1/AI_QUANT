#!/usr/bin/env python3
"""
Phase 2 ready skeleton: production-safe trading bootstrap.
This minimal file reintroduces a production-ready path with runtime secret loading
via a Secret Manager abstraction (if available) and a local fallback to YAML configs.
"""
import argparse
import base64
from typing import Optional
from datetime import date
try:
    from .telegram_alert import send_telegram_message  # type: ignore
except Exception:
    def send_telegram_message(*args, **kwargs) -> bool:
        return False

def _load_secret_value_from_secret_manager(project_id: Optional[str], secret_name: str) -> Optional[str]:
    if not project_id:
        return None
    try:
        from google.cloud import secretmanager  # type: ignore
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        resp = client.access_secret_version(request={"name": name})
        payload = resp.payload.data
        if not payload:
            return None
        raw = payload.decode("UTF-8")
        # attempt to decode base64 if it's encoded
        try:
            import base64 as _b64
            decoded = _b64.b64decode(raw).decode("utf-8")
            return decoded
        except Exception:
            return raw
    except Exception:
        return None
import json
import logging
import os
import sys
import time
from typing import Dict, Any

# Attempt to import a secret manager integration
try:
    import sys
    base_core_path = os.path.join(os.path.dirname(__file__), "src", "core")
    if base_core_path not in sys.path:
        sys.path.insert(0, base_core_path)
    from secret_manager import get_secret_value
except Exception:
    def get_secret_value(*args, **kwargs):
        return None

# Phase 2 adapters import (local path fallback)
# (BASE_DIR is defined later in this file; move adapters import to after BASE_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
PHASE2_MODE = os.environ.get("PHASE2_MODE", "local")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_YAML_PATH = os.environ.get("ACCOUNTS_YAML_PATH", os.path.join(BASE_DIR, "src", "core", "accounts.yaml"))
PHASE2_MODE = os.environ.get("PHASE2_MODE", "legacy")
def load_accounts_from_secret_v2() -> Dict[str, Any] | None:
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        return None
    try:
        if callable(globals().get("get_secret_value")):
            secret_yaml = get_secret_value(project_id, "ACCOUNTS_YAML", "latest")
            if secret_yaml:
                import yaml, tempfile
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".yaml") as tf:
                    tf.write(secret_yaml)
                    tf.flush()
                    return load_accounts(tf.name)
        return None
    except Exception as exc:
        logging.error(f"Secret-based accounts load failed (v2): {exc}")
        return None
ADAPTERS_PATH = os.path.join(BASE_DIR, "src", "adapters")
if ADAPTERS_PATH not in __import__("sys").path:
    __import__("sys").path.insert(0, ADAPTERS_PATH)
try:
    from price_feed import fetch_prices_for_accounts as cloud_price_fetch
    from news_feed import fetch_latest_news as cloud_news_fetch
    from order_interface import place_order as cloud_place_order
except Exception:
    cloud_price_fetch = None
    cloud_news_fetch = None
    cloud_place_order = None
# Phase 2 adapters: local fallback path
ADAPTERS_PATH = os.path.join(BASE_DIR, "src", "adapters")
if ADAPTERS_PATH not in sys.path:
    sys.path.insert(0, ADAPTERS_PATH)
try:
    from price_feed import fetch_prices_for_accounts as cloud_price_fetch
    from news_feed import fetch_latest_news as cloud_news_fetch
    from order_interface import place_order as cloud_place_order
except Exception:
    cloud_price_fetch = None
    cloud_news_fetch = None
    cloud_place_order = None
def update_dashboard_status_atomic(status: Dict[str, Any]) -> None:
    """Write status.json atomically to the dashboard directory to avoid partial writes"""
    from pathlib import Path
    import json
    import tempfile
    status_dir = Path(BASE_DIR) / "dashboard"
    status_path = status_dir / "status.json"
    status_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=str(status_dir), suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(status, tmp)
        tmp_path = tmp.name
    Path(status_path).parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp_path, status_path)

_DAILY_REPORT_PATH = os.path.join(BASE_DIR, "daily_report_last_date.txt")

def maybe_send_daily_report(cycle: int, cycles: int, accounts: list[str]):
    """Send a lightweight daily report via Telegram for PAPER runs."""
    try:
        today = date.today().isoformat()
        last_sent = None
        if os.path.exists(_DAILY_REPORT_PATH):
            with open(_DAILY_REPORT_PATH, "r", encoding="utf-8") as f:
                last_sent = f.read().strip()
        if last_sent != today:
            msg = f"Daily PAPER report {today}: cycle {cycle}/{cycles}, accounts={accounts}"
            try:
                send_telegram_message(msg)
            except Exception:
                pass
            with open(_DAILY_REPORT_PATH, "w", encoding="utf-8") as f:
                f.write(today)
    except Exception:
        pass


def load_accounts_from_secret() -> Dict[str, Any] | None:
    project_id = os.environ.get("GCP_PROJECT_ID")
    # Local seed support for testing without GCP
    if not project_id:
        secret_json = os.environ.get("SECRET_PAYLOAD_JSON")
        if secret_json:
            try:
                import json
                data = json.loads(secret_json)
                return data
            except Exception as exc:
                logging.error(f"LOCAL SECRET JSON load failed: {exc}")
                return None
        return None
    # If GCP project is provided, fetch from Secret Manager
    if not callable(get_secret_value):
        return None
    try:
        secret_yaml = get_secret_value(project_id, "ACCOUNTS_YAML", "latest")
        if secret_yaml:
            try:
                import yaml
                return yaml.safe_load(secret_yaml) or {}
            except Exception as exc:
                logging.error(f"Secret YAML parse failed: {exc}")
                return None
        # Fallback to an alternate secret that may contain plain JSON
        secret_json = None
        try:
            secret_json = get_secret_value(project_id, "ACCOUNTS_JSON", "latest")
        except Exception:
            secret_json = None
        if secret_json:
            import json
            try:
                return json.loads(secret_json)
            except Exception as exc:
                logging.error(f"Secret JSON parse failed: {exc}")
                return None
        return None
    except Exception as exc:
        logging.error(f"Secret-based accounts load failed: {exc}")
        return None


def load_accounts(path: str) -> Dict[str, Any]:
    # Phase 2: attempt new secret loader (runtime Secret Manager) if Phase 2 is cloud-enabled
    if PHASE2_MODE == "cloud":
        secret_accounts = load_accounts_from_secret_v2()
        if secret_accounts is not None:
            return secret_accounts
    if not path or not os.path.exists(path):
        logging.warning(f"Accounts YAML not found at {path}; continuing with empty accounts.")
        return {}
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        logging.error(f"Failed to load accounts: {exc}")
        return {}
def ensure_old_install_isolated():
    # Create a guard folder to keep legacy/install separate
    old_dir = Path(BASE_DIR) / "old_install"
    old_dir.mkdir(parents=True, exist_ok=True)
    marker = old_dir / "README.md"
    if not marker.exists():
        marker.write_text("# Legacy install isolated\nThis folder is kept for reference and must not be used by Phase 2.", encoding="utf-8")

def load_accounts_from_secret_v2() -> Dict[str, Any] | None:
    """
    Phase 2 local/global secret loader (Google Secret Manager or local seed).
    Priority: GCP Secret Manager, then SECRET_PAYLOAD_JSON, then None.
    """
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        secret_json = os.environ.get("SECRET_PAYLOAD_JSON")
        if secret_json:
            try:
                import json
                return json.loads(secret_json)
            except Exception as exc:
                logging.error(f"LOCAL SECRET JSON load failed: {exc}")
                return None
        return None
    try:
        from google.cloud import secretmanager  # type: ignore
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/ACCOUNTS_YAML/versions/latest"
        resp = client.access_secret_version(request={"name": name})
        payload = resp.payload.data.decode("UTF-8")
        import yaml
        return yaml.safe_load(payload) if payload else {}
    except Exception as exc:
        logging.error(f"Secret-based accounts load failed (v2): {exc}")
        return None


def run_trading_loop(accounts: Dict[str, Any], cycles: int = 2, local_mock: bool = False) -> int:
    logging.info("Starting production-like cloud trading loop (Phase 2).")
    # Support: paper trading with live price feed (live data, paper trades)
    live_price_enabled = os.environ.get("LIVE_PRICE_DATA", "false").lower() == "true"
    LIVE_TRADING_ENABLED = os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true"
    LIVE_NEWS_ENABLED = os.environ.get("LIVE_NEWS_DATA", "false").lower() == "true"
    price_provider = None
    if live_price_enabled:
        try:
            from .price_feed_factory import create_price_feed_provider  # type: ignore
            price_provider = create_price_feed_provider()
        except Exception:
            price_provider = None

    if local_mock:
        # Phase 2 local mock path
        mock_accounts = accounts or {
            "acc-1": {"symbols": ["EURUSD"]},
            "acc-2": {"symbols": ["GBPUSD", "EURUSD"]},
            "acc-3": {"symbols": ["XAUUSD"]},
        }
        base_prices = {"EURUSD": 1.08, "GBPUSD": 1.25, "XAUUSD": 1900.0}
        for cycle in range(1, cycles + 1):
            logging.info(f"Cycle {cycle}/{cycles} [MOCK] started.")
            # Attempt to fetch live-like prices from adapter if available
            prices = {}
            if live_price_enabled and price_provider is not None:
                # Use live price feed for paper trading (no real orders)
                for acc, cfg in (mock_accounts or {}).items():
                    acc_prices = {sym: price_provider.get_latest_price(sym) for sym in cfg.get("symbols", [])}
                    prices[acc] = acc_prices
            # Fetch live news if enabled (independent of price path)
            if LIVE_NEWS_ENABLED and 'cloud_news_fetch' in globals():
                try:
                    # Try with accounts first, if supported
                    news = cloud_news_fetch(mock_accounts)
                except TypeError:
                    # Fallback to no-args version if the function signature does not accept parameters
                    try:
                        news = cloud_news_fetch()
                    except Exception as exc:
                        logging.error(f"MOCK: News fetch failed (no-args): {exc}")
                        news = None
                except Exception as exc:
                    logging.error(f"MOCK: News fetch failed: {exc}")
                else:
                    logging.debug(f"Live news fetched for MOCK: {news is not None}")
            else:
                if cloud_price_fetch:
                    try:
                        prices = cloud_price_fetch(mock_accounts)
                    except Exception as exc:
                        logging.error(f"Adapter price fetch failed: {exc}")
                if not prices:
                    prices = {}
                    for acc, cfg in (mock_accounts or {}).items():
                        acc_prices = {sym: base_prices.get(sym, 1.0) for sym in cfg.get("symbols", [])}
                        prices[acc] = acc_prices
            # Signals per account
            signals = {acc: "mock_strategy" for acc in mock_accounts}
            active_strategy = next(iter(signals.values()), "mock_strategy")
            if cloud_place_order:
                if live_price_enabled and LIVE_TRADING_ENABLED:
                    for acc, sig in signals.items():
                        try:
                            placed = cloud_place_order(acc, sig)
                            if placed:
                                # You can wire a real notifier here later
                                pass
                        except Exception as exc:
                            logging.error(f"MOCK: Order placement failed for {acc}: {exc}")
                else:
                    logging.info("Trading disabled: LIVE_PRICE_DATA is enabled but LIVE_TRADING_ENABLED is not set.")
            # Update dashboard with status
            if live_price_enabled:
                mode_label = "LIVE_PRICE_ONLY" if not LIVE_TRADING_ENABLED else "LIVE_TRADING"
            else:
                mode_label = "MOCK"
            status = {
                "mode": mode_label,
                "cycle": cycle,
                "cycles": cycles,
                "accounts": list(mock_accounts.keys()),
                "active_strategy": active_strategy,
                "timestamp": int(time.time())
            }
            update_dashboard_status_atomic(status)
            # Daily paper-trading report
            if 'mock_accounts' in locals():
                maybe_send_daily_report(cycle, cycles, list(mock_accounts.keys()))
            # Optional: notify on MOCK cycle completion
            if mode_label.startswith("MOCK"):
                try:
                    from datetime import datetime
                    msg = f"MOCK Cycle {cycle}/{cycles} completed at {datetime.utcnow().isoformat()}Z"
                    send_telegram_message(msg)
                except Exception as exc:
                    logging.debug(f"Telegram alert skipped: {exc}")
            time.sleep(0.2)
            logging.info(f"Cycle {cycle}/{cycles} [MOCK] completed.")
        logging.info("Trading loop finished. [MOCK]")
        return 0
    if not accounts:
        logging.info("No accounts configured; nothing to run.")
        return 0
    for cycle in range(1, cycles + 1):
        logging.info(f"Cycle {cycle}/{cycles} started.")
        # placeholder real data flow
        time.sleep(0.2)
        logging.info(f"Cycle {cycle}/{cycles} completed.")
    logging.info("Trading loop finished.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 2: production-ready bootstrap (cloud).")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "health", "version"], help="Command to execute")
    parser.add_argument("--local-mock", action="store_true", help="Run in local mock mode for quick tests")
    parser.add_argument("--cycles", type=int, default=2, help="Number of MOCK cycles to run")
    parser.add_argument("--test-secrets", action="store_true", help="Test Secret Manager integration and output results")
    args = parser.parse_args()

    if args.command == "health":
        logging.info("Health check: OK (Phase 2 skeleton)")
        return 0
    if args.command == "version":
        print("cloud_declutter_v2 planned deployment bootstrap Phase 2 skeleton")
        return 0
    if args.test_secrets:
        try:
            # Attempt to test secret loading integration (non-destructive)
            data = None
            project_id = os.environ.get("GCP_PROJECT_ID")
            if project_id:
                data = load_accounts_from_secret_v2()
            print({"secret_loader_test": {"project": project_id, "result": data}})
        except Exception as exc:
            print({"secret_loader_test": {"error": str(exc)}})
        return 0

    accounts = load_accounts(ACCOUNTS_YAML_PATH)
    return run_trading_loop(accounts, cycles=args.cycles, local_mock=args.local_mock)


if __name__ == "__main__":
    sys.exit(main())


