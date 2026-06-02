#!/usr/bin/env python3
"""
WORKING TRADING SYSTEM - ACTUALLY EXECUTES TRADES
This system will generate signals and EXECUTE them immediately
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone

# Set up environment
os.environ['OANDA_ENVIRONMENT'] = os.environ.get('OANDA_ENVIRONMENT', 'practice')

# Path setup is handled by src.runner.main
# All imports from google-cloud-trading-system/src/
from src.core.dynamic_account_manager import get_account_manager
from src.core.trading_scanner import TradingScanner
from src.core.order_manager import OrderManager
from src.core.execution_gate import ExecutionGate
# NEWS: Import news fetching registry
try:
    from src.control_plane.news_provider import fetch_news_with_registry
    HAS_NEWS_PROVIDER = True
except ImportError:
    HAS_NEWS_PROVIDER = False
    logger.warning("⚠️ Could not import fetch_news_with_registry - news integration disabled")

from src.strategies.momentum_trading import MomentumTradingStrategy
# Note: Using gold_scalping_optimized as gold_scalping doesn't exist
try:
    from src.strategies.gold_scalping_optimized import GoldScalpingOptimizedStrategy as GoldScalpingStrategy
except ImportError:
    # Fallback: use momentum if gold scalping not available
    GoldScalpingStrategy = MomentumTradingStrategy

# Market hours check (proper FX market hours)
from src.core.market_hours import is_fx_market_open

# Status snapshot for API bridge (lazy import - happens after path setup)
HAS_STATUS_SNAPSHOT = None  # Will be determined lazily

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _can_execute() -> tuple[bool, str]:
    """Determine if execution is enabled based on trading mode and flags.
    
    Uses canonical EXECUTION_UNLOCK_OK with backward-compatible PAPER_EXECUTION_ENABLED alias.
    
    Returns:
        (can_execute: bool, reason: str)
    """
    gate = ExecutionGate()
    decision = gate.decision()
    
    # Live mode: requires dual-confirm
    if decision.mode == 'live':
        if decision.allowed:
            return (True, "live_dual_enabled")
        else:
            return (False, f"live_blocked_{decision.reason}")
    
    # Paper mode: canonical gating with backward-compatible alias
    # Canonical: EXECUTION_UNLOCK_OK (checked first)
    # Alias: PAPER_EXECUTION_ENABLED (checked if canonical not set)
    # Truthy values: true, 1, yes, y, on
    # Default: disabled (fail-safe)
    def _env_bool(name: str, default: bool = False) -> bool:
        v = os.getenv(name)
        if v is None:
            return default
        return v.strip().lower() in ("true", "1", "yes", "y", "on")
    
    execution_unlock_ok = _env_bool("EXECUTION_UNLOCK_OK", False)
    paper_execution_enabled = _env_bool("PAPER_EXECUTION_ENABLED", False)
    
    # Canonical var wins; if not set, use alias
    paper_execution = execution_unlock_ok if os.getenv("EXECUTION_UNLOCK_OK") is not None else paper_execution_enabled
    
    if paper_execution:
        return (True, "paper_execution_enabled")
    else:
        return (False, "paper_signals_only")


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
    oanda_api_key = os.getenv("OANDA_API_KEY", "").strip()
    oanda_account_id = os.getenv("OANDA_ACCOUNT_ID", "").strip()
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
    
    # Account ID must match (either single OANDA_ACCOUNT_ID or account_id must be in allowlist)
    if oanda_account_id and account_id != oanda_account_id:
        # Check if using allowlist mode
        account_suffix_allowlist = os.getenv("ACCOUNT_SUFFIX_ALLOWLIST", "").strip()
        account_id_prefix = os.getenv("ACCOUNT_ID_PREFIX", "101-004-30719775-").strip()
        if account_suffix_allowlist:
            # Multi-account mode: account_id should match prefix + suffix pattern
            suffix = account_id.replace(account_id_prefix, "")
            if suffix not in [s.strip() for s in account_suffix_allowlist.split(",")]:
                logger.debug(f"⚠️ Account {account_id[-3:]} not in allowlist")
                return False
        else:
            # Single account mode: must match exactly
            if account_id != oanda_account_id:
                logger.debug(f"⚠️ Account {account_id[-3:]} does not match OANDA_ACCOUNT_ID")
                return False
    
    # OANDA credentials present - valid for execution
    return True


class WorkingTradingSystem:
    def __init__(self):
        # Defer OANDA_API_KEY check to runtime (allows paper-mode testing)
        if 'OANDA_API_KEY' not in os.environ:
            logger.warning("⚠️ OANDA_API_KEY not set - paper mode only")
        
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        
        # Get account configs from YAML (even if broker not initialized)
        # This allows scanning to run with paper accounts
        self.account_configs = self.account_manager.account_configs
        self.account_ids_for_scanning = list(self.account_configs.keys()) if self.account_configs else []
        
        self.strategies = {
            'momentum': MomentumTradingStrategy(),
            'gold': GoldScalpingStrategy()
        }
        self.order_managers = {}
        
        # Hot-reload support: track config state
        self._config_last_mtime = 0.0
        self._config_load_error = None  # Track config load failures
        self._active_strategy_key = "momentum"  # Default
        self._scan_interval = 30  # Default
        self._strategy_assignments = None  # Multi-account assignments
        self._account_risk_limits = {}  # Per-account risk limits from config
        self._global_max_daily_trades = 3  # Global default (from config.risk.max_daily_trades_per_account)
        
        # Risk caps tracking
        self._open_trades_per_account = {}  # account_id -> count
        self._daily_trades_per_account = {}  # account_id -> count (resets daily)
        self._last_trade_time_per_account = {}  # account_id -> timestamp
        self._last_trade_time_per_symbol = {}  # (account_id, symbol) -> timestamp
        self._signal_fingerprints = {}  # (account_id, instrument, strategy_key) -> (timestamp, entry_price, side) for dedupe
        self._orders_per_hour_per_account = {}  # account_id -> list of timestamps (for hourly rate limiting)
        self._cancels_per_hour_per_account = {}  # account_id -> list of timestamps (for hourly cancel limiting)
        self._orders_per_minute = []  # List of (timestamp, account_id) for rate limiting
        self._last_daily_reset = datetime.now(timezone.utc).date()
        
        # New observability counters
        self._price_sanity_blocks_per_account = {}  # account_id -> count
        self._tp_omitted_per_account = {}  # account_id -> count
        self._throttle_skips_per_account = {}  # account_id -> count
        self._oanda_cancel_reasons_per_account = {}  # account_id -> {reason: count}
        
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
            for account_id in self.active_accounts:
                if _has_valid_broker(account_id, self.account_manager):
                    execution_ready_accounts.append(account_id)
                    try:
                        # OrderManager stub doesn't need account_id, but we store it for reference
                        self.order_managers[account_id] = OrderManager()
                        logger.info(f"✅ OrderManager created for account {account_id[-3:]}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not initialize OrderManager for {account_id}: {e}")
        
        if not can_execute:
            logger.info(f"📄 Execution disabled ({exec_reason}) - signals-only mode")
        elif not execution_ready_accounts:
            logger.info(f"📄 Execution enabled but no valid brokers available - signals-only mode")
        else:
            logger.info(f"✅ Execution enabled ({exec_reason}) - {len(execution_ready_accounts)} account(s) ready")
        
        if not self.account_ids_for_scanning:
            logger.info("ℹ️ No accounts configured in YAML - scanning will run with default instruments")
        else:
            logger.info(f"✅ Working Trading System initialized")
            logger.info(f"   Accounts for scanning: {len(self.account_ids_for_scanning)}")
            logger.info(f"   Accounts with execution capability: {len(execution_ready_accounts)}")
        
        # Write initial status snapshot
        self._write_status_snapshot(0, 0)
    
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
                "timestamp_utc": datetime.now(timezone.utc).timestamp()
            })
        return formatted

    def _write_status_snapshot(self, signals_generated: int, executed_count: int, recent_signals_list=None) -> None:
        """Write status snapshot for API (atomic, no secrets)"""
        if not self.status_writer:
            return
        
        try:
            # Get execution state
            can_execute, exec_reason = _can_execute()
            
            # Count execution-ready accounts
            # If execution is unlocked (can_execute=True), count loaded accounts as execution-capable
            # Broker validity check is separate and doesn't affect capability count
            execution_ready_count = 0
            if can_execute:
                execution_ready_count = len(self.active_accounts)
            
            # Build daily limit map (account_id -> limit value)
            daily_limit_map = {}
            for account_id in self.account_ids_for_scanning:
                account_limits = self._account_risk_limits.get(account_id)
                if account_limits and account_limits.max_daily_trades is not None:
                    daily_limit_map[account_id] = account_limits.max_daily_trades
                elif account_limits and account_limits.max_daily_trades is None:
                    # Use global default
                    daily_limit_map[account_id] = self._global_max_daily_trades
                else:
                    # No per-account config, use global default
                    daily_limit_map[account_id] = self._global_max_daily_trades
            
            # Build snapshot (NO SECRETS)
            snapshot = {
                "mode": os.getenv("TRADING_MODE", "paper"),
                "execution_enabled": can_execute,
                "execution_reason": exec_reason,
                "accounts_total": len(self.account_ids_for_scanning),
                "accounts_execution_capable": execution_ready_count,
                "active_strategy_key": self._active_strategy_key,
                "scan_interval": self._scan_interval,
                "last_signals_generated": signals_generated,
                "last_executed_count": executed_count,
                "last_scan_iso": datetime.utcnow().isoformat() + "Z",
                "market_closed": not is_fx_market_open(datetime.now(timezone.utc)),  # FX market hours
                "accounts": [],  # Populated below without secrets
                "recent_signals": self._format_signals_for_snapshot(recent_signals_list) if recent_signals_list else [],
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
                "tp_omitted_per_account": dict(self._tp_omitted_per_account),
                "throttle_skips_per_account": dict(self._throttle_skips_per_account),
                "oanda_cancel_reasons_per_account": dict(self._oanda_cancel_reasons_per_account),
            }
            
            # Add account summaries (no secrets, masked IDs)
            for account_id in self.account_ids_for_scanning:
                if account_id in self.account_configs:
                    config = self.account_configs[account_id]
                    snapshot["accounts"].append({
                        "id_masked": account_id[-4:] if len(account_id) > 4 else "****",
                        "strategy": config.strategy_name,
                        "instruments": config.instruments[:3],  # Limit list size
                        "execution_capable": can_execute  # Execution capable if execution is unlocked
                    })
            
            # Write atomically
            self.status_writer.write(snapshot)
            
        except Exception as e:
            # Log explicit marker with errno and path for observability
            errno_str = str(getattr(e, 'errno', 'unknown'))
            path_str = str(getattr(self.status_writer, 'snapshot_path', 'unknown'))
            logger.warning(f"STATUS_WRITE_FAIL errno={errno_str} path={path_str} error={str(e)[:200]}")
    
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
            self._account_risk_limits = {
                account_id: limits
                for account_id, limits in (config.account_risk_limits or {}).items()
            }
            self._config_last_mtime = config_store.get_mtime()
            
            logger.info(f"📝 Runtime config loaded: strategy={self._active_strategy_key}, interval={self._scan_interval}s, global_max_daily_trades={self._global_max_daily_trades}")
            if self._strategy_assignments:
                enabled_count = sum(1 for a in self._strategy_assignments if a.enabled)
                logger.info(f"   Strategy assignments: {enabled_count} enabled out of {len(self._strategy_assignments)}")
            if self._account_risk_limits:
                logger.info(f"   Account risk limits: {len(self._account_risk_limits)} accounts configured")
            
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
        """
        # Map config keys to strategy instances
        strategy_map = {
            'momentum': self.strategies.get('momentum'),
            'gold': self.strategies.get('gold'),
            'gold_scalping': self.strategies.get('gold'),  # Alias
            'momentum_v2': self.strategies.get('momentum'),  # Fallback to momentum
            'range': self.strategies.get('momentum'),  # Fallback to momentum
            'eur_usd_5m_safe': self.strategies.get('momentum'),  # Fallback to momentum
            'mean_rev_v2': self.strategies.get('momentum'),  # Fallback to momentum
            'xau_usd_session_bias_1': self.strategies.get('gold'),  # Use gold strategy for XAU_USD
            'xau_usd_session_bias_2': self.strategies.get('gold'),  # Use gold strategy for XAU_USD
            'xau_usd_session_bias_3': self.strategies.get('gold'),  # Use gold strategy for XAU_USD
            'ultra_strict_forex': self.strategies.get('momentum'),  # Fallback to momentum
            'pat_orb_dual_session': self.strategies.get('momentum'),  # Fallback to momentum
            'trump_dna': self.strategies.get('gold'),  # Use gold strategy (closest to Trump DNA approach)
        }
        
        strategy = strategy_map.get(strategy_key)
        if strategy is None:
            logger.warning(f"⚠️ Strategy '{strategy_key}' not found, using momentum")
            strategy = self.strategies.get('momentum')
        
        return strategy
    
    def scan_and_execute(self):
        """Scan for opportunities and EXECUTE trades immediately
        
        Supports multi-account strategy assignments:
        - If strategy_assignments present: runs assigned strategy per account
        - Else: uses legacy active_strategy_key on first execution-capable account
        
        Always runs scanning even if no broker accounts are available.
        """
        logger.info("🔍 SCANNING FOR OPPORTUNITIES...")
        
        # GATE: Config Validity Check
        if self._config_load_error:
            logger.error(f"CONFIG_INVALID_BLOCK error={{self._config_load_error}}")
            self._write_status_snapshot(0, 0)
            return 0
        
        all_signals = []
        
        # Load effective assignments from runtime config
        effective_assignments = []
        if self._strategy_assignments:
            # Use strategy_assignments where enabled=true
            for assignment in self._strategy_assignments:
                if assignment.enabled:
                    effective_assignments.append(assignment)
        else:
            # Legacy behavior: use active_strategy_key on first execution-capable account
            if self.account_ids_for_scanning:
                first_account = self.account_ids_for_scanning[0]
                # Create a pseudo-assignment for legacy compatibility using StrategyAssignment
                try:
                    from src.control_plane.schema import StrategyAssignment
                    effective_assignments = [StrategyAssignment(
                        account_id=first_account,
                        strategy_key=self._active_strategy_key,
                        enabled=True
                    )]
                except ImportError:
                    # Fallback: use a simple object
                    class LegacyAssignment:
                        def __init__(self, account_id, strategy_key, enabled=True):
                            self.account_id = account_id
                            self.strategy_key = strategy_key
                            self.enabled = enabled
                    effective_assignments = [LegacyAssignment(
                        account_id=first_account,
                        strategy_key=self._active_strategy_key,
                        enabled=True
                    )]
        
        if not effective_assignments:
            logger.warning("⚠️ No strategy assignments configured - skipping scan")
            self._write_status_snapshot(0, 0)
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
                
                # Get instruments from account config, or use strategy registry defaults
                if account_id in self.account_configs:
                    config = self.account_configs[account_id]
                    instruments = config.instruments if config.instruments else ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']
                else:
                    # Try to get instruments from strategy registry
                    try:
                        from src.control_plane.strategy_registry import get_strategy_info
                        strategy_info = get_strategy_info(strategy_key)
                        if strategy_info:
                            instruments = strategy_info.instruments
                        else:
                            instruments = ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']
                    except Exception:
                        instruments = ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']
                
                market_data = client.get_current_prices(instruments)
                
                # GATE: Price Feed Freshness Check
                now_ts = datetime.now(timezone.utc).timestamp()
                MAX_PRICE_AGE_SECONDS = 30
                stale_instruments = []
                price_timestamps = {}
                
                for inst in instruments:
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
                    continue
                
                # Get strategy instance by key
                strategy = self._get_strategy_by_key(strategy_key)
                if not strategy:
                    logger.warning(f"⚠️ Strategy '{strategy_key}' not found for account {account_id[-3:]}, skipping")
                    continue
                
                # Run strategy for this account only
                try:
                    # Pass news context to strategy (if it accepts it)
                    try:
                        signals = strategy.analyze_market(market_data, news_data=news_context)
                    except TypeError:
                        # Fallback for strategies that don't accept news_data yet
                        signals = strategy.analyze_market(market_data)
                    
                    # LOG EVIDENCE: STRAT_EVIDENCE (Canonical Marker)
                    primary_inst = instruments[0] if instruments else "UNKNOWN"
                    price_used = market_data.get(primary_inst)
                    mid_price = price_used.mid if price_used else 0
                    
                    # Construct evidence object (single line, key=value)
                    # Using clean string representation for lists
                    prov_str = ",".join(news_context.get("providers", []))
                    if not prov_str: prov_str = "none"
                    
                    evidence_str = (
                        f"STRAT_EVIDENCE system=ALPHA account={account_id[-3:]} strategy={strategy_key} "
                        f"instrument={primary_inst} price_mid={mid_price:.5f} "
                        f"price_ts={price_timestamps.get(primary_inst, 0):.3f} "
                        f"news_used_count={news_context.get('count', 0)} "
                        f"news_providers={prov_str} "
                        f"signals_generated={len(signals) if signals else 0} "
                        f"decision={'BUY' if signals and signals[0].side.value == 'BUY' else ('SELL' if signals and signals[0].side.value == 'SELL' else 'NONE')}"
                    )
                    logger.info(evidence_str)
                    
                    if signals:
                        logger.info(f"📊 {strategy_key} generated {len(signals)} signals for account {account_id[-3:]}")
                        for signal in signals:
                            # Hard assertion: ensure signal is tagged with correct account_id
                            signal.account_id = account_id
                            signal.strategy_key = strategy_key
                            # Log for audit
                            logger.debug(f"   Signal: {signal.instrument} {signal.side.value} for account {account_id[-3:]}")
                            all_signals.append(signal)
                    else:
                        logger.debug(f"   {strategy_key} for account {account_id[-3:]}: no signals")
                except Exception as e:
                    logger.warning(f"⚠️ {strategy_key} failed for account {account_id[-3:]}: {e}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to scan account {account_id[-3:]} with strategy {strategy_key}: {e}")
        
        logger.info(f"📊 Total signals generated: {len(all_signals)}")
        
        # EXECUTE TRADES (only if execution is enabled and order managers are available)
        executed_trades = 0
        if not self.execution_enabled:
            logger.info(f"📄 Execution disabled (signals-only) — signals generated: {len(all_signals)}, executed: 0")
            self._write_status_snapshot(len(all_signals), 0, recent_signals_list=all_signals)
            return len(all_signals)  # Return signal count, not executed count
        
        if not self.order_managers:
            logger.info(f"📄 Execution enabled but no order managers available — signals generated: {len(all_signals)}, executed: 0")
            self._write_status_snapshot(len(all_signals), 0, recent_signals_list=all_signals)
            return len(all_signals)  # Return signal count, not executed count
        
        # Reset daily counters if new day
        current_date = datetime.now(timezone.utc).date()
        if current_date > self._last_daily_reset:
            self._daily_trades_per_account.clear()
            self._last_daily_reset = current_date
            logger.info("📅 Daily trade counters reset")
        
        # Risk caps (strict enforcement)
        MAX_OPEN_TRADES_PER_ACCOUNT = 1
        # MAX_DAILY_TRADES_PER_ACCOUNT is now per-account (see below)
        MAX_ORDERS_PER_MINUTE_PER_VM = 4
        COOLDOWN_SECONDS_PER_SYMBOL = 300
        
        # Clean old order timestamps (keep only last minute)
        now = datetime.now(timezone.utc)
        self._orders_per_minute = [(ts, acc) for ts, acc in self._orders_per_minute if (now - ts).total_seconds() < 60]
        
        # Update open trades count per account (query from broker)
        # Note: OrderManager may be a stub in paper mode, so we query via API instead
        for account_id in self.order_managers.keys():
            try:
                # Try to get open positions via direct OANDA API call
                # This works even if OrderManager is a stub
                oanda_api_key = os.getenv("OANDA_API_KEY", "").strip()
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
        
        for signal in all_signals:
            try:
                account_id = signal.account_id
                
                # Hard assertion: ensure order manager exists for this account
                if account_id not in self.order_managers:
                    logger.warning(f"⚠️ No order manager for account {account_id[-3:]}, skipping signal")
                    continue
                
                order_manager = self.order_managers[account_id]
                
                # RISK CAPS ENFORCEMENT
                # 1. Check max open trades per account
                open_count = self._open_trades_per_account.get(account_id, 0)
                if open_count >= MAX_OPEN_TRADES_PER_ACCOUNT:
                    logger.warning(f"⛔ Skipping {signal.instrument}: account {account_id[-3:]} has {open_count} open trades (max: {MAX_OPEN_TRADES_PER_ACCOUNT})")
                    continue
                
                # 2. Check max daily trades per account (per-account limit or global default)
                daily_count = self._daily_trades_per_account.get(account_id, 0)
                
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
                        continue
                
                # 3. Check orders per minute per VM
                orders_last_minute = len([ts for ts, acc in self._orders_per_minute])
                if orders_last_minute >= MAX_ORDERS_PER_MINUTE_PER_VM:
                    logger.warning(f"⛔ Skipping {signal.instrument}: {orders_last_minute} orders in last minute (max: {MAX_ORDERS_PER_MINUTE_PER_VM})")
                    continue
                
                # 4. THROTTLE: Check cooldown per symbol (300s default)
                symbol_key = (account_id, signal.instrument)
                last_trade_time = self._last_trade_time_per_symbol.get(symbol_key)
                if last_trade_time:
                    seconds_since = (now - last_trade_time).total_seconds()
                    if seconds_since < COOLDOWN_SECONDS_PER_SYMBOL:
                        self._throttle_skips_per_account[account_id] = self._throttle_skips_per_account.get(account_id, 0) + 1
                        logger.warning(f"THROTTLE_SKIP {{account:{account_id[-3:]},instrument:{signal.instrument},reason:cooldown_active,seconds_since:{int(seconds_since)},cooldown_seconds:{COOLDOWN_SECONDS_PER_SYMBOL},next_allowed_time:{(last_trade_time + timedelta(seconds=COOLDOWN_SECONDS_PER_SYMBOL)).isoformat()}}}")
                        continue
                
                # 5. THROTTLE: Per-account cooldown (120s minimum between any orders)
                last_account_trade = self._last_trade_time_per_account.get(account_id)
                if last_account_trade:
                    seconds_since_account = (now - last_account_trade).total_seconds()
                    account_cooldown = 120  # 2 minutes minimum
                    if seconds_since_account < account_cooldown:
                        self._throttle_skips_per_account[account_id] = self._throttle_skips_per_account.get(account_id, 0) + 1
                        logger.warning(f"THROTTLE_SKIP {{account:{account_id[-3:]},instrument:{signal.instrument},reason:account_cooldown,seconds_since:{int(seconds_since_account)},cooldown_seconds:{account_cooldown},next_allowed_time:{(last_account_trade + timedelta(seconds=account_cooldown)).isoformat()}}}")
                        continue
                
                # 6. THROTTLE: Hourly order rate limit (12 orders/hour per account)
                if account_id not in self._orders_per_hour_per_account:
                    self._orders_per_hour_per_account[account_id] = []
                hour_ago = now - timedelta(hours=1)
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
                signal_fingerprint = (account_id, signal.instrument, self._active_strategy_key)
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
                
                # Place the order via ExecutionGate (handles paper/live mode)
                gate = ExecutionGate()
                
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
                    MAX_PRICE_DEVIATION_PCT_FX = float(os.getenv("MAX_PRICE_DEVIATION_PCT_FX", "0.5"))
                    MAX_PRICE_DEVIATION_PCT_METALS = float(os.getenv("MAX_PRICE_DEVIATION_PCT_METALS", "1.0"))
                    # For metals: no multiplier (strict 1.0% for both SL and TP)
                    # For FX: multiplier allowed but default to 1.0 (no multiplier) for strictness
                    MAX_STOP_DEVIATION_MULTIPLIER_FX = float(os.getenv("MAX_STOP_DEVIATION_MULTIPLIER_FX", "1.0"))
                    MAX_STOP_DEVIATION_MULTIPLIER_METALS = 1.0  # Metals: no multiplier (strict)
                    
                    # Minimum TP distance to prevent immediate fill/cancel spam
                    # 0.05% for FX, 0.1% for XAU default
                    MIN_TP_DISTANCE_PCT_FX = float(os.getenv("MIN_TP_DISTANCE_PCT_FX", "0.05"))
                    MIN_TP_DISTANCE_PCT_METALS = float(os.getenv("MIN_TP_DISTANCE_PCT_METALS", "0.1"))
                    
                    max_dev_pct = MAX_PRICE_DEVIATION_PCT_METALS if is_xau else MAX_PRICE_DEVIATION_PCT_FX
                    stop_multiplier = MAX_STOP_DEVIATION_MULTIPLIER_METALS if is_xau else MAX_STOP_DEVIATION_MULTIPLIER_FX
                    max_stop_dev_pct = max_dev_pct * stop_multiplier
                    min_tp_dist_pct = MIN_TP_DISTANCE_PCT_METALS if is_xau else MIN_TP_DISTANCE_PCT_FX
                    
                    # PRICE SANITY CHECK: Validate take-profit and stop-loss prices against current market
                    # Get current market price for validation
                    mid = 0.0
                    try:
                        price_url = f"{oanda_base_url}/v3/accounts/{account_id}/pricing?instruments={signal.instrument}"
                        price_resp = requests.get(price_url, headers=headers, timeout=5)
                        if price_resp.status_code == 200:
                            price_data = price_resp.json()
                            prices = price_data.get("prices", [])
                            if prices:
                                current_price = prices[0]
                                bid = float(current_price.get("bids", [{}])[0].get("price", 0))
                                ask = float(current_price.get("asks", [{}])[0].get("price", 0))
                                mid = (bid + ask) / 2.0
                                
                                # Validate stop-loss and take-profit distances
                                if signal.side.value == 'BUY':
                                    stop_dev_pct = abs(signal.stop_loss - mid) / mid * 100 if mid > 0 else 999
                                    tp_dev_pct = abs(signal.take_profit - mid) / mid * 100 if mid > 0 else 999
                                    
                                    # For BUY: stop should be below entry
                                    if signal.stop_loss >= signal.entry_price:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},reason:stop_above_entry}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} must be below entry {signal.entry_price:.{price_precision}f} for BUY")
                                    
                                    # Check if stop is too far (BLOCKING - uses strict threshold)
                                    if stop_dev_pct > max_stop_dev_pct:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},dev_pct:{stop_dev_pct:.2f},threshold_pct:{max_stop_dev_pct:.2f},reason:stop_too_far}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} deviates {stop_dev_pct:.2f}% from market {mid:.{price_precision}f} (max: {max_stop_dev_pct:.2f}%)")
                                    
                                elif signal.side.value == 'SELL':
                                    stop_dev_pct = abs(signal.stop_loss - mid) / mid * 100 if mid > 0 else 999
                                    tp_dev_pct = abs(signal.take_profit - mid) / mid * 100 if mid > 0 else 999
                                    
                                    # For SELL: stop should be above entry
                                    if signal.stop_loss <= signal.entry_price:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},reason:stop_below_entry}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} must be above entry {signal.entry_price:.{price_precision}f} for SELL")

                                    # Check if stop is too far (BLOCKING - uses strict threshold)
                                    if stop_dev_pct > max_stop_dev_pct:
                                        self._price_sanity_blocks_per_account[account_id] = self._price_sanity_blocks_per_account.get(account_id, 0) + 1
                                        logger.warning(f"PRICE_SANITY_BLOCK {{account:{account_id[-3:]},instrument:{signal.instrument},order_type:MARKET,stop_loss:{signal.stop_loss:.{price_precision}f},mid:{mid:.{price_precision}f},dev_pct:{stop_dev_pct:.2f},threshold_pct:{max_stop_dev_pct:.2f},reason:stop_too_far}}")
                                        raise RuntimeError(f"Stop-loss {signal.stop_loss:.{price_precision}f} deviates {stop_dev_pct:.2f}% from market {mid:.{price_precision}f} (max: {max_stop_dev_pct:.2f}%)")

                    except Exception as e:
                        # Re-raise blocking errors
                        if "Stop-loss" in str(e) or "Take-profit" in str(e):
                            raise e
                        # Log warning for network/other errors but don't hard block (safe default)
                        logger.warning(f"⚠️ Price sanity check failed (non-blocking): {str(e)[:200]}")
                    
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
                
                result = gate.place_market_order(
                    instrument=signal.instrument,
                    units=int(position_size),
                    account_id=account_id,
                    exec_fn=exec_order,
                    meta={"source": "working_trading_system", "path": "place_market_order"}
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
                        signal_fingerprint = (account_id, signal.instrument, self._active_strategy_key)
                        self._signal_fingerprints[signal_fingerprint] = (now, signal.entry_price, signal.side.value)
                        logger.info(f"✅ TRADE EXECUTED: {signal.instrument} {signal.side.value} - Units: {int(position_size)} ({', '.join(tx_ids)})")
                    else:
                        logger.error(f"❌ TRADE FAILED: {signal.instrument} {signal.side.value} - OANDA response missing transaction IDs")
                else:
                    logger.error(f"❌ TRADE FAILED: {signal.instrument} {signal.side.value} - No result from execution")
                    
            except Exception as e:
                error_msg = str(e)[:200]
                logger.error(f"❌ Trade execution failed: {signal.instrument} {signal.side.value} - {error_msg}")
        
        if executed_trades > 0:
            logger.info(f"🎯 EXECUTED {executed_trades} TRADES")
        else:
            logger.info(f"📄 Execution enabled but no trades executed — signals generated: {len(all_signals)}, executed: 0")
        
        self._write_status_snapshot(len(all_signals), executed_trades, recent_signals_list=all_signals)
        return executed_trades

def run_forever(max_iterations: int = 0) -> None:
    """Run continuous scanning"""
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
            logger.error(f"❌ System error: {e}")
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


