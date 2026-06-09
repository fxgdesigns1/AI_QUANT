"""
Compatibility shim for older imports.

Goals:
- Allow runner to start for paper-mode scanning/status
- Keep secrets env-only
- Minimal surface area; upgrade later if needed
"""

from dataclasses import dataclass
import os
import logging

logger = logging.getLogger(__name__)

@dataclass
class SimpleAccount:
    account_id: str

@dataclass
class SimpleAccountConfig:
    """Minimal account config object for compatibility"""
    account_id: str
    strategy_name: str = 'momentum'
    instruments: list = None
    
    def __post_init__(self):
        if self.instruments is None:
            self.instruments = ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']

class SimpleAccountManager:
    def __init__(self) -> None:
        execution_unlock_ok = os.getenv("EXECUTION_UNLOCK_OK", "").strip().lower() == "true"
        aid = os.getenv("OANDA_ACCOUNT_ID", "").strip()
        
        if not aid:
            if execution_unlock_ok:
                # If execution is unlocked but account ID missing, fail closed
                raise RuntimeError(
                    "EXECUTION_UNLOCK_OK=true requires OANDA_ACCOUNT_ID to be set. "
                    "Set OANDA_ACCOUNT_ID or set EXECUTION_UNLOCK_OK=false for signals-only mode."
                )
            # Paper-safe: allow no-account mode for scanning-only when execution is locked
            logger.warning("⚠️ OANDA_ACCOUNT_ID not set - running in paper mode with zero accounts (signals-only)")
            self._accounts = []
            self.account_configs = {}
        else:
            self._accounts = [SimpleAccount(account_id=aid)]
            # Minimal account configs for compatibility
            self.account_configs = {
                aid: SimpleAccountConfig(
                    account_id=aid,
                    strategy_name='momentum',
                    instruments=['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']
                )
            }
    
    def execution_capable(self) -> bool:
        """Check if execution is capable (has accounts and execution unlocked)"""
        execution_unlock_ok = os.getenv("EXECUTION_UNLOCK_OK", "").strip().lower() == "true"
        return execution_unlock_ok and len(self._accounts) > 0
    
    def accounts_loaded(self) -> int:
        """Return count of loaded accounts"""
        return len(self._accounts)

    def list_accounts(self):
        return self._accounts
    
    def get_active_accounts(self):
        """Return list of active accounts (compatibility method)"""
        return [acc.account_id for acc in self._accounts]
    
    def get_account_client(self, account_id: str):
        """Return account client (stub - returns None for paper mode)"""
        return None  # No real broker client in stub mode

def get_account_manager():
    return SimpleAccountManager()
