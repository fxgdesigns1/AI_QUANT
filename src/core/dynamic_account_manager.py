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

    def list_accounts(self):
        return self._accounts

def get_account_manager():
    return SimpleAccountManager()
