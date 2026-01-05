"""Trade ledger - append-only JSONL trade log

REQUIREMENTS:
- Append-only (no updates/deletes)
- One JSON object per line
- Account ID redaction (last 4 only)
- Thread-safe writes
- No secrets in ledger
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading


def redact_account_id(account_id: str) -> str:
    """Redact account ID to show last 4 digits only
    
    Args:
        account_id: Full account ID (e.g., "101-004-30719775-001")
    
    Returns:
        Redacted account ID (e.g., "****-****-****-001")
    """
    if not account_id:
        return "****-****-****-****"
    
    # Extract last 4 digits (assuming format: xxx-xxx-xxxxxxxx-xxx)
    parts = account_id.split('-')
    if len(parts) >= 4:
        # Format: xxx-xxx-xxxxxxxx-xxx -> show last 4 of last segment
        last_part = parts[-1]
        if len(last_part) >= 4:
            last_4 = last_part[-4:]
            return f"****-****-****-{last_4}"
    
    # Fallback: just mask everything except last 4 chars
    if len(account_id) >= 4:
        return "****" + account_id[-4:]
    
    return "****"


class TradeLedger:
    """Append-only trade ledger (JSONL format)
    
    Thread-safe writes. Reads from JSONL file.
    """
    
    def __init__(self, ledger_path: Optional[str] = None):
        """Initialize trade ledger
        
        Args:
            ledger_path: Path to JSONL ledger file. Defaults to data/trade_ledger.jsonl
        """
        if ledger_path is None:
            ledger_path = os.getenv("TRADE_LEDGER_PATH", "data/trade_ledger.jsonl")
        
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
    
    def write_trade(self, trade_data: Dict[str, Any]) -> None:
        """Write trade to ledger (append-only)
        
        Args:
            trade_data: Trade record dict. Account IDs will be redacted.
        
        Raises:
            IOError: If write fails
        """
        # Redact account IDs
        safe_data = self._redact_secrets(trade_data.copy())
        
        # Ensure required fields
        safe_data.setdefault("logged_at", datetime.now(timezone.utc).isoformat())
        
        # Serialize to JSON (single line, no indentation)
        trade_json = json.dumps(safe_data, sort_keys=True)
        
        # Thread-safe append
        with self._write_lock:
            with open(self.ledger_path, 'a', encoding='utf-8') as f:
                f.write(trade_json + '\n')
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
    
    def read_trades(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Read trades from ledger (most recent first)
        
        Args:
            limit: Maximum number of trades to return
            offset: Number of trades to skip (for pagination)
        
        Returns:
            List of trade records (most recent first)
        """
        if not self.ledger_path.exists():
            return []
        
        trades = []
        
        # Read all lines (simple approach - for small ledgers)
        # For large ledgers, would need to read backwards or use database
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trade = json.loads(line)
                        trades.append(trade)
                    except json.JSONDecodeError:
                        # Skip corrupted lines
                        continue
        except IOError:
            return []
        
        # Reverse to get most recent first
        trades.reverse()
        
        # Apply pagination
        return trades[offset:offset + limit]
    
    def count_trades(self) -> int:
        """Count total trades in ledger
        
        Returns:
            Total number of trades
        """
        if not self.ledger_path.exists():
            return 0
        
        count = 0
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        count += 1
        except IOError:
            return 0
        
        return count
    
    def _redact_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact secrets from trade data
        
        Args:
            data: Trade data dict
        
        Returns:
            Dict with secrets redacted
        """
        # Redact account_id fields
        for key in ['account_id', 'account_id_redacted', 'account']:
            if key in data and data[key]:
                data[f"{key}_redacted"] = redact_account_id(str(data[key]))
                if key != f"{key}_redacted":
                    del data[key]  # Remove original if not the redacted key
        
        # Remove any other secret-like keys
        secret_patterns = ['api_key', 'token', 'password', 'secret']
        keys_to_remove = [k for k in data.keys() 
                         if any(pattern in k.lower() for pattern in secret_patterns)]
        for key in keys_to_remove:
            del data[key]
        
        return data


# Global instance
_trade_ledger_instance: Optional[TradeLedger] = None
_ledger_lock = threading.Lock()


def get_trade_ledger() -> TradeLedger:
    """Get global trade ledger instance (singleton)
    
    Returns:
        TradeLedger instance
    """
    global _trade_ledger_instance
    
    if _trade_ledger_instance is None:
        with _ledger_lock:
            if _trade_ledger_instance is None:
                _trade_ledger_instance = TradeLedger()
    
    return _trade_ledger_instance
