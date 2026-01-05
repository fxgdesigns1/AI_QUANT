"""
Compatibility shim for older imports.

Goals:
- Allow runner to start for paper-mode scanning/status
- Keep secrets env-only
- Minimal surface area; upgrade later if needed
"""

from dataclasses import dataclass
import os

@dataclass
class SimpleAccount:
    account_id: str

class SimpleAccountManager:
    def __init__(self) -> None:
        aid = os.getenv("OANDA_ACCOUNT_ID", "").strip()
        if not aid:
            raise RuntimeError("Missing OANDA_ACCOUNT_ID (set in environment)")
        self._accounts = [SimpleAccount(account_id=aid)]
        
        # Minimal account configs for compatibility
        self.account_configs = {
            aid: {
                'account_id': aid,
                'strategy': 'momentum',
                'enabled': False,  # Disabled by default for safety
                'paper_mode': True
            }
        }

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
