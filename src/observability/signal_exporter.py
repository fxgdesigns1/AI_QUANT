import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)

class SignalExporter:
    """
    Singleton, append-only signal exporter.
    Writes signals to a local JSONL file for downstream consumption (e.g., bridges).
    
    Principles:
    - Never blocks execution
    - Never throws exceptions to caller
    - No network calls
    - Append-only persistence
    - Thread-safe
    """
    
    _instance = None
    _lock = threading.Lock()
    _file_lock = threading.Lock()
    
    # Configuration
    # We use os.path.expanduser to dynamically determine home directory
    # This ensures it works on VM (typically /home/username) and local (if mirrored)
    LOG_FILE_PATH = os.path.expanduser("~/gcloud-system/logs/signals.jsonl")
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SignalExporter, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the exporter (ensure directory exists)."""
        try:
            log_dir = os.path.dirname(self.LOG_FILE_PATH)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
        except OSError:
            # Fallback for local development or permission issues
            # We silently switch to a local logs directory to prevent crash
            try:
                self.LOG_FILE_PATH = os.path.join(os.getcwd(), "logs", "signals.jsonl")
                log_dir = os.path.dirname(self.LOG_FILE_PATH)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                logger.warning(f"Using fallback log path: {self.LOG_FILE_PATH}")
            except Exception:
                pass # Total silence if fallback also fails
        except Exception as e:
            # We log but suppress errors to ensure fail-safety
            logger.error(f"Failed to initialize SignalExporter: {e}")

    def emit(self,
             strategy: str,
             symbol: str,
             side: str,
             units: int,
             entry_type: str = "MARKET",
             stop_loss: Optional[float] = None,
             take_profit: Optional[float] = None,
             confidence: float = 0.0,
             regime: str = "unknown",
             session: str = "unknown",
             news_state: str = "unknown",
             execution_allowed: bool = False,
             block_reason: Optional[str] = None,
             account: str = "unknown",
             bridge_account: Optional[str] = None,
             meta: Optional[Dict[str, Any]] = None,
             fanout: Optional[bool] = None) -> Optional[str]:
        """
        Emit a trading signal to the append-only log.
        
        Args:
            strategy: Strategy identifier
            symbol: Trading instrument (e.g., 'EUR_USD')
            side: 'BUY' or 'SELL'
            units: Number of units (absolute value)
            entry_type: 'MARKET' or 'LIMIT'
            stop_loss: Stop loss price
            take_profit: Take profit price
            confidence: Signal confidence (0.0-1.0)
            regime: Market regime detected
            session: Trading session
            news_state: News filter state
            execution_allowed: Whether the execution gate allowed this trade
            block_reason: Reason if blocked
            account: Target account ID
            bridge_account: Bridge Account Mapping (e.g. 'ftmo_eval_primary')
            meta: Additional metadata
            
        Returns:
            signal_id (str) if successful, None otherwise
        """
        try:
            if fanout is None:
                try:
                    from src.observability.bridge_signal_router import _load_bridge_config
                    cfg = _load_bridge_config()
                    rules = cfg.get("routing_rules") or cfg.get("fanout") or {}
                    fanout = rules.get("fanout_enabled", rules.get("enabled", False))
                except Exception:
                    fanout = False
            if fanout:
                from src.observability.bridge_signal_router import emit_signal as bridge_emit
                return bridge_emit(
                    strategy=strategy, symbol=symbol, side=side, units=units,
                    bridge_account=bridge_account, fanout=True,
                    entry_type=entry_type, stop_loss=stop_loss, take_profit=take_profit,
                    confidence=confidence, execution_allowed=execution_allowed,
                    meta=meta, account=account, regime=regime, session=session,
                    news_state=news_state, block_reason=block_reason,
                )
            # 1. Construct Signal Object
            timestamp_utc = datetime.now(timezone.utc).isoformat()
            signal_id = str(uuid.uuid4())
            
            signal_data = {
                "signal_id": signal_id,
                "timestamp_utc": timestamp_utc,
                "system": "ALPHA",
                "strategy": strategy,
                "account": account,
                "bridge_account": bridge_account,
                "symbol": symbol,
                "side": side,
                "units": units,
                "entry_type": entry_type,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": confidence,
                "regime": regime,
                "session": session,
                "news_state": news_state,
                "execution_allowed": execution_allowed,
                "block_reason": block_reason
            }
            
            # Add metadata if provided, but prevent overwriting core fields
            if meta:
                # Filter out keys that would overwrite standard fields
                safe_meta = {k: v for k, v in meta.items() if k not in signal_data}
                signal_data["meta"] = safe_meta

            # 2. Serialize to JSON
            json_line = json.dumps(signal_data)
            
            # 3. Write to file (Thread-safe)
            with self._file_lock:
                # Force directory check on every write to guarantee existence
                # This is idempotent and cheap, but ensures robustness if log dir is deleted
                log_dir = os.path.dirname(self.LOG_FILE_PATH)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                    
                with open(self.LOG_FILE_PATH, "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Failed to emit signal: {e}")
            return None

    def read_signals(self, 
                    limit: int = 100, 
                    strategy: Optional[str] = None, 
                    symbol: Optional[str] = None, 
                    since_ts: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read signals from the log file.
        Designed for API consumption.
        
        Args:
            limit: Max number of records to return (from end)
            strategy: Filter by strategy ID
            symbol: Filter by symbol
            since_ts: Filter by ISO timestamp (>=)
            
        Returns:
            List of signal dictionaries
        """
        signals = []
        try:
            if not os.path.exists(self.LOG_FILE_PATH):
                return []
                
            # Efficiently read last N lines would be better for large files,
            # but for simplicity and robustness we read line by line here.
            # In a production system with massive logs, rotation + 'tail' logic is needed.
            # For now, we read all and filter in memory (assuming file rotation is handled externally).
            
            with self._file_lock:
                with open(self.LOG_FILE_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            
            # Reverse to get latest first
            for line in reversed(lines):
                if len(signals) >= limit:
                    break
                    
                try:
                    line = line.strip()
                    if not line:
                        continue
                        
                    data = json.loads(line)
                    
                    # Apply Filters
                    if strategy and data.get("strategy") != strategy:
                        continue
                    if symbol and data.get("symbol") != symbol:
                        continue
                    if since_ts and data.get("timestamp_utc") < since_ts:
                        continue
                        
                    signals.append(data)
                except json.JSONDecodeError:
                    continue
                    
            return signals
            
        except Exception as e:
            logger.error(f"Failed to read signals: {e}")
            return []

# Convenience global instance accessor
_exporter = SignalExporter()

def get_signal_exporter() -> SignalExporter:
    return _exporter
