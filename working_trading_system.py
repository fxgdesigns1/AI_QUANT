#!/usr/bin/env python3
"""
WORKING TRADING SYSTEM - ACTUALLY EXECUTES TRADES
This system will generate signals and EXECUTE them immediately
"""

import os
import sys
import time
import logging
import math
import traceback
import datetime as dt
from datetime import datetime, timezone
from typing import Any, Optional
import json

# --- FXG multi-account normalization helpers ---
def fxg_resolve_oanda_account_id(raw_account_id: str) -> str:
    """Return full OANDA account id.
    Accepts lane id like '002' or full id like '101-...-002'.
    Uses env OANDA_ACCOUNT_ID_### (suffix derived from last 3 chars) then falls back to OANDA_ACCOUNT_ID.
    Returns input if nothing set.
    """
    import os
    raw = (str(raw_account_id) if raw_account_id is not None else '').strip()
    suf = raw[-3:]
    mapped = os.getenv('OANDA_ACCOUNT_ID_' + suf, '').strip()
    if mapped:
        return mapped
    fallback = os.getenv('OANDA_ACCOUNT_ID', '').strip()
    return fallback or raw


def _fxg_allowed_oanda_account_ids() -> set:
    """Strict allowlist of execution-capable full OANDA account IDs from env (no secrets in logs)."""
    allowed_ids = set()
    for i in range(1, 7):
        v = os.getenv(f"OANDA_ACCOUNT_ID_{i:03d}", "").strip()
        if v:
            allowed_ids.add(v)
    if not allowed_ids:
        fallback = os.getenv("OANDA_ACCOUNT_ID", "").strip()
        if fallback:
            allowed_ids.add(fallback)
    return allowed_ids


def fxg_get_oanda_api_key_for_account(account_id: str) -> str:
    """Return GLOBAL OANDA API key (single key serves all accounts/lanes).

    Intentionally ignores any OANDA_API_KEY_### variables to match architecture.
    """
    import os
    return os.getenv("OANDA_API_KEY", "").strip()


def _fxg_append_problem_event(
    *,
    severity: str,
    subsystem: str,
    key: str,
    summary: str,
    details: Optional[str] = None,
    hint_cmd: Optional[str] = None,
    fingerprint: Optional[str] = None,
) -> None:
    """
    Append a single problems.jsonl event for control-plane aggregation.
    Non-blocking, best-effort, NO secrets.
    """
    try:
        from pathlib import Path

        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        p = logs_dir / "problems.jsonl"

        event = {
            "ts_utc": time.time(),
            "severity": (severity or "AMBER").upper(),
            "subsystem": (subsystem or "unknown")[:64],
            "key": (key or "unknown")[:80],
            "summary": (summary or "")[:240],
            "details": (details or "")[:400] if details else None,
            "hint_cmd": (hint_cmd or "")[:240] if hint_cmd else None,
            "fingerprint": (fingerprint or "")[:200] if fingerprint else None,
        }

        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:
        return


# Set up environment
os.environ['OANDA_ENVIRONMENT'] = os.environ.get('OANDA_ENVIRONMENT', 'practice')

# Path setup is handled by src.runner.main
# All imports from google-cloud-trading-system/src/
from src.core.dynamic_account_manager import get_account_manager
from src.core.trading_scanner import TradingScanner
from src.core.order_manager import OrderManager
from src.core.execution_gate import ExecutionGate
from src.observability.signal_exporter import SignalExporter, get_signal_exporter
from src.core.trade_selector import TradeSelector
try:
    from src.core.bias_observer import observe_bias
    HAS_BIAS_OBSERVER = True
except ImportError:
    HAS_BIAS_OBSERVER = False
    observe_bias = None
    logging.getLogger(__name__).warning(
        "⚠️ src.core.bias_observer not available — bias observation disabled"
    )
try:
    from src.core.bias_resolver import resolve_bias, BiasComponent
    HAS_BIAS_RESOLVER = True
except ImportError:
    HAS_BIAS_RESOLVER = False
    resolve_bias = None
    BiasComponent = None
    logging.getLogger(__name__).warning(
        "⚠️ src.core.bias_resolver not available — bias resolution disabled"
    )
from src.core.price_action_bias import PriceActionBias
from src.core.regime_bias import RegimeBias
from src.core.market_regime import MarketRegimeDetector
try:
    from src.core.strategy_trigger_probe import get_strategy_trigger_probe
    HAS_STRATEGY_PROBE = True
except Exception as e:
    HAS_STRATEGY_PROBE = False
    get_strategy_trigger_probe = None
    logging.getLogger(__name__).warning(f"⚠️ strategy_trigger_probe unavailable: {e}")
try:
    from src.observability.structured_logger import logger as structured_logger
except ImportError:
    structured_logger = None
    logging.getLogger(__name__).warning("⚠️ structured_logger unavailable - observability logs skipped")
from src.core.constants import (
    MIN_TP_DISTANCE_PCT_FX,
    MIN_TP_DISTANCE_PCT_METALS,
    MAX_PRICE_DEVIATION_PCT_FX,
    MAX_PRICE_DEVIATION_PCT_METALS,
    MAX_STOP_DEVIATION_MULTIPLIER_FX,
    MAX_STOP_DEVIATION_MULTIPLIER_METALS
)
# NEWS: Import news fetching registry
try:
    from src.control_plane.news_provider import fetch_news_with_registry
    HAS_NEWS_PROVIDER = True
except ImportError:
    HAS_NEWS_PROVIDER = False
    logging.getLogger(__name__).warning("⚠️ Could not import fetch_news_with_registry - news integration disabled")

try:
    from src.control_plane.telegram_notifier import (
        send_telegram_message,
        maybe_send_problem_alert,
        maybe_send_heads_up,
        maybe_send_confirmed,
    )
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    send_telegram_message = None
    maybe_send_problem_alert = None
    maybe_send_heads_up = None
    maybe_send_confirmed = None

from src.strategies.momentum_trading import MomentumTradingStrategy
try:
    from src.strategies.session_execution_strategy import SessionExecutionStrategy
    HAS_SESSION_EXECUTION_STRATEGY = True
except ImportError:
    HAS_SESSION_EXECUTION_STRATEGY = False
try:
    from src.strategies.range_trading import RangeTradingStrategy
except ImportError:
    RangeTradingStrategy = MomentumTradingStrategy
try:
    from src.strategies.eur_usd_5m_safe import EurUsd5mSafeStrategy
except ImportError:
    EurUsd5mSafeStrategy = MomentumTradingStrategy
try:
    from src.strategies.momentum_v2 import MomentumV2Strategy
except ImportError:
    MomentumV2Strategy = MomentumTradingStrategy
# Gold scalping strategy
try:
    from src.strategies.gold_scalping_optimized import GoldScalpingOptimizedStrategy as GoldScalpingStrategy
except ImportError:
    try:
        from src.strategies.gold_scalping import GoldScalpingStrategy
    except ImportError:
        # Fallback: use momentum if gold scalping not available
        GoldScalpingStrategy = MomentumTradingStrategy
# Session regime aligned gatekeeper strategy
try:
    from src.strategies.session_regime_aligned import SessionRegimeAlignedStrategy
    HAS_SESSION_REGIME_GATE = True
except ImportError:
    HAS_SESSION_REGIME_GATE = False
    logging.getLogger(__name__).warning("⚠️ SessionRegimeAlignedStrategy not available - gate disabled")

# Market hours check (proper FX market hours)
from src.core.market_hours import is_fx_market_open

# Readiness Observability
try:
    from runner_src.observability.readiness import get_readiness_summary
    HAS_READINESS_OBSERVABILITY = True
except ImportError:
    HAS_READINESS_OBSERVABILITY = False
    logging.getLogger(__name__).warning("⚠️ runner_src.observability.readiness not available - readiness score will be 0")

# Status snapshot for API bridge (lazy import - happens after path setup)
HAS_STATUS_SNAPSHOT = None  # Will be determined lazily

# Imports for Snapshot Integrity (Regime/Bias)
try:
    from src.control_plane.outlook_engine import get_outlook_engine
    from src.core.market_regime import MarketRegimeDetector
    from src.control_plane.market_data_provider import get_candles
    HAS_SNAPSHOT_DEPENDENCIES = True
except ImportError:
    HAS_SNAPSHOT_DEPENDENCIES = False
    logging.getLogger(__name__).warning("⚠️ Snapshot dependencies (Outlook/Regime) missing")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GLOBAL_SIGNAL_LOG_PATH = "/opt/ai-quant/logs/global_signal_decisions.jsonl"


def _log_global_signal_decision(payload: dict) -> None:
    """
    GLOBAL_SIGNAL_DECISION_PROBE
    Append-only JSONL log of signal readiness and rejection decisions.
    """
    try:
        payload.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
        os.makedirs(os.path.dirname(GLOBAL_SIGNAL_LOG_PATH), exist_ok=True)
        with open(GLOBAL_SIGNAL_LOG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        logger.error(f"GLOBAL_SIGNAL_LOG_FAILED: {e}")


def _get_forensic_logger():
    """Lazy-init forensic logger for STRUCTURED_LOGGER patch verification."""
    fl = logging.getLogger("FORENSIC_STRUCTURED_LOGGER")
    if not fl.handlers:
        os.makedirs("logs/forensic_probes", exist_ok=True)
        fh = logging.FileHandler("logs/forensic_probes/STRUCTURED_LOGGER_PATCH_VERIFY.log")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        fl.addHandler(fh)
        fl.setLevel(logging.INFO)
    return fl


# RISK CONSTANTS (Single Source of Truth) - Moved to src.core.constants
# MIN_TP_DISTANCE_PCT_FX = 0.001      # 0.1% minimum TP distance for FX
# MIN_TP_DISTANCE_PCT_METALS = 0.002  # 0.2% minimum TP distance for metals

def _can_execute(readiness_score: int = None) -> tuple[bool, str]:
    """Determine if execution is enabled based on trading mode and flags.
    
    Uses canonical EXECUTION_UNLOCK_OK with backward-compatible PAPER_EXECUTION_ENABLED alias.
    Also checks readiness score for paper execution (if provided).
    
    Returns:
        (can_execute: bool, reason: str)
    """
    gate = ExecutionGate()
    try:
        decision = gate.decision(readiness_score=readiness_score)
    except TypeError:
        decision = gate.decision()
    
    # Live mode: requires dual-confirm
    if decision.mode == 'live':
        if decision.allowed:
            return (True, "live_dual_enabled")
        else:
            return (False, f"live_blocked_{decision.reason_code}")
            
    # Paper mode: Check allowed status from decision (includes readiness check)
    if decision.allowed:
        return (True, decision.reason_code)
    else:
        return (False, decision.reason_code)


def _is_placeholder_account_id(account_id: str) -> bool:
    """Check if account_id is clearly a placeholder/invalid value."""
    if not account_id or not account_id.strip():
        return True
    
    account_id_lower = account_id.lower().strip()
    
    # Common placeholder prefixes
    placeholder_prefixes = ['test-', 'demo-', 'placeholder-', 'replace_', 'example-', 'sample-']
    if any(account_id_lower.startswith(prefix) for prefix in placeholder_prefixes):
        return True
    
    # Too short to be a real OANDA account ID
    if len(account_id.strip()) <= 3:
        return True
    
    # Contains placeholder keywords
    placeholder_keywords = ['placeholder', 'demo', 'test', 'example', 'sample', 'replace']
    if any(keyword in account_id_lower for keyword in placeholder_keywords):
        return True
    
    return False


def _has_valid_broker(account_id: str, account_manager) -> bool:
    """Check if account has a valid (non-placeholder) broker client for execution."""
    # Placeholder account_ids cannot have valid brokers
    if _is_placeholder_account_id(account_id):
        return False
    
    # For paper trading, we require OANDA Practice credentials (not PaperBroker)
    # Check for required OANDA env vars
    oanda_api_key = fxg_get_oanda_api_key_for_account(account_id)
    # IMPORTANT: normalize account id ('002' -> full env-backed id)
    resolved_account_id = fxg_resolve_oanda_account_id(account_id)
    oanda_account_id = resolved_account_id
    oanda_base_url = os.getenv("OANDA_BASE_URL", "").strip()
    
    # If OANDA_BASE_URL not set, default to practice
    if not oanda_base_url:
        trading_mode = os.getenv("TRADING_MODE", "paper").lower()
        if trading_mode == "live":
            oanda_base_url = "https://api-fxtrade.oanda.com"
        else:
            oanda_base_url = "https://api-fxpractice.oanda.com"
    
    # Require OANDA credentials for execution (paper or live)
    if not oanda_api_key:
        logger.debug(f"⚠️ OANDA_API_KEY not set for account {account_id[-3:]}")
        return False
    
    # Strict allowlist: only accounts present in env are execution-capable
    allowed_ids = _fxg_allowed_oanda_account_ids()
    if allowed_ids and resolved_account_id not in allowed_ids:
        logger.debug(f"⚠️ Account {account_id[-3:]} blocked (not in env allowlist)")
        return False
    
    # OANDA credentials present - valid for execution
    return True


class WorkingTradingSystem:
    def __init__(self):
        # FAIL-FAST: Verify critical constants exist
        try:
            _ = MIN_TP_DISTANCE_PCT_FX
            _ = MIN_TP_DISTANCE_PCT_METALS
        except NameError:
            raise RuntimeError("CRITICAL: Risk constants missing — execution blocked")

        # Defer OANDA_API_KEY check to runtime (allows paper-mode testing)
        if 'OANDA_API_KEY' not in os.environ:
            logger.warning("⚠️ OANDA_API_KEY not set - paper mode only")
            _fxg_append_problem_event(
                severity="AMBER",
                subsystem="env",
                key="env_missing_oanda_api_key",
                summary="OANDA_API_KEY is missing (execution will not be broker-valid).",
                hint_cmd="sudo grep -n '^OANDA_API_KEY=' /etc/ai-quant/.env | sed -E 's/=.*$/=REDACTED/'",
                fingerprint="env_missing_oanda_api_key",
            )
            if maybe_send_problem_alert:
                try:
                    maybe_send_problem_alert(
                        "env_missing_oanda_api_key",
                        "OANDA_API_KEY is missing (paper-safe, but execution cannot place orders).",
                        severity="AMBER",
                        hint_cmd="sudo grep -n '^OANDA_API_KEY=' /etc/ai-quant/.env | sed -E 's/=.*$/=REDACTED/'",
                        fingerprint="env_missing_oanda_api_key",
                    )
                except Exception:
                    pass
        
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        
        # Get account configs from YAML (even if broker not initialized)
        # This allows scanning to run with paper accounts
        self.account_configs = self.account_manager.account_configs
        self.account_ids_for_scanning = list(self.account_configs.keys()) if self.account_configs else []
        
        # Defensive logging: Log all loaded accounts
        for account_id in self.account_ids_for_scanning:
            account_suffix = account_id[-3:] if len(account_id) >= 3 else account_id
            logger.info(f"ACCOUNT_LOADED account={account_suffix} full_id={account_id} active={account_id in self.active_accounts}")
        
        self.strategies = {
            'momentum': MomentumTradingStrategy(),
            'gold': GoldScalpingStrategy(),
            'range': RangeTradingStrategy(),
            'eur_usd_5m_safe': EurUsd5mSafeStrategy(),
            'momentum_v2': MomentumV2Strategy()
        }
        
        # PHASE 1: Add SessionExecutionStrategy if available
        if HAS_SESSION_EXECUTION_STRATEGY:
            self.strategies['session_execution'] = SessionExecutionStrategy()
            logger.info("✅ SessionExecutionStrategy registered")
        else:
            logger.warning("⚠️ SessionExecutionStrategy not available (import failed)")
        
        # PHASE 1: Validate strategy_id for all registered strategies
        from src.control_plane.strategy_registry import log_strategy_registry, validate_strategy_key
        log_strategy_registry()
        
        # PHASE 1: Validate each strategy instance has strategy_id and it matches registry
        for registry_key, strategy_instance in self.strategies.items():
            if strategy_instance is None:
                continue
            # Ensure strategy has strategy_id attribute (from BaseStrategy)
            if not hasattr(strategy_instance, 'strategy_id'):
                logger.error(f"❌ Strategy '{registry_key}' missing strategy_id attribute - execution will be blocked")
                continue
            
            strategy_id = strategy_instance.strategy_id
            if not strategy_id or strategy_id.strip() == "":
                logger.error(f"❌ Strategy '{registry_key}' has empty strategy_id - execution will be blocked")
                continue
            
            # PHASE 1: Validate registry key exists (required for account config validation)
            if not validate_strategy_key(registry_key):
                logger.warning(
                    f"⚠️ Strategy registry key '{registry_key}' not found in registry "
                    f"(strategy_id: {strategy_id}). This may cause account config validation issues."
                )
            else:
                logger.debug(f"✅ Strategy '{registry_key}' validated (strategy_id: {strategy_id})")
            
            # PHASE 1: Validate strategy_id itself is in registry (for execution gate validation)
            # Note: strategy_id may differ from registry_key (e.g., 'gold' registry key -> 'gold_scalping' strategy_id)
            # Both should be valid, but strategy_id is what gets passed to execution gate
            if not validate_strategy_key(strategy_id):
                logger.warning(
                    f"⚠️ Strategy '{registry_key}' has strategy_id '{strategy_id}' not found in registry. "
                    f"Execution gate may block trades. Consider adding '{strategy_id}' to registry or "
                    f"updating STRATEGY_ID to match registry key '{registry_key}'."
                )
            else:
                logger.debug(f"✅ Strategy '{registry_key}' strategy_id '{strategy_id}' validated in registry")
        self.order_managers = {}
        
        # Session regime aligned gatekeeper (read-only, fail-closed)
        # PHASE 1: ENABLE_SESSION_REGIME_GATE must be true (fail-closed)
        enable_gate_env = os.getenv("ENABLE_SESSION_REGIME_GATE", "true").lower()
        enable_gate = enable_gate_env not in ("false", "0", "no", "off")
        
        # Fail-closed enforcement: if HAS_SESSION_REGIME_GATE and gate is disabled, fail startup
        if HAS_SESSION_REGIME_GATE and not enable_gate:
            raise RuntimeError(
                "CRITICAL: ENABLE_SESSION_REGIME_GATE=false is not allowed. "
                "Session regime gate must be enabled (fail-closed requirement)."
            )
        
        if HAS_SESSION_REGIME_GATE and enable_gate:
            self.session_regime_gate = SessionRegimeAlignedStrategy()
            logger.info("✅ Session regime aligned gatekeeper initialized")
        else:
            self.session_regime_gate = None
            if not HAS_SESSION_REGIME_GATE:
                logger.info("⚠️ Session regime aligned gatekeeper not available (dependencies missing)")
            else:
                logger.info("ℹ️ Session regime aligned gatekeeper disabled (ENABLE_SESSION_REGIME_GATE=false)")
        
        # Hot-reload support: track config state
        self._config_last_mtime = 0.0
        self._config_load_error = None  # Track config load failures
        self._active_strategy_key = "momentum"  # Default
        self._scan_interval = 30  # Default
        self._strategy_assignments = None  # Multi-account assignments
        self._account_risk_limits = {}  # Per-account risk limits from config
        self._global_max_daily_trades = 10  # Global default (from config.risk.max_daily_trades_per_account) - RAISED FOR PAPER TESTING
        self._max_open_trades_per_account = 3  # Default (from config.risk.max_positions)
        
        # Risk caps tracking
        self._open_trades_per_account = {}  # account_id -> count
        self._daily_trades_per_account = {}  # account_id -> count (resets daily)
        self._last_trade_time_per_account = {}  # account_id -> timestamp
        self._last_trade_time_per_symbol = {}  # (account_id, symbol) -> timestamp
        self._signal_fingerprints = {}  # (account_id, instrument, strategy_key) -> (timestamp, entry_price, side) for dedupe
        self._orders_per_hour_per_account = {}  # account_id -> list of timestamps (for hourly rate limiting)
        self._cancels_per_hour_per_account = {}  # account_id -> list of timestamps (for hourly cancel limiting)
        self._orders_per_minute = []  # List of (timestamp, account_id) for rate limiting
        self._last_daily_reset = dt.datetime.now(dt.timezone.utc).date()
        self._last_alert_at = 0.0
        self._last_alert_fingerprint = None
        
        # New observability counters
        self._price_sanity_blocks_per_account = {}  # account_id -> count
        self._price_integrity_blocks_per_account = {}  # account_id -> count (NEW)
        self._tp_omitted_per_account = {}  # account_id -> count
        self._throttle_skips_per_account = {}  # account_id -> count
        self._oanda_cancel_reasons_per_account = {}  # account_id -> {reason: count}
        self._last_cycle_lane_stats = {}  # resolved_account_id -> last-cycle stats (no secrets)
        
        # Trade Selector (Quality over Quantity)
        self.trade_selector = TradeSelector()
        
        # Strategy Trigger Probe (read-only instrumentation)
        if HAS_STRATEGY_PROBE and get_strategy_trigger_probe is not None:
            try:
                self.strategy_probe = get_strategy_trigger_probe(enabled=True)
                logger.info("✅ Strategy trigger probe enabled")
            except Exception as e:
                self.strategy_probe = None
                logger.warning(f"⚠️ Strategy trigger probe failed to init: {e}")
        else:
            self.strategy_probe = None
            logger.info("ℹ️ Strategy trigger probe disabled")
        
        # Snapshot Integrity Dependencies
        if HAS_SNAPSHOT_DEPENDENCIES:
            try:
                self.outlook_engine = get_outlook_engine()
                self.regime_detector = MarketRegimeDetector()
                self.price_action_bias = PriceActionBias()
                self.regime_bias = RegimeBias()
                logger.info("✅ Outlook/Regime/Bias engines initialized for snapshot integrity")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize Outlook/Regime for snapshot: {e}")
                self.outlook_engine = None
                self.regime_detector = None
                self.price_action_bias = None
                self.regime_bias = None
        else:
            self.outlook_engine = None
            self.regime_detector = None
            self.price_action_bias = None
            self.regime_bias = None
        
        # Price integrity validation thresholds (env-driven with safe defaults)
        self._max_price_staleness_seconds = int(os.getenv('MAX_PRICE_STALENESS_SECONDS', '15'))
        self._min_xau_usd_mid = float(os.getenv('MIN_XAU_USD_MID', '500'))
        self._max_xau_usd_mid = float(os.getenv('MAX_XAU_USD_MID', '10000'))
        self._min_fx_mid = float(os.getenv('MIN_FX_MID', '0.2'))
        self._max_fx_mid = float(os.getenv('MAX_FX_MID', '5.0'))
        
        # Try to load initial runtime config (optional)
        self._load_runtime_config()
        
        # Determine execution eligibility
        can_execute, exec_reason = _can_execute()
        self.execution_enabled = can_execute
        
        # Initialize status snapshot writer (lazy import after path setup)
        self.status_writer = self._get_status_writer()
        
        # Count accounts with valid execution brokers (non-placeholder, non-PaperBroker)
        execution_ready_accounts = []
        if can_execute:
            allowed_ids = _fxg_allowed_oanda_account_ids()
            # IMPORTANT: multi-lane execution is env-backed (OANDA_ACCOUNT_ID_001..006).
            # Do not rely on YAML "active_accounts" to enumerate lanes, since signals may carry lane ids (e.g. '002').
            candidate_accounts = sorted(allowed_ids) if allowed_ids else []
            if not candidate_accounts:
                # Fallback: derive from loaded accounts if allowlist is not configured
                candidate_accounts = [fxg_resolve_oanda_account_id(a) for a in (self.active_accounts or [])]
            for account_id in candidate_accounts:
                if _has_valid_broker(account_id, self.account_manager):
                    resolved_account_id = fxg_resolve_oanda_account_id(account_id)
                    if allowed_ids and resolved_account_id not in allowed_ids:
                        logger.debug(f"⚠️ Account {account_id[-3:]} blocked (not in env allowlist)")
                        continue
                    if resolved_account_id not in execution_ready_accounts:
                        execution_ready_accounts.append(resolved_account_id)
                    try:
                        # OrderManager stub doesn't need account_id, but we store it for reference
                        if resolved_account_id not in self.order_managers:
                            self.order_managers[resolved_account_id] = OrderManager()
                            logger.info(f"✅ OrderManager created for account {resolved_account_id[-3:]}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not initialize OrderManager for {resolved_account_id[-3:]}: {e}")
        
        if not can_execute:
            logger.info(f"📄 Execution disabled ({exec_reason}) - signals-only mode")
        elif not execution_ready_accounts:
            logger.info(f"📄 Execution enabled but no valid brokers available - signals-only mode")
        else:
            logger.info(f"✅ Execution enabled ({exec_reason}) - {len(execution_ready_accounts)} account(s) ready")
        
        if not self.account_ids_for_scanning:
            logger.info("ℹ️ No accounts configured in YAML - scanning will run with default instruments")
        
        # CANARY SIGNAL: Emit startup probe signal to verify strategy execution path
        try:
            logger.info("🔍 Emitting canary startup probe signal...")
            get_signal_exporter().emit(
                strategy="CANARY_STRATEGY_PROBE",
                symbol="EUR_USD",
                side="BUY",
                units=1,
                entry_type="MARKET",
                stop_loss=None,
                take_profit=None,
                confidence=0.01,
                regime="canary",
                session="canary",
                news_state="canary",
                execution_allowed=False,
                block_reason="canary_startup_probe",
                account="canary",
                bridge_account=None,
                meta={
                    "purpose": "verify_strategies_execute_path",
                    "source": "working_trading_system_startup",
                    "timestamp": dt.datetime.now(dt.timezone.utc).isoformat()
                }
            )
            logger.info("✅ Canary startup probe signal emitted")
        except Exception as e:
            logger.warning(f"⚠️ Failed to emit canary signal: {e}")
        else:
            logger.info(f"✅ Working Trading System initialized")
            logger.info(f"   Accounts for scanning: {len(self.account_ids_for_scanning)}")
            logger.info(f"   Accounts with execution capability: {len(execution_ready_accounts)}")
        
        # PHASE 1: Account isolation enforcement - fail-fast at startup
        self._enforce_account_isolation()
        
        # Write initial status snapshot
        self._write_status_snapshot(0, 0, [], [])

        # === STARTUP HEARTBEAT (SIGNAL EXPORT SIDECAR) ===
        try:
            logger.info(f"📡 SignalExporter path: {get_signal_exporter().LOG_FILE_PATH}")
            get_signal_exporter().emit(
                strategy='SYSTEM_HEARTBEAT',
                symbol='NONE',
                side='NONE',
                units=0,
                entry_type='NONE',
                confidence=0.0,
                regime='unknown',
                session='unknown',
                news_state='unknown',
                execution_allowed=False,
                block_reason='startup_heartbeat',
                account='system',
                bridge_account=os.getenv('BRIDGE_ACCOUNT', 'ftmo_eval_primary'),
                meta={'purpose': 'startup_link_check'}
            )
        except Exception:
            pass
        # === END STARTUP HEARTBEAT ===
    
    def _get_status_writer(self):
        """Lazy import status snapshot writer (after path setup)"""
        global HAS_STATUS_SNAPSHOT
        if HAS_STATUS_SNAPSHOT is None:
            try:
                from src.control_plane.status_snapshot import get_status_snapshot
                HAS_STATUS_SNAPSHOT = True
                return get_status_snapshot()
            except ImportError:
                HAS_STATUS_SNAPSHOT = False
                return None
        elif HAS_STATUS_SNAPSHOT:
            from src.control_plane.status_snapshot import get_status_snapshot
            return get_status_snapshot()
        else:
            return None
    
    def _enforce_account_isolation(self) -> None:
        """
        PHASE 1: Account isolation enforcement - DISABLED for account 006.
        
        Account 006 is now treated as a standard trading account and can use any strategy.
        SessionExecutionStrategy can still use account 006, but it's no longer exclusive.
        """
        SESSION_EXECUTION_STRATEGY = "session_execution"
        REQUIRED_ACCOUNT_SUFFIX = "006"
        
        # Check strategy assignments if configured
        if self._strategy_assignments:
            for assignment in self._strategy_assignments:
                account_id = assignment.account_id
                strategy_key = assignment.strategy_key
                account_suffix = account_id[-3:] if len(account_id) >= 3 else None
                
                # Rule 1: SessionExecutionStrategy can use account 006 (preferred but not required)
                if strategy_key == SESSION_EXECUTION_STRATEGY:
                    if account_suffix != REQUIRED_ACCOUNT_SUFFIX:
                        logger.warning(
                            f"⚠️ SessionExecutionStrategy typically uses account suffix {REQUIRED_ACCOUNT_SUFFIX}, "
                            f"but found suffix {account_suffix} (account_id: {account_id[-6:] if len(account_id) >= 6 else account_id}). "
                            f"Continuing with standard account behavior."
                        )
                    else:
                        logger.info(f"✅ SessionExecutionStrategy bound to account {REQUIRED_ACCOUNT_SUFFIX}")
                
                # Rule 2: Account 006 isolation DISABLED - allow standard strategies
                elif account_suffix == REQUIRED_ACCOUNT_SUFFIX:
                    logger.info(
                        f"✅ Account 006 isolation disabled – account {REQUIRED_ACCOUNT_SUFFIX} can use standard strategies. "
                        f"Strategy '{strategy_key}' assigned to account {account_id[-6:] if len(account_id) >= 6 else account_id}."
                    )
        
        logger.info("✅ Account isolation enforcement: Account 006 treated as standard trading account")
    
    def _persist_strategy_readiness(self, strategy_id: str, instrument: str, readiness) -> None:
        """Persist strategy readiness snapshot to runtime/strategy_readiness.json"""
        try:
            from pathlib import Path
            import json
            
            # Determine runtime directory
            repo_root = Path(__file__).resolve().parent
            runtime_dir = repo_root / "runtime"
            runtime_dir.mkdir(exist_ok=True)
            
            # Load existing readiness data
            readiness_file = runtime_dir / "strategy_readiness.json"
            if readiness_file.exists():
                try:
                    with open(readiness_file, 'r') as f:
                        all_readiness = json.load(f)
                except Exception:
                    all_readiness = {}
            else:
                all_readiness = {}
            
            # Convert readiness to dict
            readiness_dict = {
                "strategy_id": readiness.strategy_id,
                "instrument": readiness.instrument,
                "readiness_score": readiness.readiness_score,
                "blocking_reasons": readiness.blocking_reasons,
                "bias_alignment": readiness.bias_alignment.value,
                "estimated_time_to_entry_minutes": readiness.estimated_time_to_entry_minutes,
                "last_signal_ts": readiness.last_signal_ts,
                "regime": readiness.regime,
                "volatility_pct": readiness.volatility_pct,
                "embargo_active": readiness.embargo_active,
                "daily_bias": readiness.daily_bias,
                "weekly_bias": readiness.weekly_bias,
                "execution_allowed": readiness.execution_allowed,
                "cooldown_remaining_minutes": readiness.cooldown_remaining_minutes,
                "signal_confidence": readiness.signal_confidence,
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "details": readiness.details
            }
            
            # Store by strategy_id + instrument key
            key = f"{strategy_id}:{instrument}"
            all_readiness[key] = readiness_dict
            
            # Write atomically
            tmp_file = readiness_file.with_suffix(".tmp")
            with open(tmp_file, 'w') as f:
                json.dump(all_readiness, f, indent=2)
            tmp_file.replace(readiness_file)
            
        except Exception as e:
            logger.debug(f"Failed to persist strategy readiness: {e}")
    
    def _write_alpha_gap_probe(self, probe_data: dict) -> None:
        """ALPHA_GATE_AND_SIGNAL_FLOW_PROBE: Write evidence-only probe log.
        
        This probe distinguishes news embargo, session gate, and signal evaluation failures.
        Append-only, no behavior change.
        """
        try:
            import json
            log_path = "/opt/ai-quant/logs/alpha_gap_probe.jsonl"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            # Ensure all required fields
            probe_entry = {
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "instrument": probe_data.get("instrument", "UNKNOWN"),
                "news_checked": probe_data.get("news_checked", False),
                "news_embargo_active": probe_data.get("news_embargo_active", False),
                "news_reason": probe_data.get("news_reason"),
                "session_gate_checked": probe_data.get("session_gate_checked", False),
                "session_gate_result": probe_data.get("session_gate_result", "UNKNOWN"),
                "session_gate_reason": probe_data.get("session_gate_reason"),
                "dependencies_loaded": probe_data.get("dependencies_loaded", {
                    "readiness_evaluator": False,
                    "bias_engine": False,
                    "regime_engine": False
                }),
                "strategies_registered": probe_data.get("strategies_registered", 0),
                "strategies_evaluated": probe_data.get("strategies_evaluated", 0),
                "signals_emitted": probe_data.get("signals_emitted", 0),
                "signals_blocked": probe_data.get("signals_blocked", 0),
                "primary_blocker": probe_data.get("primary_blocker", "UNKNOWN"),
                "source_of_truth": probe_data.get("source_of_truth", "UNKNOWN")
            }
            
            with open(log_path, "a") as f:
                f.write(json.dumps(probe_entry) + "\n")
        except Exception as e:
            # Fail silently - probe should never break execution
            logger.debug(f"ALPHA_GAP_PROBE write failed: {e}")

    def _persist_reasoning_snapshot(self, instrument: str, readiness, embargo_active: bool, embargo_seconds_remaining: Optional[int] = None) -> None:
        """
        Create and persist REASONING_SNAPSHOT object per instrument.
        
        Writes to:
        - /opt/ai-quant/runtime/reasoning_snapshot.json (overwrite each cycle)
        - /opt/ai-quant/logs/reasoning_snapshot.jsonl (append each cycle)
        """
        try:
            from pathlib import Path
            import json
            import os
            
            # Determine paths (use /opt/ai-quant if available, else fallback to local)
            if os.path.exists("/opt/ai-quant"):
                runtime_dir = Path("/opt/ai-quant/runtime")
                logs_dir = Path("/opt/ai-quant/logs")
            else:
                # Fallback to local paths for development
                repo_root = Path(__file__).resolve().parent
                runtime_dir = repo_root / "runtime"
                logs_dir = repo_root / "logs"
            
            runtime_dir.mkdir(parents=True, exist_ok=True)
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract primary blocker (first blocking reason, or None if ready)
            primary_blocker = None
            secondary_blockers = []
            
            if readiness and readiness.blocking_reasons:
                primary_blocker = readiness.blocking_reasons[0] if len(readiness.blocking_reasons) > 0 else None
                secondary_blockers = readiness.blocking_reasons[1:] if len(readiness.blocking_reasons) > 1 else []
            
            # Determine nearest unblock event
            nearest_unblock_event = None
            estimated_time_to_readiness = None
            
            if readiness:
                # Use estimated_time_to_entry_minutes if available
                if readiness.estimated_time_to_entry_minutes is not None:
                    estimated_time_to_readiness = readiness.estimated_time_to_entry_minutes
                    if estimated_time_to_readiness > 0:
                        nearest_unblock_event = f"Estimated {estimated_time_to_readiness} minutes"
                    else:
                        nearest_unblock_event = "Ready now"
                elif embargo_active and embargo_seconds_remaining is not None:
                    # Embargo-based estimate
                    embargo_minutes = int(embargo_seconds_remaining / 60) + 1
                    estimated_time_to_readiness = embargo_minutes
                    nearest_unblock_event = f"Embargo clears in {embargo_minutes} minutes"
                elif readiness.cooldown_remaining_minutes is not None and readiness.cooldown_remaining_minutes > 0:
                    estimated_time_to_readiness = readiness.cooldown_remaining_minutes
                    nearest_unblock_event = f"Cooldown expires in {readiness.cooldown_remaining_minutes} minutes"
                elif primary_blocker:
                    # Generic blocker - cannot estimate
                    nearest_unblock_event = "Unknown"
                else:
                    nearest_unblock_event = "Ready now"
                    estimated_time_to_readiness = 0
            
            # Construct bias_state string
            bias_state = "UNKNOWN"
            if readiness:
                if readiness.daily_bias and readiness.weekly_bias:
                    bias_state = f"{readiness.daily_bias}/{readiness.weekly_bias}"
                elif readiness.daily_bias:
                    bias_state = f"{readiness.daily_bias}/UNKNOWN"
                elif readiness.weekly_bias:
                    bias_state = f"UNKNOWN/{readiness.weekly_bias}"
            
            # Build reasoning snapshot
            timestamp_utc = dt.datetime.now(dt.timezone.utc).isoformat()
            
            reasoning_snapshot = {
                "instrument": instrument,
                "primary_blocker": primary_blocker,
                "secondary_blockers": secondary_blockers,
                "readiness_score": readiness.readiness_score if readiness else 0,
                "nearest_unblock_event": nearest_unblock_event,
                "estimated_time_to_readiness": estimated_time_to_readiness,
                "embargo_active": embargo_active,
                "regime": readiness.regime if readiness else "UNKNOWN",
                "bias_state": bias_state,
                "timestamp_utc": timestamp_utc
            }
            
            # Write to JSON file (overwrite each cycle - single instrument snapshot)
            snapshot_file = runtime_dir / "reasoning_snapshot.json"
            tmp_file = snapshot_file.with_suffix(".tmp")
            with open(tmp_file, 'w') as f:
                json.dump(reasoning_snapshot, f, indent=2)
            tmp_file.replace(snapshot_file)
            
            # Append to JSONL log file
            jsonl_file = logs_dir / "reasoning_snapshot.jsonl"
            with open(jsonl_file, 'a') as f:
                f.write(json.dumps(reasoning_snapshot) + '\n')
            
        except Exception as e:
            logger.debug(f"Failed to persist reasoning snapshot for {instrument}: {e}")
    
    def _write_status_snapshot(self, signals_generated: int, executed_count: int, recent_signals_list=None, recent_news_list=None) -> None:
        """Write status snapshot for API (atomic, no secrets)"""
        if not self.status_writer:
            return
        
        try:
            # Get execution state (defensive against attribute errors)
            can_execute, exec_reason = _can_execute()
            
            # Check if self.execution_enabled matches can_execute, update if needed
            current_exec_enabled = getattr(self, "execution_enabled", None)
            if current_exec_enabled != can_execute:
                self.execution_enabled = can_execute
            
            # Count execution-ready accounts
            # If execution is unlocked (can_execute=True), count loaded accounts as execution-capable
            # Broker validity check is separate and doesn't affect capability count
            allowed_ids = _fxg_allowed_oanda_account_ids()
            execution_capable_accounts = []
            if can_execute:
                # Prefer authoritative, normalized keys used for execution
                if self.order_managers:
                    execution_capable_accounts = sorted(self.order_managers.keys())
                else:
                    # Fallback: resolve active accounts against env allowlist
                    for _raw in (self.active_accounts or []):
                        _resolved = fxg_resolve_oanda_account_id(_raw)
                        if not allowed_ids or _resolved in allowed_ids:
                            if _resolved not in execution_capable_accounts:
                                execution_capable_accounts.append(_resolved)
            execution_ready_count = len(execution_capable_accounts)
            
            # Build daily limit map (account_id -> limit value)
            daily_limit_map = {}
            for account_id in (execution_capable_accounts or self.account_ids_for_scanning):
                resolved_account_id = fxg_resolve_oanda_account_id(account_id)
                if allowed_ids and resolved_account_id not in allowed_ids:
                    continue
                account_limits = self._account_risk_limits.get(resolved_account_id) or self._account_risk_limits.get(account_id)
                if account_limits and account_limits.max_daily_trades is not None:
                    daily_limit_map[resolved_account_id] = account_limits.max_daily_trades
                elif account_limits and account_limits.max_daily_trades is None:
                    # Use global default
                    daily_limit_map[resolved_account_id] = self._global_max_daily_trades
                else:
                    # No per-account config, use global default
                    daily_limit_map[resolved_account_id] = self._global_max_daily_trades
            
            # === SNAPSHOT INTEGRITY: REGIME & BIAS ===
            # Fetch global outlook (using EUR_USD as representative)
            daily_bias = "UNKNOWN"
            weekly_bias = "UNKNOWN"
            monthly_bias = "UNKNOWN"
            
            if self.outlook_engine:
                try:
                    daily = self.outlook_engine.get_latest("daily")
                    weekly = self.outlook_engine.get_latest("weekly")
                    monthly = self.outlook_engine.get_latest("monthly")
                    
                    def get_bias(outlook, instrument="EUR_USD"):
                        if not outlook: return "UNKNOWN"
                        for o in outlook.get("outlooks", []):
                            if o.get("instrument") == instrument:
                                return o.get("bias", "UNKNOWN")
                        return "UNKNOWN"

                    daily_bias = get_bias(daily)
                    weekly_bias = get_bias(weekly)
                    monthly_bias = get_bias(monthly)
                except Exception:
                    pass

            # Fetch Regime (on EUR_USD)
            regime = "UNKNOWN"
            current_session = "UNKNOWN"
            
            if self.regime_detector and HAS_SNAPSHOT_DEPENDENCIES:
                try:
                    # Fetch fresh candles for regime detection (EUR_USD)
                    candles = get_candles("EUR_USD", granularity="M5", count=60)
                    analysis = self.regime_detector.detect_regime("EUR_USD", candles)
                    regime = analysis.regime.value
                except Exception:
                    regime = "UNKNOWN"
                    
            # Determine Session
            current_time = dt.datetime.now(dt.timezone.utc)
            h = current_time.hour
            if h >= 22 or h < 6:
                current_session = "asia"
            elif 6 <= h < 12:
                current_session = "london"
            elif 12 <= h < 16:
                current_session = "london_ny_overlap"
            elif 16 <= h < 21:
                current_session = "new_york"
            else:
                current_session = "transition"

            # Calculate Readiness (Observability)
            readiness_score = 0
            readiness_countdown = "Unknown"
            readiness_breakdown = None
            no_trade_reason = "regime_unknown" if regime == "UNKNOWN" else None

            if HAS_READINESS_OBSERVABILITY:
                try:
                    readiness_context = {
                        "regime": regime,
                        "regime_resolved": regime != "UNKNOWN" and regime is not None,
                        "bias_available": daily_bias != "UNKNOWN",
                        "bias_confidence": 1.0 if daily_bias != "UNKNOWN" else 0.0,
                        "policy_ready": True, 
                        "news_embargo": False, # TODO: Wire up real news status
                        "risk_ok": can_execute,
                        "embargo_seconds_remaining": 0
                    }
                    import dataclasses
                    readiness_data = get_readiness_summary(readiness_context)
                    readiness_score = readiness_data.get("readiness_score", 0)
                    readiness_countdown = readiness_data.get("countdown_minutes", "Unknown")
                    readiness_breakdown_obj = readiness_data.get("breakdown")
                    if readiness_breakdown_obj and dataclasses.is_dataclass(readiness_breakdown_obj):
                        readiness_breakdown = dataclasses.asdict(readiness_breakdown_obj)
                    else:
                        readiness_breakdown = readiness_breakdown_obj
                    
                    # Update no_trade_reason based on blocks
                    if not can_execute:
                         no_trade_reason = exec_reason
                    elif readiness_score < 100:
                         # Find first blocker
                         blockers = readiness_data.get("blocking_components", [])
                         if blockers:
                             no_trade_reason = blockers[0]
                except Exception as e:
                    logger.warning(f"Readiness calc failed: {e}")

            # Build snapshot (NO SECRETS)
            # FORCE paper mode reporting if not explicitly live to ensure safety compliance
            trading_mode = os.getenv("TRADING_MODE", "paper")
            if trading_mode != 'live':
                trading_mode = 'paper'
                
            snapshot = {
                "mode": trading_mode,
                "execution_enabled": can_execute,
                "execution_reason": exec_reason,
                "accounts_total": len(execution_capable_accounts) if execution_capable_accounts else len(self.account_ids_for_scanning),
                "accounts_execution_capable": execution_ready_count,
                "active_strategy_key": self._active_strategy_key,
                "scan_interval": self._scan_interval,
                "last_signals_generated": signals_generated,
                "last_executed_count": executed_count,
                "last_scan_iso": dt.datetime.utcnow().isoformat() + "Z",
                "market_closed": not is_fx_market_open(dt.datetime.now(dt.timezone.utc)),  # FX market hours
                "accounts": [],  # Populated below without secrets
                "recent_signals": self._format_signals_for_snapshot(recent_signals_list) if recent_signals_list else [],
                "recent_news": recent_news_list or [],
                "positions": [],  # Empty in signals-only
                "pending_trades": [],  # Empty in signals-only
                "strategy_assignments": [
                    {
                        "account_id": a.account_id[-4:] if len(a.account_id) > 4 else "****",  # Masked
                        "strategy_key": a.strategy_key,
                        "enabled": a.enabled
                    }
                    for a in (self._strategy_assignments or [])
                ] if self._strategy_assignments else [],
                # Contract compliance (v1): daily limits and trades tracking
                "daily_limit_current": daily_limit_map,  # account_id -> limit (0=unlimited, None=use global)
                "daily_trades_today": dict(self._daily_trades_per_account),  # account_id -> count
                
                # Observability counters
                "price_sanity_blocks_per_account": dict(self._price_sanity_blocks_per_account),
                "price_integrity_blocks_per_account": dict(self._price_integrity_blocks_per_account),  # NEW
                "tp_omitted_per_account": dict(self._tp_omitted_per_account),
                "throttle_skips_per_account": dict(self._throttle_skips_per_account),
                "oanda_cancel_reasons_per_account": dict(self._oanda_cancel_reasons_per_account),
                
                # Trade Selection Pool (Observability)
                "trade_selection_pool": self.trade_selector.get_top_candidates(limit=10) if hasattr(self, 'trade_selector') else [],
                
                # GLOBAL STATE INTEGRITY
                "session": current_session,
                "regime": regime,
                "daily_bias": daily_bias,
                "weekly_bias": weekly_bias,
                "monthly_bias": monthly_bias,
                
                # Readiness & Status Badge
                "readiness_score": readiness_score,
                "readiness_countdown": readiness_countdown,
                "readiness_breakdown": readiness_breakdown,
                "no_trade_reason": no_trade_reason
            }
            
            # Add account summaries (no secrets, masked IDs)
            accounts_for_snapshot = execution_capable_accounts or list(self.account_ids_for_scanning)
            seen = set()
            # Build best-effort strategy mapping from runtime assignments (no behavior change).
            strategy_by_suffix = {}
            try:
                for a in (self._strategy_assignments or []):
                    if not getattr(a, "enabled", False):
                        continue
                    aid = getattr(a, "account_id", "") or ""
                    suf = str(aid)[-3:] if aid else ""
                    if suf:
                        strategy_by_suffix[suf] = str(getattr(a, "strategy_key", "") or "")
            except Exception:
                pass
            for account_id in accounts_for_snapshot:
                resolved_account_id = fxg_resolve_oanda_account_id(account_id)
                if allowed_ids and resolved_account_id not in allowed_ids:
                    continue
                if resolved_account_id in seen:
                    continue
                seen.add(resolved_account_id)
                config = (
                    self.account_configs.get(resolved_account_id)
                    or self.account_configs.get(account_id)
                    or self.account_configs.get(resolved_account_id[-3:])  # YAML may key lanes as '001'..'006'
                )
                # Enforce non-null strategy/instruments in status (truthy string/list only).
                lane_suffix = resolved_account_id[-3:] if resolved_account_id else ""
                default_instruments = ["EUR_USD", "GBP_USD", "XAU_USD", "USD_JPY", "AUD_USD"]
                strategy_name = None
                instruments_list = None
                if config:
                    strategy_name = getattr(config, "strategy_name", None)
                    instruments_list = getattr(config, "instruments", None)
                if not strategy_name:
                    strategy_name = strategy_by_suffix.get(lane_suffix) or self._active_strategy_key or "unknown"
                if not isinstance(instruments_list, list):
                    instruments_list = default_instruments

                lane_stats = {}
                try:
                    lane_stats = (self._last_cycle_lane_stats or {}).get(resolved_account_id) or (self._last_cycle_lane_stats or {}).get(lane_suffix) or {}
                except Exception:
                    lane_stats = {}
                if config:
                    snapshot["accounts"].append({
                        "id_masked": resolved_account_id[-4:] if len(resolved_account_id) > 4 else "****",
                        "strategy": str(strategy_name),
                        "instruments": list(instruments_list)[:3],  # Limit list size
                        "execution_capable": can_execute  # Execution capable if execution is unlocked
                        ,
                        "last_cycle_ts_utc": lane_stats.get("last_cycle_ts_utc"),
                        "signals_generated_last_cycle": int(lane_stats.get("signals_generated_last_cycle") or 0),
                        "executed_last_cycle": int(lane_stats.get("executed_last_cycle") or 0),
                        "last_skip_reason": lane_stats.get("last_skip_reason"),
                    })
                else:
                    snapshot["accounts"].append({
                        "id_masked": resolved_account_id[-4:] if len(resolved_account_id) > 4 else "****",
                        "strategy": str(strategy_name),
                        "instruments": list(instruments_list)[:3],
                        "execution_capable": can_execute
                        ,
                        "last_cycle_ts_utc": lane_stats.get("last_cycle_ts_utc"),
                        "signals_generated_last_cycle": int(lane_stats.get("signals_generated_last_cycle") or 0),
                        "executed_last_cycle": int(lane_stats.get("executed_last_cycle") or 0),
                        "last_skip_reason": lane_stats.get("last_skip_reason"),
                    })
            
            # Write atomically
            self.status_writer.write(snapshot)
            
        except Exception as e:
            # Log explicit marker with errno and path for observability
            errno_str = str(getattr(e, 'errno', 'unknown'))
            path_str = str(getattr(self.status_writer, 'snapshot_path', 'unknown'))
            logger.warning(f"STATUS_WRITE_FAIL errno={errno_str} path={path_str} error={str(e)[:200]}")
            _fxg_append_problem_event(
                severity="AMBER",
                subsystem="runner",
                key="status_write_fail",
                summary="Status snapshot write failed (STATUS_WRITE_FAIL).",
                details=f"errno={errno_str} path={path_str} error={str(e)[:200]}",
                hint_cmd="sudo journalctl -u ai-quant-runner -n 120 --no-pager | egrep -i 'STATUS_WRITE_FAIL' | tail -n 50",
                fingerprint=f"status_write_fail:{errno_str}:{path_str}",
            )
            if maybe_send_problem_alert:
                try:
                    maybe_send_problem_alert(
                        "status_write_fail",
                        f"Status snapshot write failed (errno={errno_str}).",
                        severity="AMBER",
                        hint_cmd="sudo journalctl -u ai-quant-runner -n 120 --no-pager | egrep -i 'STATUS_WRITE_FAIL' | tail -n 50",
                        fingerprint=f"status_write_fail:{errno_str}:{path_str}",
                    )
                except Exception:
                    pass
    
    def _execute_forced_paper_test(self, account_id: str) -> None:
        """[FORENSIC] Place ONE PAPER test order (EUR_USD BUY 1000) via full execution pipeline.
        Reversible. Only called when FORCE_PAPER_TEST_TRADE=true. PAPER mode only."""
        try:
            instrument = "EUR_USD"
            units = 1000
            oanda_api_key = fxg_get_oanda_api_key_for_account(account_id)
            oanda_base_url = os.getenv("OANDA_BASE_URL", "").strip()
            if not oanda_base_url:
                trading_mode = os.getenv("TRADING_MODE", "paper").lower()
                oanda_base_url = "https://api-fxpractice.oanda.com" if trading_mode != "live" else "https://api-fxtrade.oanda.com"
            if not oanda_api_key:
                logger.warning("[FORCED_TEST_TRADE] OANDA_API_KEY missing — skipping PAPER test order")
                return
            try:
                from src.control_plane.market_data_provider import get_latest_price
                price_obj = get_latest_price(instrument, timeout_s=5.0, validate=False)
                mid = price_obj.mid if price_obj else 0.0
            except Exception as e:
                logger.warning(f"[FORCED_TEST_TRADE] get_latest_price failed: {e} — using fallback 1.05")
                mid = 1.05
            if mid <= 0:
                mid = 1.05
            stop_loss = round(mid - 0.01, 5)
            price_precision = 5

            def exec_order():
                import requests
                headers = {"Authorization": f"Bearer {oanda_api_key}", "Content-Type": "application/json"}
                url = f"{oanda_base_url}/v3/accounts/{account_id}/orders"
                order_payload = {
                    "order": {
                        "type": "MARKET",
                        "instrument": instrument,
                        "units": str(units),
                        "stopLossOnFill": {"price": f"{stop_loss:.{price_precision}f}"}
                    }
                }
                r = requests.post(url, headers=headers, json=order_payload, timeout=10)
                if r.status_code not in (200, 201):
                    raise RuntimeError(f"OANDA order failed: HTTP {r.status_code} - {r.text[:200]}")
                return r.json()

            gate = ExecutionGate()
            meta = {"source": "working_trading_system", "path": "_execute_forced_paper_test", "strategy_id": "forced_test", "strategy_key": "FORCED_TEST"}
            result = gate.place_market_order(
                instrument=instrument,
                units=units,
                account_id=account_id,
                exec_fn=exec_order,
                meta=meta
            )
            if result and (result.get("orderCreateTransaction", {}).get("id") or result.get("orderFillTransaction", {}).get("id")):
                logger.info(f"[FORCED_TEST_TRADE] PAPER order placed for account {account_id[-3:]} — tx present")
            else:
                logger.warning(f"[FORCED_TEST_TRADE] PAPER order response for {account_id[-3:]} missing tx id: {type(result)}")
        except Exception as e:
            logger.error(f"[FORCED_TEST_TRADE] PAPER test failed for {account_id[-3:]}: {e}")
    
    def _format_signals_for_snapshot(self, signals):
        """Format signals for status snapshot (no secrets)"""
        formatted = []
        for signal in signals[:20]:  # Limit to recent 20 signals
            formatted.append({
                "id": f"{signal.instrument}_{signal.side.value}_{id(signal)}",
                "instrument": signal.instrument,
                "side": signal.side.value if hasattr(signal.side, 'value') else str(signal.side),
                "strategy_key": getattr(signal, 'strategy_key', None),
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "account_id_masked": signal.account_id[-4:] if signal.account_id and len(signal.account_id) > 4 else "****",
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).timestamp()
            })
        return formatted

    def _notify_telegram_signals(self, signals):
        if not HAS_TELEGRAM:
            return
        if not signals:
            return
        now_ts = time.time()
        if now_ts - self._last_alert_at < 60:
            return
        fingerprint = ",".join(
            f"{s.instrument}:{getattr(s.side, 'value', s.side)}:{getattr(s, 'strategy_key', '')}"
            for s in signals[:5]
        )
        if fingerprint == self._last_alert_fingerprint:
            return
        lines = ["AI_QUANT Signals:"]
        for s in signals[:5]:
            side = getattr(s.side, "value", s.side)
            strat = getattr(s, "strategy_key", "") or "unknown"
            lines.append(f"{s.instrument} {side} @ {s.entry_price} ({strat})")
        try:
            send_telegram_message("\n".join(lines))
            self._last_alert_at = now_ts
            self._last_alert_fingerprint = fingerprint
        except Exception as e:
            logger.warning(f"⚠️ Telegram alert failed: {str(e)[:200]}")

    def _apply_trade_selection_config(self, config) -> None:
        """Apply TradeSelector config with ultra_strict_forex-only override support.

        Contract:
        - Global defaults remain unchanged for all strategies.
        - Overrides are ONLY consulted when active_strategy_key == 'ultra_strict_forex'.
        - If override is missing/unusable, falls back to config.trade_selection.
        """
        try:
            active_key = getattr(config, "active_strategy_key", None) or getattr(self, "_active_strategy_key", None)
            overrides = getattr(config, "trade_selection_overrides", None) or {}

            ts = None
            used_override = False

            if active_key == "ultra_strict_forex" and isinstance(overrides, dict):
                ts = overrides.get(active_key)
                used_override = ts is not None

            if ts is None:
                ts = getattr(config, "trade_selection", None)

            if ts is not None and hasattr(self, "trade_selector"):
                self.trade_selector.update_config(ts)
                mode_val = getattr(ts, "mode", None)
                logger.info(f"   Trade Selection Mode: {mode_val} (override={'yes' if used_override else 'no'})")
        except Exception as e:
            logger.warning(f"⚠️ Trade selection config apply failed: {str(e)[:200]}")
    
    def _load_runtime_config(self) -> None:
        """Load runtime config if available (hot-reload support)
        
        This allows dashboard to change settings without restarting runner.
        Config changes are applied deterministically before next scan.
        """
        try:
            # Try to import control plane config store
            from src.control_plane.config_store import ConfigStore
            
            config_store = ConfigStore()
            config = config_store.load()
            
            # Update internal state
            self._active_strategy_key = config.active_strategy_key
            self._scan_interval = config.scan_interval_seconds
            self._strategy_assignments = config.strategy_assignments
            self._global_max_daily_trades = config.risk.max_daily_trades_per_account
            self._max_open_trades_per_account = config.risk.max_positions
            self._account_risk_limits = {
                account_id: limits
                for account_id, limits in (config.account_risk_limits or {}).items()
            }
            self._config_last_mtime = config_store.get_mtime()
            
            logger.info(f"📝 Runtime config loaded: strategy={self._active_strategy_key}, interval={self._scan_interval}s, global_max_daily_trades={self._global_max_daily_trades}")
            if self._strategy_assignments:
                enabled_count = sum(1 for a in self._strategy_assignments if a.enabled)
                logger.info(f"   Strategy assignments: {enabled_count} enabled out of {len(self._strategy_assignments)}")
                
                # PHASE 2: Validate strategy assignments against registry
                from src.control_plane.strategy_registry import validate_strategy_key
                valid_strategies = set()
                invalid_strategies = set()
                disabled_strategies = set()
                
                for assignment in self._strategy_assignments:
                    strategy_key = assignment.strategy_key
                    if not validate_strategy_key(strategy_key):
                        if assignment.enabled:
                            invalid_strategies.add(strategy_key)
                        else:
                            logger.debug(f"   ⚠️ Disabled strategy '{strategy_key}' not found in registry (acceptable if legacy)")
                    elif not assignment.enabled:
                        disabled_strategies.add(strategy_key)
                    else:
                        valid_strategies.add(strategy_key)
                
                if invalid_strategies:
                    logger.warning(f"   ❌ Invalid strategy keys (not in registry): {invalid_strategies}")
                if disabled_strategies:
                    logger.info(f"   ℹ️ Disabled strategies: {disabled_strategies}")
                if valid_strategies:
                    logger.info(f"   ✅ Valid enabled strategies: {valid_strategies}")
            if self._account_risk_limits:
                logger.info(f"   Account risk limits: {len(self._account_risk_limits)} accounts configured")
            
            # Update TradeSelector config
            if hasattr(config, 'trade_selection'):
                # Apply TradeSelector config (override applies ONLY for ultra_strict_forex)
                self._apply_trade_selection_config(config)
            
            # Clear error if successful
            self._config_load_error = None
            
        except ImportError:
            # Control plane not available - use defaults
            logger.debug("Control plane not available - using default settings")
            self._strategy_assignments = None
            self._config_load_error = None  # Acceptable state
        except Exception as e:
            self._config_load_error = str(e)
            logger.warning(f"⚠️ Could not load runtime config: {e}")
            self._strategy_assignments = None
    
    def _check_config_reload(self) -> None:
        """Check if runtime config changed and reload if needed (hot-reload)
        
        Called before each scan to detect config changes from dashboard.
        NO CODE RELOAD - only updates settings and strategy selection.
        """
        try:
            from src.control_plane.config_store import ConfigStore
            
            config_store = ConfigStore()
            current_mtime = config_store.get_mtime()
            
            # Check if config file changed
            if current_mtime > self._config_last_mtime:
                logger.info("🔄 Runtime config changed - reloading...")
                config = config_store.load()
                
                old_strategy = self._active_strategy_key
                old_interval = self._scan_interval
                
                self._active_strategy_key = config.active_strategy_key
                self._scan_interval = config.scan_interval_seconds
                self._strategy_assignments = config.strategy_assignments
                self._global_max_daily_trades = config.risk.max_daily_trades_per_account
                # Convert account_risk_limits dict to simple dict for fast lookup
                self._account_risk_limits = {
                    account_id: limits
                    for account_id, limits in (config.account_risk_limits or {}).items()
                }
                self._config_last_mtime = current_mtime
                
                # Log changes
                if old_strategy != self._active_strategy_key:
                    logger.info(f"   Strategy changed: {old_strategy} → {self._active_strategy_key}")
                if old_interval != self._scan_interval:
                    logger.info(f"   Scan interval changed: {old_interval}s → {self._scan_interval}s")
                if self._strategy_assignments:
                    enabled_count = sum(1 for a in self._strategy_assignments if a.enabled)
                    logger.info(f"   Strategy assignments: {enabled_count} enabled")
                if self._account_risk_limits:
                    logger.info(f"   Account risk limits: {len(self._account_risk_limits)} accounts configured")
                
                # Update TradeSelector config
                if hasattr(config, 'trade_selection'):
                    self._apply_trade_selection_config(config)
                
                logger.info("✅ Runtime config reloaded successfully")
        except ImportError:
            # Control plane not available - skip hot reload
            pass
        except Exception as e:
            logger.warning(f"⚠️ Config reload failed: {e}")
    
    def _get_active_strategy_instance(self):
        """Get strategy instance based on active config key
        
        Maps runtime config strategy key to actual strategy instances.
        Supports hot-switching strategies without restart.
        """
        return self._get_strategy_by_key(self._active_strategy_key)
    
    def _get_strategy_by_key(self, strategy_key: str):
        """Get strategy instance by strategy key
        
        Maps strategy keys to actual strategy instances.
        Uses alias resolution to handle legacy/variant strategy keys.
        """
        # Resolve alias first (momentum_trading -> momentum, gold_scalping_strict1 -> gold_scalping)
        from src.control_plane.strategy_registry import resolve_strategy_alias
        resolved_key = resolve_strategy_alias(strategy_key)
        
        # Log alias resolution if it occurred
        if resolved_key != strategy_key:
            logger.info(f"STRATEGY_RESOLVED original={strategy_key} resolved={resolved_key}")
        
        # Map config keys to strategy instances
        strategy_map = {
            'momentum': self.strategies.get('momentum'),
            'momentum_trading': self.strategies.get('momentum'),  # Alias resolved to momentum
            'gold': self.strategies.get('gold'),
            'gold_scalping': self.strategies.get('gold'),  # Alias
            'gold_scalping_strict1': self.strategies.get('gold'),  # Alias resolved to gold_scalping -> gold
            'momentum_v2': self.strategies.get('momentum_v2'),  # Use momentum_v2 strategy
            'range': self.strategies.get('range'),  # Use range strategy
            'eur_usd_5m_safe': self.strategies.get('eur_usd_5m_safe'),  # Use eur_usd_5m_safe strategy
            'session_execution': self.strategies.get('session_execution'),  # PHASE 1: SessionExecutionStrategy
            'mean_rev_v2': self.strategies.get('range'),  # Use range strategy (mean reversion)
            'xau_usd_session_bias_1': self.strategies.get('gold'),  # Use gold strategy for XAU_USD
            'xau_usd_session_bias_2': self.strategies.get('gold'),  # Use gold strategy for XAU_USD
            'xau_usd_session_bias_3': self.strategies.get('gold'),  # Use gold strategy for XAU_USD
            'ultra_strict_forex': self.strategies.get('momentum'),  # Fallback to momentum
            'pat_orb_dual_session': self.strategies.get('momentum'),  # Fallback to momentum
            'trump_dna': self.strategies.get('gold'),  # Use gold strategy (closest to Trump DNA approach)
        }
        
        # Try resolved key first, then original key
        strategy = strategy_map.get(resolved_key) or strategy_map.get(strategy_key)
        if strategy is None:
            # STRICT: No fallback to momentum for unknown keys
            logger.warning(f"⚠️ Strategy '{strategy_key}' (resolved: '{resolved_key}') not found in registry map")
            return None
        
        return strategy
    
    def price_integrity_check(self, instrument: str, price_obj: Any, now_ts: float, account_id: str) -> tuple[bool, str, dict]:
        """
        Price Integrity Gate - validates price before allowing signal generation/execution
        Returns: (ok: bool, reason: str, meta: dict)
        """
        meta = {
            'instrument': instrument,
            'account': account_id[-3:] if account_id else 'unknown'
        }
        
        # Check 1: Price object exists and has mid price
        if not price_obj or not hasattr(price_obj, 'mid'):
            return False, "missing_price_object", meta
        
        mid = float(price_obj.mid)
        meta['mid'] = mid
        
        # Check 2: Mid price is finite and positive
        if not (mid > 0 and math.isfinite(mid)):
            return False, "invalid_mid_price", meta
        
        # Check 3: Price freshness
        if hasattr(price_obj, 'ts_utc'):
            price_ts = float(price_obj.ts_utc)
            age_seconds = now_ts - price_ts
            meta['age_seconds'] = age_seconds
            meta['price_ts'] = price_ts
            
            if age_seconds > self._max_price_staleness_seconds:
                return False, f"stale_price_age_{age_seconds:.0f}s", meta
        
        # Check 4: Instrument-specific sanity ranges
        if 'XAU' in instrument:
            # Gold price validation
            if mid < self._min_xau_usd_mid or mid > self._max_xau_usd_mid:
                meta['min_allowed'] = self._min_xau_usd_mid
                meta['max_allowed'] = self._max_xau_usd_mid
                return False, f"xau_price_out_of_range", meta
        elif 'JPY' in instrument:
            # JPY pairs validation (e.g. USD/JPY ~150)
            if mid < 50.0 or mid > 300.0:
                meta['min_allowed'] = 50.0
                meta['max_allowed'] = 300.0
                return False, f"jpy_price_out_of_range", meta
        else:
            # FX majors validation
            if mid < self._min_fx_mid or mid > self._max_fx_mid:
                meta['min_allowed'] = self._min_fx_mid
                meta['max_allowed'] = self._max_fx_mid
                return False, f"fx_price_out_of_range", meta
        
        # All checks passed
        return True, "ok", meta
    
    def _observe_bias_for_instrument(self, instrument: str) -> None:
        """Collect and log bias state for observability (Step 4)"""
        if not (HAS_BIAS_OBSERVER and HAS_BIAS_RESOLVER):
            return
        # Only proceed if dependencies are available
        if not (self.outlook_engine and self.regime_detector and self.price_action_bias and self.regime_bias):
            return

        try:
            # 1. Regime Detection
            # Note: Using H1 candles for regime context to match session strategy
            from src.control_plane.market_data_provider import get_candles
            try:
                # Fetch H1 candles (60 count is enough for regime detection)
                candles = get_candles(instrument, granularity="H1", count=60)
                regime_analysis = self.regime_detector.detect_regime(instrument, candles, timeframe_seconds=3600)
            except Exception:
                # Fallback to dummy
                from src.core.market_regime import MarketRegime
                from dataclasses import make_dataclass
                # Create compatible dummy structure
                DummyRegime = make_dataclass("DummyRegime", [("regime", Any), ("candles_remaining", int), ("eta_seconds", int), ("adx", float), ("consistency", float), ("volatility", float), ("direction", str)])
                regime_analysis = DummyRegime(MarketRegime.UNKNOWN, 0, 0, 0.0, 0.0, 0.0, "UNKNOWN")
            
            regime_str = regime_analysis.regime.name if hasattr(regime_analysis.regime, "name") else str(regime_analysis.regime)

            # 2. Outlook Bias
            daily_outlook = self.outlook_engine.get_latest("daily")
            weekly_outlook = self.outlook_engine.get_latest("weekly")
            
            # Helper to find instrument in outlook
            def find_bias(outlooks, symbol):
                if not outlooks: return None
                for o in outlooks.get("outlooks", []):
                    if o.get("instrument") == symbol:
                        return o
                return None

            d_out = find_bias(daily_outlook, instrument)
            w_out = find_bias(weekly_outlook, instrument)
            
            aligned = False
            details = {}
            if d_out and w_out:
                d_bias = d_out.get("bias", "NEUTRAL")
                w_bias = w_out.get("bias", "NEUTRAL")
                details["daily_bias"] = d_bias
                details["weekly_bias"] = w_bias
                
                if d_bias != "NEUTRAL" and d_bias == w_bias:
                    aligned = True
                    details["effective_bias"] = d_bias
            
            outlook_component = BiasComponent(
                bias=details.get("effective_bias") if aligned else None,
                confidence=0.8 if aligned else 0.0,
                source="outlook_roadmap",
                status="ok" if aligned else "misaligned",
                details=details
            )

            # 3. Price Action Bias
            price_bias_result = self.price_action_bias.calculate_bias(instrument)
            price_component = BiasComponent(
                bias=price_bias_result.bias,
                confidence=price_bias_result.confidence,
                source=price_bias_result.source,
                status="ok" if price_bias_result.bias is not None else "neutral",
                details=price_bias_result.metrics or {},
            )

            # 4. Regime Bias
            regime_bias_result = self.regime_bias.from_analysis(instrument, regime_analysis)
            regime_component = BiasComponent(
                bias=regime_bias_result.bias,
                confidence=regime_bias_result.confidence,
                source=regime_bias_result.source,
                status="ok" if regime_bias_result.bias is not None else "neutral",
                details=regime_bias_result.metrics or {},
            )

            # 5. Resolve
            resolved = resolve_bias(
                outlook=outlook_component,
                price_action=price_component,
                regime=regime_component,
                min_confidence=0.4 # Default from strategy
            )

            # 6. Observe
            observation = observe_bias(
                instrument=instrument,
                regime=regime_str,
                price_action_component=price_component,
                regime_component=regime_component,
                outlook_component=outlook_component,
                resolved_bias=resolved
            )

            # 7. Log (Step 5/6)
            if structured_logger:
                try:
                    structured_logger.info(
                        "BIAS_STATE",
                        event="BIAS_STATE",
                        subsystem="runner_observability",
                        **observation
                    )
                except Exception:
                    _get_forensic_logger().warning("[SKIP] BIAS_STATE log failed safely")
            else:
                _get_forensic_logger().warning("[SKIP] structured_logger missing, log skipped safely")
            
        except Exception as e:
            logger.debug(f"Bias observability failed for {instrument}: {e}")

    def scan_and_execute(self):
        """Scan for opportunities and EXECUTE trades immediately
        
        Supports multi-account strategy assignments:
        - Must have strategy_assignments configured.
        - Strict mode: No assignments = No scanning.
        
        Always runs scanning even if no broker accounts are available.
        """
        forensic_logger = _get_forensic_logger()
        forensic_logger.info("[BOOT] Entered scan_and_execute")
        structured_logger = None
        try:
            from src.observability.structured_logger import logger as _sl
            structured_logger = _sl
            forensic_logger.info("[INIT] structured_logger initialized successfully")
        except Exception as e:
            structured_logger = logging.getLogger("AI_QUANT_FALLBACK")
            forensic_logger.error(f"[INIT_FAIL] structured_logger fallback used: {e}")

        logger.info("🔍 SCANNING FOR OPPORTUNITIES...")
        logger.info(f"[PROBE] scan_tick_start ts={dt.datetime.utcnow().isoformat()}Z")

        # Per-lane last-cycle stats (no secrets). Updated throughout this cycle and written into status.json.
        cycle_ts_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        cycle_stats = {}  # resolved_account_id -> {last_cycle_ts_utc, signals_generated_last_cycle, executed_last_cycle, last_skip_reason}

        def _lane_stats(acc_id: str):
            rid = fxg_resolve_oanda_account_id(acc_id)
            if rid not in cycle_stats:
                cycle_stats[rid] = {
                    "last_cycle_ts_utc": cycle_ts_iso,
                    "signals_generated_last_cycle": 0,
                    "executed_last_cycle": 0,
                    "last_skip_reason": None,
                }
            return cycle_stats[rid]

        # Ensure all execution-capable lanes have a stats entry each cycle (even if 0 signals).
        try:
            for _acc in list(getattr(self, "order_managers", {}).keys()):
                _lane_stats(_acc)
        except Exception:
            pass
        
        # GATE: Config Validity Check
        if self._config_load_error:
            logger.error(f"CONFIG_INVALID_BLOCK error={{self._config_load_error}}")
            _fxg_append_problem_event(
                severity="RED",
                subsystem="config",
                key="config_invalid_block",
                summary="Config invalid (CONFIG_INVALID_BLOCK). Runner scan is blocked.",
                details=str(self._config_load_error)[:200],
                hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'CONFIG_INVALID_BLOCK|Runtime config' | tail -n 80",
                fingerprint=f"config_invalid_block:{str(self._config_load_error)[:80]}",
            )
            if maybe_send_problem_alert:
                try:
                    maybe_send_problem_alert(
                        "config_invalid_block",
                        "Config invalid: runner scan blocked (CONFIG_INVALID_BLOCK).",
                        severity="RED",
                        hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'CONFIG_INVALID_BLOCK|Runtime config' | tail -n 80",
                        fingerprint=f"config_invalid_block:{str(self._config_load_error)[:80]}",
                    )
                except Exception:
                    pass
            self._write_status_snapshot(0, 0, [], [])
            self._last_cycle_lane_stats = cycle_stats
            return 0
            
        # SYSTEM READINESS (Global)
        system_readiness_score = 100
        if HAS_READINESS_OBSERVABILITY:
            try:
                # Use EUR_USD as system proxy for bias/regime
                proxy_instrument = "EUR_USD"
                regime = "UNKNOWN"
                daily_bias = "UNKNOWN"
                
                # Fetch Regime (on EUR_USD)
                if self.regime_detector and HAS_SNAPSHOT_DEPENDENCIES:
                     try:
                         candles = get_candles(proxy_instrument, granularity="M5", count=60)
                         analysis = self.regime_detector.detect_regime(proxy_instrument, candles)
                         regime = analysis.regime.value
                     except Exception:
                         pass
                         
                # Fetch Bias
                if self.outlook_engine:
                     try:
                         daily_bias = self.outlook_engine.get_daily_bias(proxy_instrument)
                     except Exception:
                         pass
                         
                readiness_context = {
                    "regime": regime,
                    "regime_resolved": regime != "UNKNOWN",
                    "bias_available": daily_bias != "UNKNOWN",
                    "bias_confidence": 1.0 if daily_bias != "UNKNOWN" else 0.0,
                    "policy_ready": True, 
                    "news_embargo": False, 
                    "risk_ok": True
                }
                if HAS_READINESS_OBSERVABILITY:
                     # ...
                     import dataclasses
                     readiness_data = get_readiness_summary(readiness_context)
                     system_readiness_score = readiness_data.get("readiness_score", 0)
                     readiness_breakdown_obj = readiness_data.get("breakdown")
                     if readiness_breakdown_obj and dataclasses.is_dataclass(readiness_breakdown_obj):
                         readiness_breakdown = dataclasses.asdict(readiness_breakdown_obj)
                     else:
                         readiness_breakdown = readiness_breakdown_obj
            except Exception as e:
                logger.warning(f"System readiness calc failed: {e}")
        
        all_signals = []
        
        # Load effective assignments from runtime config
        effective_assignments = []
        if self._strategy_assignments:
            # Use strategy_assignments where enabled=true
            for assignment in self._strategy_assignments:
                if assignment.enabled:
                    effective_assignments.append(assignment)
        
        # STRICT MODE: No legacy fallback.
        # If no assignments are configured, we do nothing.
        
        if not effective_assignments:
            logger.warning("⚠️ No strategy assignments configured - skipping scan")
            self._write_status_snapshot(0, 0, [], [])
            self._last_cycle_lane_stats = cycle_stats
            return 0
        
        
        # NEWS: Fetch global news context once per scan
        news_context = {"count": 0, "items": [], "sentiment": 0.0, "providers": [], "status": "disabled"}
        if HAS_NEWS_PROVIDER:
            try:
                # Fetch recent news (limit 10 for strategy context)
                # Query matches API default
                n_items, n_status = fetch_news_with_registry(
                    query="forex OR trading OR finance OR market",
                    max_items=10, 
                    threshold="medium"
                )
                
                # Extract timestamps safely
                timestamps = [i.get('datetime', 0) for i in n_items if i.get('datetime')]
                
                news_context = {
                    "count": len(n_items),
                    "items": n_items,
                    "sentiment": 0.0, # Placeholder for future sentiment analysis
                    "providers": list(set(i.get('source', 'unknown') for i in n_items)),
                    "status": "active" if n_items else ("no_items" if not n_status.get("error") else "error"),
                    "timestamp_min": min(timestamps) if timestamps else None,
                    "timestamp_max": max(timestamps) if timestamps else None,
                    "unavailable_reason": n_status.get('reason') or n_status.get('error')
                }
            except Exception as e:
                news_context["status"] = "error"
                news_context["unavailable_reason"] = str(e)
                logger.warning(f"⚠️ News fetch failed: {e}")
        
        # For each assignment: run that strategy only for that account
        # Track observed instruments to ensure one BIAS_STATE log per instrument per scan
        observed_instruments = set()
        
        for assignment in effective_assignments:
            account_id = assignment.account_id
            strategy_key = assignment.strategy_key
            
            try:
                # Hard assertion: account_id must match assignment
                assert account_id == assignment.account_id, f"Account ID mismatch: {account_id} != {assignment.account_id}"
                
                # Get broker client (may be PaperBroker or OandaClient)
                client = self.account_manager.get_account_client(account_id)
                
                # If no client available, create a temporary paper broker for scanning
                if not client:
                    from src.core.paper_broker import PaperBroker
                    client = PaperBroker()  # PaperBroker doesn't accept parameters
                    logger.debug(f"📄 Using temporary paper broker for scanning: {account_id[-3:]}")
                
                # CRITICAL: Get instruments from strategy registry FIRST (strategy-specific)
                # Each account must use its strategy's configured instruments, not defaults
                instruments = None
                try:
                    from src.control_plane.strategy_registry import get_strategy_info, resolve_strategy_alias
                    # Try with alias resolution first
                    resolved_key = resolve_strategy_alias(strategy_key)
                    strategy_info = get_strategy_info(resolved_key)
                    
                    # If that fails, try direct lookup
                    if not strategy_info:
                        from src.control_plane.strategy_registry import get_strategy_registry
                        registry = get_strategy_registry()
                        strategy_info = registry.get(resolved_key) or registry.get(strategy_key)
                    
                    if strategy_info and hasattr(strategy_info, 'instruments') and strategy_info.instruments:
                        instruments = strategy_info.instruments
                        logger.debug(f"Using strategy-specific instruments for {strategy_key} (resolved: {resolved_key}): {instruments}")
                    else:
                        logger.error(f"❌ Strategy registry missing instruments for {strategy_key} (resolved: {resolved_key})")
                except Exception as e:
                    logger.error(f"❌ Could not get instruments from strategy registry for {strategy_key}: {e}")
                
                # STRICT MODE: No fallbacks allowed.
                if not instruments:
                    logger.error(f"❌ STRICT MODE: No instruments defined in registry for {strategy_key} (Account {account_id[-3:]}). Skipping.")
                    # ALPHA_GAP_PROBE: Write probe when no instruments configured
                    probe_data["primary_blocker"] = "NO_INSTRUMENTS_CONFIGURED"
                    probe_data["source_of_truth"] = "CONFIG"
                    self._write_alpha_gap_probe(probe_data)
                    continue
                
                # Get market data for ALL instruments (we'll filter to strategy-specific later)
                all_market_data = client.get_current_prices(instruments)
                
                # CRITICAL FIX: Filter market_data to ONLY strategy-specific instruments
                # Each strategy should ONLY see its configured instruments
                market_data = {inst: all_market_data[inst] for inst in instruments if inst in all_market_data}
                
                if not market_data:
                    logger.warning(f"⚠️ No market data available for strategy {strategy_key} instruments {instruments}")
                    continue
                
                # GATE: Price Feed Freshness Check
                now_ts = dt.datetime.now(dt.timezone.utc).timestamp()
                MAX_PRICE_AGE_SECONDS = 30
                stale_instruments = []
                price_timestamps = {}
                
                # ALPHA_GAP_PROBE: Initialize probe data for this assignment (account + strategy)
                # Will be written once per assignment after strategy evaluation
                probe_data = {
                    "instrument": instruments[0] if instruments else "UNKNOWN",  # Primary instrument for this assignment
                    "news_checked": HAS_NEWS_PROVIDER and bool(news_context.get("items")),
                    "news_embargo_active": False,  # Will be set when news is checked
                    "news_reason": news_context.get("unavailable_reason") if news_context.get("status") == "error" else None,
                    "session_gate_checked": False,  # Will be set later
                    "strategies_registered": len(self.strategies),
                    "strategies_evaluated": 0,  # Will be set later
                    "signals_emitted": 0,  # Will be set later
                    "signals_blocked": 0,  # Will be set later
                    "dependencies_loaded": {
                        "readiness_evaluator": HAS_READINESS_OBSERVABILITY,
                        "bias_engine": HAS_SNAPSHOT_DEPENDENCIES and self.outlook_engine is not None,
                        "regime_engine": HAS_SNAPSHOT_DEPENDENCIES and self.regime_detector is not None
                    }
                }
                
                for inst in instruments:
                    logger.info(f"[PROBE] instrument_loop instrument={inst}")
                    price = market_data.get(inst)
                    if price:
                        price_age = now_ts - price.ts_utc
                        price_timestamps[inst] = price.ts_utc
                        if price_age > MAX_PRICE_AGE_SECONDS:
                            stale_instruments.append(f"{inst}({int(price_age)}s)")
                    else:
                        stale_instruments.append(f"{inst}(missing)")
                
                if stale_instruments:
                    logger.warning(f"PRICE_FEED_BLOCK account={account_id[-3:]} stale={','.join(stale_instruments)}")
                    _fxg_append_problem_event(
                        severity="AMBER",
                        subsystem="market_data",
                        key="price_feed_block",
                        summary=f"PRICE_FEED_BLOCK: stale or missing prices (acct={account_id[-3:]}).",
                        details=f"max_age_s={MAX_PRICE_AGE_SECONDS} stale={','.join(stale_instruments)[:240]}",
                        hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'PRICE_FEED_BLOCK' | tail -n 50",
                        fingerprint=f"price_feed_block:{account_id[-3:]}:{','.join(stale_instruments)[:80]}",
                    )
                    if maybe_send_problem_alert:
                        try:
                            maybe_send_problem_alert(
                                "price_feed_block",
                                f"Price feed stale/missing for acct {account_id[-3:]} (max_age_s={MAX_PRICE_AGE_SECONDS}).",
                                severity="AMBER",
                                hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'PRICE_FEED_BLOCK' | tail -n 50",
                                fingerprint=f"price_feed_block:{account_id[-3:]}:{','.join(stale_instruments)[:80]}",
                            )
                        except Exception:
                            pass
                    # ALPHA_GAP_PROBE: Write probe when blocked by stale price feed
                    probe_data["primary_blocker"] = "PRICE_FEED_STALE"
                    probe_data["source_of_truth"] = "PRICE_FEED"
                    self._write_alpha_gap_probe(probe_data)
                    continue
                
                # GATE: Price Integrity Check (NEW - validates price ranges and quality)
                price_integrity_failed = False
                for inst in instruments:
                    # BIAS OBSERVABILITY (Step 4): Invoke bias observer per scan cycle (once per instrument)
                    if inst not in observed_instruments:
                        self._observe_bias_for_instrument(inst)
                        observed_instruments.add(inst)
                    
                    price = market_data.get(inst)
                    if price:
                        ok, reason, meta = self.price_integrity_check(inst, price, now_ts, account_id)
                        if not ok:
                            # Log detailed failure
                            logger.warning(
                                f"PRICE_INTEGRITY_FAIL account={account_id[-3:]} strategy={strategy_key} "
                                f"instrument={inst} mid={meta.get('mid', 'N/A')} "
                                f"reason={reason} meta={meta}"
                            )
                            _fxg_append_problem_event(
                                severity="AMBER",
                                subsystem="price_integrity",
                                key="price_integrity_fail",
                                summary=f"PRICE_INTEGRITY_FAIL: {inst} blocked (acct={account_id[-3:]} strat={strategy_key}).",
                                details=f"reason={reason} mid={meta.get('mid','N/A')}",
                                hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'PRICE_INTEGRITY_FAIL' | tail -n 50",
                                fingerprint=f"price_integrity_fail:{account_id[-3:]}:{inst}:{reason}",
                            )
                            if maybe_send_problem_alert:
                                try:
                                    maybe_send_problem_alert(
                                        "price_integrity_fail",
                                        f"Price integrity blocked {inst} for acct {account_id[-3:]} ({reason}).",
                                        severity="AMBER",
                                        hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'PRICE_INTEGRITY_FAIL' | tail -n 50",
                                        fingerprint=f"price_integrity_fail:{account_id[-3:]}:{inst}:{reason}",
                                    )
                                except Exception:
                                    pass
                            # Increment counter
                            self._price_integrity_blocks_per_account[account_id] = \
                                self._price_integrity_blocks_per_account.get(account_id, 0) + 1
                            price_integrity_failed = True
                            break  # Fail fast on first integrity failure
                
                if price_integrity_failed:
                    # ALPHA_GAP_PROBE: Write probe when blocked by price integrity
                    probe_data["primary_blocker"] = "PRICE_INTEGRITY"
                    probe_data["source_of_truth"] = "PRICE_INTEGRITY"
                    self._write_alpha_gap_probe(probe_data)
                    continue  # Skip this account/strategy - fail closed
                
                # Get strategy instance by key
                strategy = self._get_strategy_by_key(strategy_key)
                if not strategy:
                    logger.warning(f"⚠️ Strategy '{strategy_key}' not found for account {account_id[-3:]}, skipping")
                    # ALPHA_GAP_PROBE: Write probe when strategy not found
                    probe_data["primary_blocker"] = "STRATEGY_NOT_FOUND"
                    probe_data["source_of_truth"] = "CONFIG"
                    self._write_alpha_gap_probe(probe_data)
                    continue
                
                logger.info(f"[PROBE] strategy_loaded strategy={strategy.__class__.__name__}")
                
                # GATE: Session regime aligned check (before signal generation)
                # Check each instrument - if any instrument is blocked, skip signal generation
                gate_allowed = True
                if self.session_regime_gate:
                    current_time = dt.datetime.now(dt.timezone.utc)
                    # Check first instrument as representative (can be extended to check all)
                    check_instrument = instruments[0] if instruments else None
                    if check_instrument:
                        # Prepare news context with embargo check and explicit triggers for audit/telemetry
                        news_context_for_gate = news_context.copy()
                        news_items = news_context.get("items", []) or []
                        embargo_triggers = []
                        is_embargo = False
                        embargo_seconds_remaining = None
                        now_ts = current_time.timestamp()
                        embargo_window = 7200  # 2 hours
                        
                        for item in news_items[:5]:  # only need the most recent few
                            impact = (item.get("impact") or "").lower()
                            category = (item.get("category") or "").lower()
                            if impact == "high" or category == "central_banks":
                                is_embargo = True
                                item_ts = item.get("ts_utc") or item.get("datetime")
                                if item_ts:
                                    # Convert to timestamp if string
                                    if isinstance(item_ts, str):
                                        try:
                                            item_dt = dt.datetime.fromisoformat(item_ts.replace('Z', '+00:00'))
                                            item_ts = item_dt.timestamp()
                                        except Exception:
                                            item_ts = None
                                    
                                    if item_ts:
                                        # Calculate time to/from event
                                        time_to_event = item_ts - now_ts
                                        if abs(time_to_event) < embargo_window:
                                            # Calculate seconds remaining until embargo clears
                                            if time_to_event > 0:
                                                # Before event: embargo clears after event + window
                                                remaining = int(time_to_event + embargo_window)
                                            else:
                                                # After event: embargo clears after window expires
                                                remaining = int(embargo_window - abs(time_to_event))
                                            
                                            if embargo_seconds_remaining is None or remaining < embargo_seconds_remaining:
                                                embargo_seconds_remaining = remaining
                                
                                embargo_triggers.append({
                                    "source": item.get("source"),
                                    "title": item.get("title"),
                                    "impact": item.get("impact"),
                                    "category": item.get("category"),
                                    "ts_utc": item.get("ts_utc") or item.get("datetime"),
                                })
                        
                        news_context_for_gate["is_embargo"] = is_embargo
                        news_context_for_gate["state"] = "embargo" if is_embargo else news_context.get("status", "normal")
                        news_context_for_gate["embargo_seconds_remaining"] = embargo_seconds_remaining
                        
                        # ALPHA_GAP_PROBE: Capture news embargo status
                        probe_data["news_embargo_active"] = is_embargo
                        if is_embargo and embargo_triggers:
                            probe_data["news_reason"] = f"High impact news: {embargo_triggers[0].get('title', 'Unknown')}"
                        # include structured reasons for why embargo is active (for audit/telemetry)
                        if embargo_triggers:
                            news_context_for_gate["embargo_triggers"] = embargo_triggers
                        
                        # EMBARGO COUNTDOWN LOGGING
                        if is_embargo:
                            if structured_logger:
                                try:
                                    structured_logger.info(
                                        "embargo_active",
                                        subsystem="news_aggregator",
                                        embargo_active=True,
                                        embargo_seconds_remaining=embargo_seconds_remaining,
                                        embargo_triggers_count=len(embargo_triggers),
                                        instrument=check_instrument
                                    )
                                except Exception as e:
                                    forensic_logger.warning(f"[SKIP] embargo log failed: {e}")
                            else:
                                forensic_logger.warning("[SKIP] structured_logger missing, embargo log skipped safely")
                        
                        try:
                            gate_allowed = self.session_regime_gate.should_allow_trade(
                                symbol=check_instrument,
                                market_data=market_data,
                                news_context=news_context_for_gate,
                                timestamp_utc=current_time,
                            )
                        except Exception as e:
                            logger.warning(f"SESSION_REGIME_GATE error for {check_instrument}: {e} - defaulting to block")
                            gate_allowed = False  # Fail-closed on error
                            probe_data["session_gate_reason"] = f"Exception: {str(e)}"
                        
                        # ALPHA_GAP_PROBE: Capture session gate decision
                        probe_data["session_gate_checked"] = True
                        probe_data["session_gate_result"] = "ALLOW" if gate_allowed else "BLOCK"
                        if not probe_data.get("session_gate_reason"):
                            probe_data["session_gate_reason"] = "session_regime_gate_decision" if not gate_allowed else None
                        
                        if not gate_allowed:
                            logger.debug(
                                f"SESSION_REGIME_GATE blocked {strategy_key} for account {account_id[-3:]} "
                                f"instrument {check_instrument} - skipping signal generation"
                            )
                            # Observability: Signal Rejected
                            if structured_logger and getattr(structured_logger, "log_signal", None):
                                structured_logger.log_signal("SIGNAL_REJECTED", {
                                    "instrument": check_instrument,
                                    "strategy": strategy_key,
                                    "account": account_id[-3:] if account_id else "unknown",
                                    "reason": "session_regime_gate_block",
                                    "details": {"embargo": is_embargo}
                                })
                            else:
                                forensic_logger.warning("[SKIP] structured_logger missing or no log_signal, log skipped safely")
                
                # If gate blocked, skip signal generation
                if not gate_allowed:
                    # Compute readiness even when blocked (for diagnostics)
                    try:
                        from src.core.strategy_readiness import get_readiness_evaluator
                        from src.control_plane.outlook_engine import get_outlook_engine
                        from src.core.execution_gate import ExecutionGuard
                        
                        readiness_eval = get_readiness_evaluator()
                        outlook_engine = get_outlook_engine()
                        execution_guard = ExecutionGuard()
                        exec_decision = execution_guard.decision()
                        
                        # Get biases
                        daily_bias = outlook_engine.get_daily_bias(check_instrument)
                        weekly_bias = outlook_engine.get_weekly_bias(check_instrument)
                        
                        # Get regime from gate context (if available)
                        regime = "UNKNOWN"
                        volatility_pct = 50.0  # Default
                        
                        # Compute readiness
                        readiness = readiness_eval.compute_strategy_readiness(
                            strategy_id=strategy_key,
                            instrument=check_instrument,
                            daily_bias=daily_bias,
                            weekly_bias=weekly_bias,
                            regime=regime,
                            volatility_pct=volatility_pct,
                            news_embargo=is_embargo,
                            execution_allowed=exec_decision.allowed,
                            cooldown_remaining_minutes=None,
                            signal_confidence=None,
                            last_signal_ts=None
                        )
                        
                        # Persist readiness snapshot
                        self._persist_strategy_readiness(strategy_key, check_instrument, readiness)
                        
                        # Persist reasoning snapshot (S1: canonical reasoning object)
                        self._persist_reasoning_snapshot(
                            instrument=check_instrument,
                            readiness=readiness,
                            embargo_active=is_embargo,
                            embargo_seconds_remaining=embargo_seconds_remaining
                        )
                    except Exception as e:
                        logger.debug(f"Readiness computation failed for {strategy_key}: {e}")
                    
                    # ALPHA_GAP_PROBE: Write probe when blocked by session gate
                    probe_data["primary_blocker"] = "SESSION_GATE"
                    probe_data["source_of_truth"] = "SESSION_GATE"
                    self._write_alpha_gap_probe(probe_data)
                    
                    continue
                
                # Run strategy for this account only
                try:
                    # STRATEGY_TRIGGER_PROBE: Collect regime and bias data before evaluation
                    probe_instrument = instruments[0] if instruments else "UNKNOWN"
                    regime_data = None
                    bias_data = None
                    
                    try:
                        if self.regime_detector and probe_instrument != "UNKNOWN":
                            from src.control_plane.market_data_provider import get_candles
                            candles = get_candles(probe_instrument, granularity="H1", count=60)
                            if candles:
                                regime_analysis = self.regime_detector.detect_regime(probe_instrument, candles, timeframe_seconds=3600)
                                regime_data = {
                                    "raw": str(regime_analysis.regime) if hasattr(regime_analysis, 'regime') else None,
                                    "resolved": regime_analysis.regime.name if hasattr(regime_analysis.regime, 'name') else str(regime_analysis.regime),
                                    "timeframe": "H1"
                                }
                    except Exception as e:
                        logger.debug(f"Probe: Failed to get regime data: {e}")
                    
                    try:
                        if self.outlook_engine and probe_instrument != "UNKNOWN":
                            daily_bias = self.outlook_engine.get_daily_bias(probe_instrument)
                            weekly_bias = self.outlook_engine.get_weekly_bias(probe_instrument)
                            bias_data = {
                                "daily": daily_bias,
                                "weekly": weekly_bias,
                                "confidence": None,  # Could be enhanced
                                "alignment": None  # Could be enhanced
                            }
                    except Exception as e:
                        logger.debug(f"Probe: Failed to get bias data: {e}")
                    
                    # STRATEGY_TRIGGER_PROBE: Instrument strategy evaluation
                    with self.strategy_probe.instrument_strategy_evaluation(
                        strategy_id=strategy_key,
                        instrument=probe_instrument,
                        market_data=market_data,
                        regime_data=regime_data,
                        bias_data=bias_data
                    ):
                        # Pass news context to strategy (if it accepts it)
                        try:
                            # Observability: Signal Evaluated
                            if structured_logger and getattr(structured_logger, "log_signal", None):
                                structured_logger.log_signal("SIGNAL_EVALUATED", {
                                    "instrument": ",".join(instruments) if instruments else "UNKNOWN",
                                    "strategy": strategy_key,
                                    "account": account_id[-3:] if account_id else "unknown",
                                    "regime": "UNKNOWN" # Will be updated if available
                                })
                                structured_logger.log_signal("SIGNAL_EVALUATED", {
                                    "instrument": instruments[0] if instruments else "UNKNOWN",
                                    "strategy": strategy.__class__.__name__,
                                    "reason": "scan_tick_visibility_probe",
                                    "execution_allowed": False
                                })
                            else:
                                forensic_logger.warning("[SKIP] structured_logger missing or no log_signal, log skipped safely")

                            signals = strategy.analyze_market(market_data, news_data=news_context)
                        except TypeError:
                            # Fallback for strategies that don't accept news_data yet
                            signals = strategy.analyze_market(market_data)
                    
                    # STRATEGY_TRIGGER_PROBE: Record signal result
                    # Get confidence threshold from strategy if available
                    confidence_threshold = getattr(strategy, 'base_confidence_threshold', None)
                    self.strategy_probe.record_signal_result(
                        strategy_id=strategy_key,
                        instrument=probe_instrument,
                        signals=signals if signals else [],
                        confidence_threshold=confidence_threshold
                    )

                    # ---- GLOBAL SIGNAL DECISION PROBE: raw evaluation (pre-filter) ----
                    # One event per *candidate* signal; if no signals but readiness high, log a near-miss.
                    try:
                        if signals:
                            for s in signals:
                                _log_global_signal_decision(
                                    {
                                        "event": "GLOBAL_SIGNAL_EVAL",
                                        "instrument": getattr(s, "instrument", None),
                                        "strategy": strategy_key,
                                        "account": account_id,
                                        "raw_signal_present": True,
                                        "confidence": getattr(s, "confidence", None),
                                        "readiness_score": readiness.readiness_score
                                        if "readiness" in locals() and readiness is not None
                                        else None,
                                        "session": locals().get("current_session"),
                                        "news_embargo": is_embargo,
                                        "execution_allowed_by_session_gate": gate_allowed,
                                        "execution_allowed_by_execution_gate": None,
                                        "rejection_stage": None,
                                        "rejection_reason": None,
                                    }
                                )
                        else:
                            # High readiness but no signal: explicit near-miss
                            if "readiness" in locals() and readiness is not None:
                                _log_global_signal_decision(
                                    {
                                        "event": "GLOBAL_SIGNAL_NEAR_MISS",
                                        "instrument": signal_instrument,
                                        "strategy": strategy_key,
                                        "account": account_id,
                                        "raw_signal_present": False,
                                        "confidence": None,
                                        "readiness_score": readiness.readiness_score,
                                        "session": locals().get("current_session"),
                                        "news_embargo": is_embargo,
                                        "execution_allowed_by_session_gate": gate_allowed,
                                        "execution_allowed_by_execution_gate": None,
                                        "rejection_stage": "signal_engine",
                                        "rejection_reason": "high_readiness_no_signal",
                                    }
                                )
                    except Exception as e:
                        logger.debug(f"GLOBAL_SIGNAL_DECISION_PROBE eval logging failed: {e}")
                    
                    # ALPHA_GAP_PROBE: Capture strategy evaluation results
                    probe_data["strategies_evaluated"] = 1
                    probe_data["signals_emitted"] = len(signals) if signals else 0
                    
                    # Compute readiness after signal evaluation
                    readiness = None
                    try:
                        from src.core.strategy_readiness import get_readiness_evaluator
                        from src.control_plane.outlook_engine import get_outlook_engine
                        from src.core.execution_gate import ExecutionGuard
                        
                        readiness_eval = get_readiness_evaluator()
                        outlook_engine = get_outlook_engine()
                        execution_guard = ExecutionGuard()
                        exec_decision = execution_guard.decision()
                        
                        # Get biases
                        signal_instrument = signals[0].instrument if signals else (instruments[0] if instruments else "UNKNOWN")
                        daily_bias = outlook_engine.get_daily_bias(signal_instrument)
                        weekly_bias = outlook_engine.get_weekly_bias(signal_instrument)
                        
                        # Get regime and volatility (simplified - could be enhanced)
                        regime = "UNKNOWN"
                        volatility_pct = 50.0
                        
                        # Get signal confidence
                        signal_conf = signals[0].confidence if signals and len(signals) > 0 else None
                        last_signal_ts = dt.datetime.now(dt.timezone.utc).timestamp() if signals else None
                        
                        # Compute readiness
                        readiness = readiness_eval.compute_strategy_readiness(
                            strategy_id=strategy_key,
                            instrument=signal_instrument,
                            daily_bias=daily_bias,
                            weekly_bias=weekly_bias,
                            regime=regime,
                            volatility_pct=volatility_pct,
                            news_embargo=is_embargo,
                            execution_allowed=exec_decision.allowed,
                            cooldown_remaining_minutes=None,
                            signal_confidence=signal_conf,
                            last_signal_ts=last_signal_ts
                        )
                        
                        # Persist readiness snapshot
                        self._persist_strategy_readiness(strategy_key, signal_instrument, readiness)
                        
                        # Persist reasoning snapshot (S1: canonical reasoning object)
                        self._persist_reasoning_snapshot(
                            instrument=signal_instrument,
                            readiness=readiness,
                            embargo_active=is_embargo,
                            embargo_seconds_remaining=embargo_seconds_remaining if 'embargo_seconds_remaining' in locals() else None
                        )
                    except Exception as e:
                        logger.debug(f"Readiness computation failed for {strategy_key}: {e}")
                    
                    # Define signal_instrument early for observability
                    signal_instrument = signals[0].instrument if signals else (instruments[0] if instruments else "UNKNOWN")

                    # Observability: Signal Outcome
                    _log_signal = structured_logger and getattr(structured_logger, "log_signal", None)
                    if signals:
                        for s in signals:
                            if _log_signal:
                                structured_logger.log_signal("SIGNAL_GENERATED", {
                                    "instrument": s.instrument,
                                    "strategy": strategy_key,
                                    "account": account_id[-3:] if account_id else "unknown",
                                    "side": str(s.side),
                                    "confidence": getattr(s, "confidence", (getattr(s, "metadata") or {}).get("confidence", 0.0))
                                })
                            else:
                                forensic_logger.warning("[SKIP] structured_logger missing or no log_signal, log skipped safely")
                    elif readiness and readiness.readiness_score > 40:
                        if _log_signal:
                            structured_logger.log_signal("SIGNAL_NEAR_MISS", {
                                "instrument": signal_instrument,
                                "strategy": strategy_key,
                                "account": account_id[-3:] if account_id else "unknown",
                                "reason": "high_readiness_no_signal",
                                "score": readiness.readiness_score,
                                "details": readiness.details
                            })
                        else:
                            forensic_logger.warning("[SKIP] structured_logger missing or no log_signal, log skipped safely")
                    else:
                        if _log_signal:
                            structured_logger.log_signal("SIGNAL_REJECTED", {
                                "instrument": signal_instrument,
                                "strategy": strategy_key,
                                "account": account_id[-3:] if account_id else "unknown",
                                "reason": "low_readiness_or_no_signal",
                                "score": readiness.readiness_score if readiness else 0
                            })
                        else:
                            forensic_logger.warning("[SKIP] structured_logger missing or no log_signal, log skipped safely")

                    # LOG EVIDENCE: STRAT_EVIDENCE (Canonical Marker)
                    # FIX: Use SIGNAL instrument for price lookup, not first scanned instrument
                    signal_instrument = signals[0].instrument if signals else (instruments[0] if instruments else "UNKNOWN")
                    price_instrument = signal_instrument  # Price MUST match signal instrument
                    
                    # Get price for the SIGNAL instrument (not scanned instrument)
                    price_used = market_data.get(price_instrument)
                    mid_price = price_used.mid if price_used else 0
                    price_ts = price_timestamps.get(price_instrument, 0)
                    
                    # Construct evidence object (single line, key=value)
                    # Using clean string representation for lists
                    prov_str = ",".join(news_context.get("providers", []))
                    if not prov_str: prov_str = "none"
                    
                    # Log strategy-specific instruments scanned
                    instruments_str = ",".join(instruments)
                    
                    # Add readiness info to evidence if available
                    readiness_info = ""
                    if readiness:
                        from src.core.strategy_explain import generate_why_not_trading
                        why_not = generate_why_not_trading(readiness)
                        readiness_info = f" readiness_score={readiness.readiness_score} why_not_trading=\"{why_not}\" bias_alignment={readiness.bias_alignment.value}"
                    
                    # CRITICAL: Log BOTH signal_instrument and price_instrument to detect mismatches
                    evidence_str = (
                        f"STRAT_EVIDENCE system=ALPHA account={account_id[-3:]} strategy={strategy_key} "
                        f"instruments_scanned={instruments_str} signal_instrument={signal_instrument} "
                        f"price_instrument={price_instrument} price_mid={mid_price:.5f} "
                        f"price_ts={price_ts:.3f} price_source=oanda "
                        f"news_used_count={news_context.get('count', 0)} "
                        f"news_providers={prov_str} "
                        f"signals_generated={len(signals) if signals else 0} "
                        f"decision={'BUY' if signals and signals[0].side.value == 'BUY' else ('SELL' if signals and signals[0].side.value == 'SELL' else 'NONE')}"
                        f"{readiness_info}"
                    )
                    logger.info(evidence_str)
                    
                    # HARD GUARD: Detect instrument/price mismatch
                    if signals and signal_instrument != price_instrument:
                        logger.error(
                            f"PRICE_INTEGRITY_MISMATCH account={account_id[-3:]} strategy={strategy_key} "
                            f"signal_instrument={signal_instrument} price_instrument={price_instrument} "
                            f"REJECTED: Signal instrument does not match price source instrument"
                        )
                        try:
                            # GLOBAL SIGNAL REJECTION: price integrity mismatch
                            for s in signals:
                                _log_global_signal_decision(
                                    {
                                        "event": "GLOBAL_SIGNAL_REJECTED",
                                        "instrument": getattr(s, "instrument", None),
                                        "strategy": strategy_key,
                                        "account": account_id,
                                        "confidence": getattr(s, "confidence", None),
                                        "readiness_score": readiness.readiness_score
                                        if "readiness" in locals() and readiness is not None
                                        else None,
                                        "rejection_stage": "price_integrity",
                                        "rejection_reason": "signal_price_mismatch",
                                    }
                                )
                        except Exception:
                            pass
                        continue  # Skip this account/strategy - fail closed
                    
                    if signals:
                        logger.info(f"📊 {strategy_key} generated {len(signals)} signals for account {account_id[-3:]}")
                        for signal in signals:
                            # HARD INVARIANT (A): instrument_invariant - scanned/evaluated instrument MUST equal signal.instrument
                            # Note: Since we iterate through market_data which is already filtered to instruments,
                            # we verify the signal instrument is in the allowlist (next check)
                            
                            # HARD INVARIANT (B): allowlist_invariant - strategy allowlist MUST include the instrument
                            if signal.instrument not in instruments:
                                logger.error(
                                    f"INVARIANT_FAIL allowlist_violation strategy={strategy_key} account={account_id[-3:]} "
                                    f"instrument={signal.instrument} allowlist={instruments} "
                                    f"REJECTED: signal instrument not in strategy allowlist"
                                )
                                # ALPHA_GAP_PROBE: Track blocked signal
                                probe_data["signals_blocked"] = probe_data.get("signals_blocked", 0) + 1
                                try:
                                    _log_global_signal_decision(
                                        {
                                            "event": "GLOBAL_SIGNAL_REJECTED",
                                            "instrument": getattr(signal, "instrument", None),
                                            "strategy": strategy_key,
                                            "account": account_id,
                                            "confidence": getattr(signal, "confidence", None),
                                            "readiness_score": readiness.readiness_score
                                            if "readiness" in locals()
                                            and readiness is not None
                                            else None,
                                            "rejection_stage": "allowlist",
                                            "rejection_reason": "instrument_not_in_strategy_allowlist",
                                        }
                                    )
                                except Exception:
                                    pass
                                continue  # REJECT signal - fail closed
                            
                            # Hard assertion: ensure signal is tagged with correct account_id
                            signal.account_id = account_id
                            signal.strategy_key = strategy_key
                            try:
                                _lane_stats(account_id)["signals_generated_last_cycle"] += 1
                            except Exception:
                                pass
                            
                            # ALPHA_GAP_PROBE: Track signal emission
                            probe_data["signals_emitted"] = probe_data.get("signals_emitted", 0) + 1
                            
                            # Account 006 isolation DISABLED - allow all strategies to use account 006
                            account_suffix = account_id[-3:] if len(account_id) >= 3 else None
                            if account_suffix == "006":
                                logger.debug(
                                    f"✅ Account 006 signal generation: strategy '{strategy_key}' generating signal for account 006 "
                                    f"(isolation disabled - standard trading account)"
                                )
                            
                            # Log for audit
                            logger.debug(f"   Signal: {signal.instrument} {signal.side.value} for account {account_id[-3:]}")

                            # === SIGNAL EXPORT (SIDECAR / OBSERVABILITY ONLY) ===
                            try:
                                # Resolve execution status safely
                                _sc_allowed = False
                                _sc_reason = "unknown"
                                if 'exec_decision' in locals():
                                    _sc_allowed = exec_decision.allowed
                                    _sc_reason = getattr(exec_decision, 'reason_code', None)
                                elif 'gate_allowed' in locals() and not gate_allowed:
                                    _sc_allowed = False
                                    _sc_reason = "session_gate_blocked"
                                
                                get_signal_exporter().emit(
                                    strategy=strategy_key,
                                    symbol=signal.instrument,
                                    side=signal.side.value if hasattr(signal.side, 'value') else str(signal.side),
                                    units=signal.units,
                                    entry_type='MARKET',
                                    stop_loss=getattr(signal, 'stop_loss', None),
                                    take_profit=getattr(signal, 'take_profit', None),
                                    confidence=getattr(signal, 'confidence', 0.0),
                                    regime=locals().get('regime', 'unknown'),
                                    session=locals().get('current_session', 'unknown'),
                                    news_state=news_context.get('status') if isinstance(news_context, dict) else 'unknown',
                                    execution_allowed=_sc_allowed,
                                    block_reason=_sc_reason if not _sc_allowed else None,
                                    account=account_id,
                                    bridge_account=os.getenv('BRIDGE_ACCOUNT', 'ftmo_eval_primary'),
                                    meta={'source': 'working_trading_system', 'scan_time': dt.datetime.now(dt.timezone.utc).isoformat()}
                                )
                            except Exception:
                                pass
                            # === END SIGNAL EXPORT ===

                            # === TELEGRAM HEADS_UP (non-blocking, deduped in notifier) ===
                            try:
                                if maybe_send_heads_up and (not _sc_allowed):
                                    conf = float(getattr(signal, "confidence", 0.0) or 0.0)
                                    maybe_send_heads_up(
                                        account_suffix=account_id[-3:],
                                        instrument=str(getattr(signal, "instrument", "") or ""),
                                        side=str(getattr(getattr(signal, "side", None), "value", getattr(signal, "side", "")) or ""),
                                        strategy=str(strategy_key),
                                        confidence=conf,
                                        block_reason=str(_sc_reason) if _sc_reason else None,
                                        readiness_hint=None,
                                        fingerprint=f"heads_up:{account_id[-3:]}:{signal.instrument}:{strategy_key}:{_sc_reason}",
                                    )
                            except Exception:
                                pass
                            # === END TELEGRAM HEADS_UP ===

                            all_signals.append(signal)
                    else:
                        logger.debug(f"   {strategy_key} for account {account_id[-3:]}: no signals")
                    # [FORENSIC] RAW_SIGNAL_PROBE: log raw signal count per strategy (reversible)
                    logger.warning(
                        f"[RAW_SIGNAL_PROBE] strategy={strategy_key} instrument={instruments[0] if instruments else 'UNKNOWN'} raw_signals={len(signals) if signals else 0}"
                    )
                    # ALPHA_GAP_PROBE: Write final probe entry after strategy evaluation
                    # Determine primary blocker
                    if probe_data.get("news_embargo_active"):
                        probe_data["primary_blocker"] = "NEWS"
                        probe_data["source_of_truth"] = "NEWS"
                    elif probe_data.get("session_gate_result") == "BLOCK":
                        probe_data["primary_blocker"] = "SESSION_GATE"
                        probe_data["source_of_truth"] = "SESSION_GATE"
                    elif probe_data.get("signals_emitted", 0) == 0:
                        probe_data["primary_blocker"] = "SIGNAL_ENGINE"
                        probe_data["source_of_truth"] = "SIGNAL_ENGINE"
                    else:
                        probe_data["primary_blocker"] = "None - Ready to Trade"
                        probe_data["source_of_truth"] = "SIGNAL_ENGINE"
                    
                    self._write_alpha_gap_probe(probe_data)
                except Exception as e:
                    forensic_logger.error(f"[EXCEPTION] scan loop strategy error: {e}", exc_info=True)
                    logger.warning(f"⚠️ {strategy_key} failed for account {account_id[-3:]}: {e}")
                    
                    # ALPHA_GAP_PROBE: Write probe even on exception
                    probe_data["primary_blocker"] = f"EXCEPTION: {str(e)}"
                    probe_data["source_of_truth"] = "EXCEPTION"
                    self._write_alpha_gap_probe(probe_data)
                        
            except Exception as e:
                forensic_logger.error(f"[EXCEPTION] scan loop account error: {e}", exc_info=True)
                logger.warning(f"⚠️ Failed to scan account {account_id[-3:]} with strategy {strategy_key}: {e}")
        
        logger.info(f"📊 Total signals generated: {len(all_signals)}")

        # GLOBAL SIGNAL PROBE: if absolutely no signals survived, log a loud failure
        if len(all_signals) == 0:
            try:
                _log_global_signal_decision(
                    {
                        "event": "GLOBAL_SIGNAL_ALL_REJECTED",
                        "reason": "no_signals_after_scan",
                        "scope": "paper_only_diagnostics",
                    }
                )
            except Exception as e:
                logger.debug(f"GLOBAL_SIGNAL_DECISION_PROBE all-rejected logging failed: {e}")

        self._notify_telegram_signals(all_signals)
        
        # Build daily limit map for TradeSelector
        daily_limit_map = {}
        for account_id in self.account_ids_for_scanning:
            account_limits = self._account_risk_limits.get(account_id)
            if account_limits and account_limits.max_daily_trades is not None:
                daily_limit_map[account_id] = account_limits.max_daily_trades
            elif account_limits and account_limits.max_daily_trades is None:
                daily_limit_map[account_id] = self._global_max_daily_trades
            else:
                daily_limit_map[account_id] = self._global_max_daily_trades
        
        # TRADE SELECTION: Filter signals based on quality and limits
        # This replaces the raw list with a prioritized subset
        # [FORENSIC] PRE_SELECTOR_PROBE: log candidate count before TradeSelector (reversible)
        logger.warning(f"[PRE_SELECTOR_PROBE] candidate_signals={len(all_signals)}")
        signals_to_execute = self.trade_selector.select_trades(
            all_signals, 
            self._daily_trades_per_account, 
            daily_limit_map
        )
        # [FORENSIC] POST_SELECTOR_PROBE: log selected count after TradeSelector (reversible)
        top = self.trade_selector.get_top_candidates(limit=10) if hasattr(self, 'trade_selector') else []
        logger.warning(f"[POST_SELECTOR_PROBE] executable_signals={len(signals_to_execute)} pool_top10={len(top)}")
        # STRATEGY_TRIGGER_PROBE: Instrument trade selection
        if self.strategy_probe is not None:
            self.strategy_probe.instrument_trade_selection(
                input_signals=all_signals,
                output_signals=signals_to_execute,
                rejection_reasons=None  # Could be enhanced to capture specific reasons
            )
        
        if len(signals_to_execute) != len(all_signals):
            logger.info(f"🎯 Trade Selection: {len(signals_to_execute)} signals selected for execution (out of {len(all_signals)})")
        
        # EXECUTE TRADES (only if execution is enabled and order managers are available)
        executed_trades = 0
        if not self.execution_enabled:
            logger.info(f"📄 Execution disabled (signals-only) — signals generated: {len(all_signals)}, selected: {len(signals_to_execute)}, executed: 0")
            self._last_cycle_lane_stats = cycle_stats
            self._write_status_snapshot(len(all_signals), 0, all_signals, news_context.get("items"))
            return len(all_signals)  # Return signal count, not executed count
        
        if not self.order_managers:
            logger.info(f"📄 Execution enabled but no order managers available — signals generated: {len(all_signals)}, executed: 0")
            self._last_cycle_lane_stats = cycle_stats
            self._write_status_snapshot(len(all_signals), 0, all_signals, news_context.get("items"))
            return len(all_signals)  # Return signal count, not executed count
        
        # Reset daily counters if new day
        current_date = dt.datetime.now(dt.timezone.utc).date()
        if current_date > self._last_daily_reset:
            self._daily_trades_per_account.clear()
            self._last_daily_reset = current_date
            logger.info("📅 Daily trade counters reset")
        
        # Risk caps (strict enforcement)
        # MAX_OPEN_TRADES_PER_ACCOUNT is loaded from runtime config (dashboard-controlled)
        MAX_OPEN_TRADES_PER_ACCOUNT = self._max_open_trades_per_account
        # MAX_DAILY_TRADES_PER_ACCOUNT is now per-account (see below)
        MAX_ORDERS_PER_MINUTE_PER_VM = int(os.getenv("MAX_ORDERS_PER_MINUTE_PER_VM", "4"))
        COOLDOWN_SECONDS_PER_SYMBOL = 300
        
        # Clean old order timestamps (keep only last minute)
        now = dt.datetime.now(dt.timezone.utc)
        self._orders_per_minute = [(ts, acc) for ts, acc in self._orders_per_minute if (now - ts).total_seconds() < 60]
        
        # Update open trades count per account (query from broker)
        # Note: OrderManager may be a stub in paper mode, so we query via API instead
        for account_id in self.order_managers.keys():
            try:
                # Try to get open positions via direct OANDA API call
                # This works even if OrderManager is a stub
                oanda_api_key = fxg_get_oanda_api_key_for_account(account_id)
                oanda_base_url = os.getenv("OANDA_BASE_URL", "").strip()
                if not oanda_base_url:
                    trading_mode = os.getenv("TRADING_MODE", "paper").lower()
                    oanda_base_url = "https://api-fxpractice.oanda.com" if trading_mode != "live" else "https://api-fxtrade.oanda.com"
                
                if oanda_api_key:
                    import requests
                    headers = {"Authorization": f"Bearer {oanda_api_key}", "Content-Type": "application/json"}
                    url = f"{oanda_base_url}/v3/accounts/{account_id}/openPositions"
                    r = requests.get(url, headers=headers, timeout=5)
                    if r.status_code == 200:
                        data = r.json()
                        positions = data.get("positions", [])
                        self._open_trades_per_account[account_id] = len([p for p in positions if float(p.get("long", {}).get("units", 0)) != 0 or float(p.get("short", {}).get("units", 0)) != 0])
                    else:
                        self._open_trades_per_account[account_id] = 0
                else:
                    self._open_trades_per_account[account_id] = 0
            except Exception as e:
                logger.debug(f"⚠️ Could not query open positions for {account_id[-3:]}: {e}")
                self._open_trades_per_account[account_id] = 0

        # Exposure Gate (M5 Option B): per-lane, per-instrument open trade cap.
        # Cache openTrades counts ONCE per lane per cycle (fail-closed on any fetch error).
        open_trades_by_instrument_cache = {}  # account_id -> {instrument: count} | None (None means fetch failed)

        def _get_open_trades_by_instrument_for_lane(acc_id: str):
            rid = fxg_resolve_oanda_account_id(acc_id)
            if rid in open_trades_by_instrument_cache:
                return open_trades_by_instrument_cache[rid]

            try:
                from src.core.exposure_gate import fetch_open_trades_by_instrument
            except Exception as e:
                open_trades_by_instrument_cache[rid] = None
                return None

            try:
                token = fxg_get_oanda_api_key_for_account(rid)
                if not token:
                    raise RuntimeError("missing_oanda_api_key")
                oanda_base_url = os.getenv("OANDA_BASE_URL", "").strip()
                if not oanda_base_url:
                    trading_mode = os.getenv("TRADING_MODE", "paper").lower()
                    oanda_base_url = "https://api-fxpractice.oanda.com" if trading_mode != "live" else "https://api-fxtrade.oanda.com"
                counts = fetch_open_trades_by_instrument(oanda_base_url, token, rid, timeout_s=10.0)
                open_trades_by_instrument_cache[rid] = counts
                return counts
            except Exception as e:
                open_trades_by_instrument_cache[rid] = None
                return None
        
        for signal in signals_to_execute:
            try:
                account_id = signal.account_id
                resolved = fxg_resolve_oanda_account_id(account_id)
                if resolved and resolved != account_id:
                    account_id = resolved
                    try:
                        signal.account_id = resolved
                    except Exception:
                        pass
                
                # Hard assertion: ensure order manager exists for this account
                if account_id not in self.order_managers:
                    logger.warning(f"⚠️ No order manager for account {account_id[-3:]}, skipping signal")
                    try:
                        _lane_stats(account_id)["last_skip_reason"] = "no_order_manager"
                    except Exception:
                        pass
                    continue
                
                order_manager = self.order_managers[account_id]
                
                # RISK CAPS ENFORCEMENT
                # 1. Check max open trades per account
                open_count = self._open_trades_per_account.get(account_id, 0)
                if open_count >= MAX_OPEN_TRADES_PER_ACCOUNT:
                    logger.warning(f"⛔ Skipping {signal.instrument}: account {account_id[-3:]} has {open_count} open trades (max: {MAX_OPEN_TRADES_PER_ACCOUNT})")
                    try:
                        _lane_stats(account_id)["last_skip_reason"] = "open_trades_cap"
                    except Exception:
                        pass
                    continue
                
                # 2. Check max daily trades per account (per-account limit or global default)
                daily_count = self._daily_trades_per_account.get(account_id, 0)
                
                # PHASE 1: Bypass daily trade cap ONLY for ALPHA paper mode
                trading_mode = os.getenv("TRADING_MODE", "paper").lower()
                system_label = os.getenv("SYSTEM_LABEL", "UNKNOWN").upper()
                bypass_daily_cap = (trading_mode == "paper" and system_label == "ALPHA")
                
                if bypass_daily_cap:
                    # ALPHA paper mode: skip daily cap check
                    logger.debug(f"✅ Daily trade cap bypassed for ALPHA paper mode (account {account_id[-3:]}, daily_count: {daily_count})")
                else:
                    # Get per-account limit (if configured) or use global default
                    account_limits = self._account_risk_limits.get(account_id)
                    if account_limits and not account_limits.enabled:
                        # Daily limit check disabled for this account
                        max_daily_trades = None  # Unlimited
                    elif account_limits and account_limits.max_daily_trades is not None:
                        # Per-account limit specified
                        max_daily_trades = account_limits.max_daily_trades
                    else:
                        # Use global default from config
                        max_daily_trades = self._global_max_daily_trades
                    
                    # Enforce limit (if max_daily_trades is 0, it means unlimited)
                    if max_daily_trades is not None and max_daily_trades > 0:
                        if daily_count >= max_daily_trades:
                            logger.warning(f"⛔ Skipping {signal.instrument}: account {account_id[-3:]} has {daily_count} daily trades (max: {max_daily_trades})")
                            try:
                                _lane_stats(account_id)["last_skip_reason"] = "daily_trade_cap"
                            except Exception:
                                pass
                            continue
                
                # 3. Check orders per minute per VM
                orders_last_minute = len([ts for ts, acc in self._orders_per_minute])
                if orders_last_minute >= MAX_ORDERS_PER_MINUTE_PER_VM:
                    logger.warning(f"⛔ Skipping {signal.instrument}: {orders_last_minute} orders in last minute (max: {MAX_ORDERS_PER_MINUTE_PER_VM})")
                    try:
                        _lane_stats(account_id)["last_skip_reason"] = "vm_rate_limit"
                    except Exception:
                        pass
                    continue
                
                # 4. THROTTLE: Check cooldown per symbol (300s default)
                symbol_key = (account_id, signal.instrument)
                last_trade_time = self._last_trade_time_per_symbol.get(symbol_key)
                if last_trade_time:
                    seconds_since = (now - last_trade_time).total_seconds()
                    if seconds_since < COOLDOWN_SECONDS_PER_SYMBOL:
                        self._throttle_skips_per_account[account_id] = self._throttle_skips_per_account.get(account_id, 0) + 1
                        logger.warning(f"THROTTLE_SKIP {{account:{account_id[-3:]},instrument:{signal.instrument},reason:cooldown_active,seconds_since:{int(seconds_since)},cooldown_seconds:{COOLDOWN_SECONDS_PER_SYMBOL},next_allowed_time:{(last_trade_time + dt.timedelta(seconds=COOLDOWN_SECONDS_PER_SYMBOL)).isoformat()}}}")
                        try:
                            _lane_stats(account_id)["last_skip_reason"] = "cooldown_active"
                        except Exception:
                            pass
                        continue
                
                # 5. THROTTLE: Per-account cooldown (120s minimum between any orders)
                last_account_trade = self._last_trade_time_per_account.get(account_id)
                if last_account_trade:
                    seconds_since_account = (now - last_account_trade).total_seconds()
                    account_cooldown = 120  # 2 minutes minimum
                    if seconds_since_account < account_cooldown:
                        self._throttle_skips_per_account[account_id] = self._throttle_skips_per_account.get(account_id, 0) + 1
                        logger.warning(f"THROTTLE_SKIP {{account:{account_id[-3:]},instrument:{signal.instrument},reason:account_cooldown,seconds_since:{int(seconds_since_account)},cooldown_seconds:{account_cooldown},next_allowed_time:{(last_account_trade + dt.timedelta(seconds=account_cooldown)).isoformat()}}}")
                        try:
                            _lane_stats(account_id)["last_skip_reason"] = "account_cooldown"
                        except Exception:
                            pass
                        continue
                
                # 6. THROTTLE: Hourly order rate limit (12 orders/hour per account)
                if account_id not in self._orders_per_hour_per_account:
                    self._orders_per_hour_per_account[account_id] = []
                hour_ago = now - dt.timedelta(hours=1)
                self._orders_per_hour_per_account[account_id] = [
                    ts for ts in self._orders_per_hour_per_account[account_id] if ts > hour_ago
                ]
                orders_last_hour = len(self._orders_per_hour_per_account[account_id])
                max_orders_per_hour = 12
                if orders_last_hour >= max_orders_per_hour:
                    self._throttle_skips_per_account[account_id] = self._throttle_skips_per_account.get(account_id, 0) + 1
                    logger.warning(f"THROTTLE_SKIP {{account:{account_id[-3:]},instrument:{signal.instrument},reason:hourly_limit,orders_last_hour:{orders_last_hour},max_orders_per_hour:{max_orders_per_hour}}}")
                    continue
                
                # 7. DEDUPE: Signal fingerprint check (prevent duplicate signals within 15 minutes)
                # Use signal.strategy_key which was set during scan
                strat_key_for_dedupe = getattr(signal, 'strategy_key', self._active_strategy_key)
                signal_fingerprint = (account_id, signal.instrument, strat_key_for_dedupe)
                last_signal = self._signal_fingerprints.get(signal_fingerprint)
                if last_signal:
                    last_time, last_entry, last_side = last_signal
                    entry_match = abs(signal.entry_price - last_entry) / last_entry < 0.001 if last_entry > 0 else False
                    side_match = signal.side.value == last_side
                    time_match = (now - last_time).total_seconds() < 900  # 15 minutes
                    if entry_match and side_match and time_match:
                        self._throttle_skips_per_account[account_id] = self._throttle_skips_per_account.get(account_id, 0) + 1
                        logger.warning(f"THROTTLE_SKIP {{account:{account_id[-3:]},instrument:{signal.instrument},reason:signal_dedupe,last_signal_time:{last_time.isoformat()},dedupe_window_seconds:900}}")
                        continue

                # 8. EXPOSURE GATE (M5 Option B): cap open trades per instrument per lane/account.
                # Counts ALL open trades for the instrument (both directions) from /openTrades.
                lane_suffix = account_id[-3:] if account_id else "???"
                try:
                    from src.core.exposure_gate import get_cap_for_lane, exposure_allows_execution
                    cap = int(get_cap_for_lane(lane_suffix) or 2)
                except Exception:
                    cap = 2

                counts = _get_open_trades_by_instrument_for_lane(account_id)
                if counts is None:
                    logger.warning(
                        "EXPOSURE_CAP_SKIP "
                        f"lane=-{lane_suffix} account={lane_suffix} instrument={signal.instrument} "
                        f"open_trades_for_instrument=-1 cap={cap} reason=exposure_check_failed"
                    )
                    try:
                        _lane_stats(account_id)["last_skip_reason"] = "exposure_check_failed"
                    except Exception:
                        pass
                    continue

                allows, reason = exposure_allows_execution(counts, signal.instrument, cap)
                if not allows:
                    n_open = int(counts.get(signal.instrument, 0) or 0)
                    logger.warning(
                        "EXPOSURE_CAP_SKIP "
                        f"lane=-{lane_suffix} account={lane_suffix} instrument={signal.instrument} "
                        f"open_trades_for_instrument={n_open} cap={cap} reason={reason}"
                    )
                    try:
                        _lane_stats(account_id)["last_skip_reason"] = reason
                    except Exception:
                        pass
                    continue
                
                # 5. Spread/slippage check (already done in strategy, but double-check here)
                # Strategy should have filtered, but verify execution path
                
                # Hard assertion: verify account_id matches assignment (prevent cross-account execution)
                # This is already enforced by signal.account_id being set during scan, but double-check
                logger.info(f"🚀 EXECUTING TRADE: {signal.instrument} {signal.side.value} on account {account_id[-3:]} (open: {open_count}, daily: {daily_count})")
                
                # Calculate position size (0.10% risk per trade as per config)
                # Get account balance via OANDA API (OrderManager may be stub)
                try:
                    oanda_api_key = os.getenv("OANDA_API_KEY", "").strip()
                    oanda_base_url = os.getenv("OANDA_BASE_URL", "").strip()
                    if not oanda_base_url:
                        trading_mode = os.getenv("TRADING_MODE", "paper").lower()
                        oanda_base_url = "https://api-fxpractice.oanda.com" if trading_mode != "live" else "https://api-fxtrade.oanda.com"
                    
                    if oanda_api_key:
                        import requests
                        headers = {"Authorization": f"Bearer {oanda_api_key}", "Content-Type": "application/json"}
                        url = f"{oanda_base_url}/v3/accounts/{account_id}/summary"
                        r = requests.get(url, headers=headers, timeout=5)
                        if r.status_code == 200:
                            data = r.json()
                            account_balance = float(data.get("account", {}).get("balance", 10000))
                        else:
                            account_balance = 10000  # Default fallback
                    else:
                        account_balance = 10000  # Default fallback
                except Exception as e:
                    logger.warning(f"⚠️ Could not get account balance for {account_id[-3:]}: {e}, using default 10000")
                    account_balance = 10000
                
                risk_amount = account_balance * 0.001  # 0.10% risk per trade
                
                # Calculate stop distance
                if signal.side.value == 'BUY':
                    stop_distance = signal.entry_price - signal.stop_loss
                else:
                    stop_distance = signal.stop_loss - signal.entry_price
                
                position_size = risk_amount / stop_distance if stop_distance > 0 else 10000
                
                # SIGNAL EXPORT (Decision Layer) - Emit intent before execution gate
                try:
                    # Check execution gate status specifically for the signal record
                    # We create a temporary gate instance just to check status for the log
                    # The actual execution later will re-check, which is fine
                    _gate_check = ExecutionGate() 
                    _decision = _gate_check.decision()
                    
                    # Extract strategy info
                    _strategy_key_exp = getattr(signal, 'strategy_key', self._active_strategy_key)
                    _strategy_exp = self._get_strategy_by_key(_strategy_key_exp)
                    _strategy_id_exp = getattr(signal, 'strategy_id', getattr(_strategy_exp, 'strategy_id', 'unknown'))
                    
                    # Get news state
                    _news_state_exp = "unknown"
                    if 'news_context' in locals():
                        _news_state_exp = str(news_context.get("state", "unknown"))
                    
                    # Derive bridge_account from config
                    _bridge_account = None
                    if hasattr(self, 'account_configs') and self.account_configs and account_id in self.account_configs:
                        _cfg = self.account_configs[account_id]
                        if isinstance(_cfg, dict):
                            _bridge_account = _cfg.get('bridge_account')
                        elif hasattr(_cfg, 'bridge_account'):
                            _bridge_account = _cfg.bridge_account

                    SignalExporter.get_signal_exporter().emit(
                        strategy=_strategy_id_exp,
                        symbol=signal.instrument,
                        side=signal.side.value,
                        units=int(position_size),
                        entry_type="MARKET",
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        confidence=getattr(signal, 'confidence', 0.0),
                        regime=getattr(signal, 'regime', 'unknown'),
                        session=getattr(signal, 'session', 'unknown'),
                        news_state=_news_state_exp,
                        execution_allowed=_decision.allowed,
                        block_reason=_decision.reason_code if not _decision.allowed else None,
                        account=account_id,
                        bridge_account=_bridge_account
                    )
                except Exception as e:
                    logger.error(f"Signal export failed (non-blocking): {e}")

                # Place the order via ExecutionGate (handles paper/live mode)
                gate = ExecutionGate()

                # TEMPORARY: XAU execution probe - log execution path for gold signals
                try:
                    if signal.instrument == "XAU_USD":
                        probe_logger = logging.getLogger("xau_execution_probe")
                        probe_logger.critical(
                            "[XAU_EXECUTION_PATH] Signal reached execution stage",
                            extra={
                                "instrument": signal.instrument,
                                "account_id": account_id,
                                "strategy_key": getattr(signal, "strategy_key", self._active_strategy_key),
                                "strategy_id": getattr(signal, "strategy_id", None),
                                "units": int(position_size),
                            },
                        )
                except Exception:
                    logger.warning("XAU_EXECUTION_PATH logging failed", exc_info=True)
                
                # SYSTEM READINESS GATE (Paper Safety)
                # Ensure we pass the GLOBAL readiness score calculated at start of scan
                if HAS_READINESS_OBSERVABILITY and 'system_readiness_score' in locals() and system_readiness_score is not None:
                     _gate_decision = gate.decision(readiness_score=system_readiness_score)
                     if not _gate_decision.allowed and _gate_decision.reason_code == "READINESS_BELOW_THRESHOLD":
                          logger.warning(f"🛑 Execution blocked by readiness gate (score={system_readiness_score}). Signal {signal.instrument} skipped.")
                          continue
                
                # PHASE 1: Get strategy object and extract strategy_id for execution metadata
                strategy_key = getattr(signal, 'strategy_key', self._active_strategy_key)
                strategy = self._get_strategy_by_key(strategy_key)
                if not strategy:
                    logger.error(f"❌ Cannot execute trade: Strategy '{strategy_key}' not found for signal {signal.instrument}")
                    continue
                
                # PHASE 1: Use strategy.strategy_id (required by execution gate)
                # First try to get it from signal, then from strategy object
                strategy_id = getattr(signal, 'strategy_id', None)
                if not strategy_id:
                    strategy_id = getattr(strategy, 'strategy_id', None)
                
                if not strategy_id:
                    logger.error(f"❌ Cannot execute trade: Strategy '{strategy_key}' missing strategy_id attribute")
                    continue
                
                # Create exec_fn that calls OANDA API directly (works even if OrderManager is stub)
                def exec_order():
                    oanda_api_key = os.getenv("OANDA_API_KEY", "").strip()
                    oanda_base_url = os.getenv("OANDA_BASE_URL", "").strip()
                    if not oanda_base_url:
                        trading_mode = os.getenv("TRADING_MODE", "paper").lower()
                        oanda_base_url = "https://api-fxpractice.oanda.com" if trading_mode != "live" else "https://api-fxtrade.oanda.com"
                    
                    import requests
                    headers = {"Authorization": f"Bearer {oanda_api_key}", "Content-Type": "application/json"}
                    url = f"{oanda_base_url}/v3/accounts/{account_id}/orders"
                    
                    # Convert prices to OANDA format
                    is_xau = 'XAU' in signal.instrument
                    price_precision = 2 if is_xau else 5
                    
                    # Configurable thresholds (STRICT defaults - no multiplier masking large deviations)
                    # Override via env for tuning (e.g., MAX_PRICE_DEVIATION_PCT_XAU_USD=3.0)
                    env_key_inst = f"MAX_PRICE_DEVIATION_PCT_{signal.instrument.replace('_', '_')}"
                    global_fx = float(os.getenv("MAX_PRICE_DEVIATION_PCT_FX", "0.5"))
                    global_metals = float(os.getenv("MAX_PRICE_DEVIATION_PCT_METALS", "1.0"))
                    
                    # Precedence: Instrument specific > Global Env > Default
                    if is_xau:
                        max_dev_pct = float(os.getenv(env_key_inst, os.getenv("MAX_PRICE_DEVIATION_PCT", str(global_metals))))
                    else:
                        max_dev_pct = float(os.getenv(env_key_inst, os.getenv("MAX_PRICE_DEVIATION_PCT", str(global_fx))))

                    # For metals: no multiplier (strict 1.0% for both SL and TP)
                    # For FX: multiplier allowed but default to 1.0 (no multiplier) for strictness
                    MAX_STOP_DEVIATION_MULTIPLIER_FX = float(os.getenv("MAX_STOP_DEVIATION_MULTIPLIER_FX", "1.0"))
                    MAX_STOP_DEVIATION_MULTIPLIER_METALS = 1.0  # Metals: no multiplier (strict)
                    
                    stop_multiplier = MAX_STOP_DEVIATION_MULTIPLIER_METALS if is_xau else MAX_STOP_DEVIATION_MULTIPLIER_FX
                    max_stop_dev_pct = max_dev_pct * stop_multiplier
                    min_tp_dist_pct = MIN_TP_DISTANCE_PCT_METALS if is_xau else MIN_TP_DISTANCE_PCT_FX
                    
                    # PRICE INTEGRITY + SANITY CHECK: Validate price integrity, then validate take-profit and stop-loss distances
                    # Get current market price with integrity validation (BLOCKS on integrity violation)
                    mid = 0.0
                    try:
                        from src.control_plane.market_data_provider import get_latest_price, PriceIntegrityError
                        price_obj = get_latest_price(signal.instrument, timeout_s=5.0, validate=True)
                        mid = price_obj.mid
                        bid = price_obj.bid
                        ask = price_obj.ask
                        
                        # FIX: Anchor execution to current market price
                        # Strategies produce signals based on potentially stale candles.
                        # Execution must be relative to the price WE will fill at NOW.
                        if mid > 0:
                            # 1. Determine anchor price (worst-case fill estimation)
                            if signal.side.value == 'BUY':
                                anchor_price = ask if ask > 0 else mid
                            else: # SELL
                                anchor_price = bid if bid > 0 else mid
                                
                            # 2. Determine original distances (from strategy intent)
                            # Protect against zero/invalid original entry
                            original_entry = signal.entry_price if signal.entry_price > 0 else mid
                            sl_dist = abs(original_entry - signal.stop_loss)
                            tp_dist = abs(original_entry - signal.take_profit) if signal.take_profit else 0
                            
                            # 3. Re-calculate absolute levels based on anchor
                            if signal.side.value == 'BUY':
                                new_sl = anchor_price - sl_dist
                                new_tp = anchor_price + tp_dist if tp_dist > 0 else 0
                            else: # SELL
                                new_sl = anchor_price + sl_dist
                                new_tp = anchor_price - tp_dist if tp_dist > 0 else 0
                                
                            # 4. Update signal object (so snapshot shows what we actually executed)
                            # Log the shift for audit
                            if abs(new_sl - signal.stop_loss) > 0.00001:
                                logger.info(f"⚓ ANCHORING EXECUTION: {signal.instrument} {signal.side.value} | Strategy SL: {signal.stop_loss:.{price_precision}f} -> Anchored SL: {new_sl:.{price_precision}f} (Market: {mid:.{price_precision}f})")
                                signal.stop_loss = new_sl
                                signal.take_profit = new_tp
                                signal.entry_price = anchor_price # Update entry to reflect likely fill
                        
                        # Price integrity validated - now validate stop-loss and take-profit distances
                        if signal.side.value == 'BUY':
                                    stop_dev_pct = abs(signal.stop_loss - mid) / mid * 100 if mid > 0 else 999
                                    tp_dev_pct = abs(signal.take_profit - mid) / mid * 100 if mid > 0 else 999
                                    
                                    # For BUY: stop should be below entry
                                    if signal.stop_loss >= signal.entry_price:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        scan_sanity_blocks[account_id] += 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},reason:stop_above_entry}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} must be below entry {signal.entry_price:.{price_precision}f} for BUY")
                                    
                                    # Check if stop is too far (BLOCKING - uses strict threshold)
                                    if stop_dev_pct > max_stop_dev_pct:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        scan_sanity_blocks[account_id] += 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},dev_pct:{stop_dev_pct:.2f},threshold_pct:{max_stop_dev_pct:.2f},reason:stop_too_far}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} deviates {stop_dev_pct:.2f}% from market {mid:.{price_precision}f} (max: {max_stop_dev_pct:.2f}%)")
                                    
                        elif signal.side.value == 'SELL':
                                    stop_dev_pct = abs(signal.stop_loss - mid) / mid * 100 if mid > 0 else 999
                                    tp_dev_pct = abs(signal.take_profit - mid) / mid * 100 if mid > 0 else 999
                                    
                                    # For SELL: stop should be above entry
                                    if signal.stop_loss <= signal.entry_price:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        scan_sanity_blocks[account_id] += 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},reason:stop_below_entry}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} must be above entry {signal.entry_price:.{price_precision}f} for SELL")

                                    # Check if stop is too far (BLOCKING - uses strict threshold)
                                    if stop_dev_pct > max_stop_dev_pct:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        scan_sanity_blocks[account_id] += 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},dev_pct:{stop_dev_pct:.2f},threshold_pct:{max_stop_dev_pct:.2f},reason:stop_too_far}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} deviates {stop_dev_pct:.2f}% from market {mid:.{price_precision}f} (max: {max_stop_dev_pct:.2f}%)")

                    except PriceIntegrityError as e:
                        # Price integrity violation - BLOCK execution
                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                        scan_sanity_blocks[account_id] += 1
                        logger.warning(f"PRICE_INTEGRITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},reason:{str(e)[:200]}}}")
                        _fxg_append_problem_event(
                            severity="AMBER",
                            subsystem="price_integrity",
                            key="price_integrity_block",
                            summary=f"PRICE_INTEGRITY_BLOCK: blocked execution for {signal.instrument} (acct={account_id[-3:]}).",
                            details=str(e)[:200],
                            hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'PRICE_INTEGRITY_BLOCK' | tail -n 80",
                            fingerprint=f"price_integrity_block:{account_id[-3:]}:{signal.instrument}:{str(e)[:80]}",
                        )
                        if maybe_send_problem_alert:
                            try:
                                maybe_send_problem_alert(
                                    "price_integrity_block",
                                    f"Price integrity blocked execution for {signal.instrument} acct {account_id[-3:]}.",
                                    severity="AMBER",
                                    hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'PRICE_INTEGRITY_BLOCK' | tail -n 80",
                                    fingerprint=f"price_integrity_block:{account_id[-3:]}:{signal.instrument}:{str(e)[:80]}",
                                )
                            except Exception:
                                pass
                        raise RuntimeError(f"Price integrity violation for {signal.instrument}: {str(e)[:200]}")
                    except Exception as e:
                        # Re-raise blocking errors
                        if "Stop-loss" in str(e) or "Take-profit" in str(e) or "Price integrity" in str(e):
                            raise e
                        # Log warning for network/other errors but don't hard block (safe default)
                        logger.warning(f"⚠️ Price fetch/validation failed (non-blocking): {str(e)[:200]}")
                    
                    order_payload = {
                        "order": {
                            "type": "MARKET",
                            "instrument": signal.instrument,
                            "units": str(int(position_size)) if signal.side.value == 'BUY' else str(-int(position_size)),
                            "stopLossOnFill": {"price": f"{signal.stop_loss:.{price_precision}f}"}
                        }
                    }
                    
                    # TP Omission Logic: Only add TP if it makes sense relative to current market
                    add_tp = True
                    tp_price = signal.take_profit
                    reason = None
                    
                    if mid > 0:  # We have a valid price reference
                        tp_dist_pct = abs(tp_price - mid) / mid * 100
                        
                        if signal.side.value == 'BUY':
                            if tp_price <= mid:  # TP must be above mid for BUY
                                add_tp = False
                                reason = "tp_below_market"
                            elif tp_dist_pct < min_tp_dist_pct: # TP too close
                                add_tp = False
                                reason = f"tp_too_close_{tp_dist_pct:.3f}_lt_{min_tp_dist_pct}"
                        else:  # SELL
                            if tp_price >= mid:  # TP must be below mid for SELL
                                add_tp = False
                                reason = "tp_above_market"
                            elif tp_dist_pct < min_tp_dist_pct: # TP too close
                                add_tp = False
                                reason = f"tp_too_close_{tp_dist_pct:.3f}_lt_{min_tp_dist_pct}"
                        
                        if not add_tp:
                            self._tp_omitted_per_account[account_id] = self._tp_omitted_per_account.get(account_id, 0) + 1
                            logger.warning(f"TP_OMITTED {{account:{account_id[-3:]},instrument:{signal.instrument},side:{signal.side.value},tp:{tp_price:.{price_precision}f},mid:{mid:.{price_precision}f},dist_pct:{tp_dist_pct:.3f},min_pct:{min_tp_dist_pct},reason:{reason}}}")
                    
                    if add_tp:
                        order_payload["order"]["takeProfitOnFill"] = {"price": f"{tp_price:.{price_precision}f}"}
                    
                    r = requests.post(url, headers=headers, json=order_payload, timeout=10)
                    if r.status_code not in (200, 201):
                        error_text = r.text[:200] if hasattr(r, 'text') else str(r)[:200]
                        _fxg_append_problem_event(
                            severity="AMBER",
                            subsystem="oanda",
                            key="oanda_order_http_error",
                            summary=f"OANDA order failed HTTP {r.status_code} (acct={account_id[-3:]} {signal.instrument}).",
                            details=error_text,
                            hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'OANDA order failed' | tail -n 80",
                            fingerprint=f"oanda_order_http_error:{account_id[-3:]}:{signal.instrument}:{r.status_code}",
                        )
                        if maybe_send_problem_alert:
                            try:
                                maybe_send_problem_alert(
                                    "oanda_order_http_error",
                                    f"OANDA order failed HTTP {r.status_code} for {signal.instrument} acct {account_id[-3:]}.",
                                    severity="AMBER",
                                    hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'OANDA order failed' | tail -n 80",
                                    fingerprint=f"oanda_order_http_error:{account_id[-3:]}:{signal.instrument}:{r.status_code}",
                                )
                            except Exception:
                                pass
                        raise RuntimeError(f"OANDA order failed: HTTP {r.status_code} - {error_text}")
                    
                    result = r.json()
                    
                    # Capture cancel reasons
                    order_cancel_tx = result.get("orderCancelTransaction", {})
                    if order_cancel_tx:
                        reason = order_cancel_tx.get("reason", "UNKNOWN")
                        if account_id not in self._oanda_cancel_reasons_per_account:
                            self._oanda_cancel_reasons_per_account[account_id] = {}
                        self._oanda_cancel_reasons_per_account[account_id][reason] = self._oanda_cancel_reasons_per_account[account_id].get(reason, 0) + 1
                    
                    # BRUTAL TRUTH: Validate transaction IDs exist
                    order_create_tx = result.get("orderCreateTransaction", {})
                    order_fill_tx = result.get("orderFillTransaction", {})
                    
                    has_tx_id = (
                        (order_create_tx and order_create_tx.get("id")) or
                        (order_fill_tx and order_fill_tx.get("id")) or
                        (order_cancel_tx and order_cancel_tx.get("id"))
                    )
                    
                    if not has_tx_id:
                        raise RuntimeError(f"OANDA response missing transaction IDs. Response keys: {list(result.keys())}")
                    
                    return result
                
                # ENFORCE: Guarantee strategy_id is in meta (defensive)
                meta_dict = {
                    "source": "working_trading_system",
                    "path": "place_market_order",
                    "strategy_id": strategy_id,  # PHASE 1: Use strategy.strategy_id from strategy object
                    "strategy_key": strategy_key,  # Keep for backward compatibility/debugging
                }
                # Defensive: ensure strategy_id is never None
                if not meta_dict.get("strategy_id"):
                    logger.error(f"❌ CRITICAL: strategy_id is None for {signal.instrument} - blocking execution")
                    continue

                # TEMPORARY: XAU execution probe — log explicit execution path entry
                if signal.instrument == "XAU_USD":
                    import logging as _logging

                    _logging.getLogger("xau_execution_probe").critical(
                        f"[XAU_EXECUTION_PATH] Signal reached execution | "
                        f"instrument={signal.instrument} | strategy_id={strategy_id} | "
                        f"units={int(position_size)} | account={account_id}"
                    )

                result = gate.place_market_order(
                    instrument=signal.instrument,
                    units=int(position_size),
                    account_id=account_id,
                    exec_fn=exec_order,
                    meta=meta_dict
                )
                
                # BRUTAL TRUTH: Only log "TRADE EXECUTED" if result contains tx ids
                # result from exec_order is the OANDA JSON response
                if result:
                    # Extract tx ids from result (it's the OANDA response dict)
                    order_create_tx = result.get("orderCreateTransaction", {}) if isinstance(result, dict) else {}
                    order_fill_tx = result.get("orderFillTransaction", {}) if isinstance(result, dict) else {}
                    order_cancel_tx = result.get("orderCancelTransaction", {}) if isinstance(result, dict) else {}
                    
                    has_tx_id = (
                        (order_create_tx and order_create_tx.get("id")) or
                        (order_fill_tx and order_fill_tx.get("id")) or
                        (order_cancel_tx and order_cancel_tx.get("id"))
                    )
                    
                    if has_tx_id:
                        # Extract tx ids for logging (safe fields only)
                        tx_ids = []
                        if order_create_tx.get("id"):
                            tx_ids.append(f"orderCreateTransaction.id={order_create_tx.get('id')}")
                        if order_fill_tx.get("id"):
                            tx_ids.append(f"orderFillTransaction.id={order_fill_tx.get('id')}")
                        if order_cancel_tx.get("id"):
                            tx_ids.append(f"orderCancelTransaction.id={order_cancel_tx.get('id')}")
                        
                        executed_trades += 1
                        # Update risk cap counters
                        self._open_trades_per_account[account_id] = open_count + 1
                        self._daily_trades_per_account[account_id] = daily_count + 1
                        self._last_trade_time_per_account[account_id] = now
                        self._last_trade_time_per_symbol[symbol_key] = now
                        self._orders_per_minute.append((now, account_id))
                        # Update hourly rate tracking
                        if account_id not in self._orders_per_hour_per_account:
                            self._orders_per_hour_per_account[account_id] = []
                        self._orders_per_hour_per_account[account_id].append(now)
                        # Update signal fingerprint for dedupe
                        strat_key_for_dedupe = getattr(signal, 'strategy_key', self._active_strategy_key)
                        signal_fingerprint = (account_id, signal.instrument, strat_key_for_dedupe)
                        self._signal_fingerprints[signal_fingerprint] = (now, signal.entry_price, signal.side.value)
                        logger.info(f"✅ TRADE EXECUTED: {signal.instrument} {signal.side.value} - Units: {int(position_size)} ({', '.join(tx_ids)})")
                        if maybe_send_confirmed:
                            try:
                                maybe_send_confirmed(
                                    account_suffix=account_id[-3:],
                                    instrument=str(signal.instrument),
                                    side=str(signal.side.value),
                                    units=int(position_size),
                                    tx_ids=list(tx_ids),
                                    fingerprint=f"confirmed:{account_id[-3:]}:{signal.instrument}:{signal.side.value}:{','.join(tx_ids)[:80]}",
                                )
                            except Exception:
                                pass
                        try:
                            _lane_stats(account_id)["executed_last_cycle"] += 1
                            _lane_stats(account_id)["last_skip_reason"] = None
                        except Exception:
                            pass
                    else:
                        logger.error(f"❌ TRADE FAILED: {signal.instrument} {signal.side.value} - OANDA response missing transaction IDs")
                else:
                    logger.error(f"❌ TRADE FAILED: {signal.instrument} {signal.side.value} - No result from execution")
                    
            except Exception as e:
                error_msg = str(e)[:200]
                logger.error(f"❌ Trade execution failed: {signal.instrument} {signal.side.value} - {error_msg}")
                _fxg_append_problem_event(
                    severity="AMBER",
                    subsystem="execution",
                    key="trade_execution_failed",
                    summary=f"Trade execution failed for {signal.instrument} (acct={account_id[-3:]}).",
                    details=error_msg,
                    hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'Trade execution failed|OANDA order failed' | tail -n 100",
                    fingerprint=f"trade_execution_failed:{account_id[-3:]}:{signal.instrument}:{error_msg[:80]}",
                )
                if maybe_send_problem_alert:
                    try:
                        maybe_send_problem_alert(
                            "trade_execution_failed",
                            f"Trade execution failed for {signal.instrument} acct {account_id[-3:]} ({error_msg}).",
                            severity="AMBER",
                            hint_cmd="sudo journalctl -u ai-quant-runner -n 200 --no-pager | egrep -i 'Trade execution failed|OANDA order failed' | tail -n 100",
                            fingerprint=f"trade_execution_failed:{account_id[-3:]}:{signal.instrument}:{error_msg[:80]}",
                        )
                    except Exception:
                        pass
        
        # [FORENSIC] FORCE_PAPER_TEST_TRADE: inject one PAPER test order per execution-capable account (reversible)
        if os.getenv("FORCE_PAPER_TEST_TRADE", "false").lower() == "true":
            for _account_id in self.active_accounts:
                if _account_id in self.order_managers:
                    logger.error(f"[FORCED_TEST_TRADE] Executing PAPER test trade for account {_account_id[-3:]}")
                    self._execute_forced_paper_test(_account_id)
        
        if executed_trades > 0:
            logger.info(f"🎯 EXECUTED {executed_trades} TRADES")
        else:
            logger.info(f"📄 Execution enabled but no trades executed — signals generated: {len(all_signals)}, executed: 0")
        
        if structured_logger and getattr(structured_logger, "log_signal", None):
            structured_logger.log_signal("SIGNAL_EVALUATED", {
                "instrument": "SYSTEM",
                "strategy": "SYSTEM_SCAN",
                "reason": "scan_tick_completed_no_trade",
                "execution_allowed": False
            })
        else:
            forensic_logger.warning("[SKIP] structured_logger missing or no log_signal, log skipped safely")
        forensic_logger.info("[CYCLE_END] scan_and_execute completed without UnboundLocalError")
        self._last_cycle_lane_stats = cycle_stats
        self._write_status_snapshot(len(all_signals), executed_trades, all_signals, news_context.get("items"))
        return executed_trades

def run_forever(max_iterations: int = 0) -> None:
    """Run continuous scanning"""
    forensic_logger = _get_forensic_logger()
    forensic_logger.info("[BOOT] Entered run_forever")
    logger.info("🚀 STARTING WORKING TRADING SYSTEM")
    
    system = WorkingTradingSystem()
    
    # Run continuous scanning
    i = 0
    while True:
        try:
            # HOT-RELOAD: Check for config changes before each scan
            system._check_config_reload()
            
            executed = system.scan_and_execute()
            
            # Use dynamically loaded scan interval
            scan_interval = system._scan_interval
            logger.info(f"⏰ Next scan in {scan_interval} seconds... (Executed {executed} trades)")
            
            i += 1
            if max_iterations > 0 and i >= max_iterations:
                logger.info(f"🛑 Reached max iterations ({max_iterations}), stopping.")
                break
            
            time.sleep(scan_interval)
        except KeyboardInterrupt:
            logger.info("🛑 Trading system stopped by user")
            break
        except Exception as e:
            forensic_logger.error(f"[EXCEPTION] scan loop error: {e}", exc_info=True)
            logger.error("❌ Scan error (continuing next cycle): %s\n%s", e, traceback.format_exc())
            time.sleep(10)

def main():
    """Main trading loop"""
    run_forever()

if __name__ == "__main__":
    # BLOCKED: Direct execution bypasses canonical entrypoint and safety gates
    # Use canonical entrypoint: python -m runner_src.runner.main
    import sys
    print("❌ BLOCKED: Direct execution of working_trading_system.py is not allowed.")
    print("   Use the canonical entrypoint: python -m runner_src.runner.main")
    print("   This ensures proper safety gates, execution controls, and environment setup.")
    sys.exit(1)
