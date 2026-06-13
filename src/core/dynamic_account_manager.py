"""
Compatibility shim for older imports.

Goals:
- Allow runner to start for paper-mode scanning/status
- Keep secrets env-only
- Minimal surface area; upgrade later if needed
- Support multiple accounts via ACCOUNT_ID_PREFIX + ACCOUNT_SUFFIX_ALLOWLIST
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

def _split_csv(v: str) -> list:
    """Split comma-separated string into list"""
    if not v:
        return []
    parts = [p.strip() for p in v.split(',')]
    return [p for p in parts if p]

class SimpleAccountManager:
    def __init__(self) -> None:
        execution_unlock_ok = os.getenv("EXECUTION_UNLOCK_OK", "").strip().lower() == "true"
        
        # Load account IDs: prefer ACCOUNT_SUFFIX_ALLOWLIST + ACCOUNT_ID_PREFIX, fallback to OANDA_ACCOUNT_ID
        account_id_prefix = os.getenv("ACCOUNT_ID_PREFIX", "101-004-30719775-").strip()
        account_suffix_allowlist_raw = os.getenv("ACCOUNT_SUFFIX_ALLOWLIST", "").strip()
        account_suffix_allowlist = _split_csv(account_suffix_allowlist_raw) if account_suffix_allowlist_raw else []
        
        # PHASE 1: Extend allowlist to include '006' for OANDA PRACTICE account (preserve existing order)
        if '006' not in account_suffix_allowlist:
            account_suffix_allowlist.append('006')
            logger.info("✅ Account suffix '006' added to allowlist (standard trading account - isolation disabled)")
        
        # Legacy: single account ID
        aid_single = os.getenv("OANDA_ACCOUNT_ID", "").strip()
        
        account_ids = []
        
        # Priority 1: Use suffix allowlist if set (multi-account mode)
        if account_suffix_allowlist:
            for suffix in account_suffix_allowlist:
                account_id = f"{account_id_prefix}{suffix}"
                account_ids.append(account_id)
            logger.info(f"📋 Loaded {len(account_ids)} accounts from ACCOUNT_SUFFIX_ALLOWLIST: {account_suffix_allowlist}")
        # Priority 2: Use single OANDA_ACCOUNT_ID (backward compatibility)
        elif aid_single:
            account_ids.append(aid_single)
            logger.info(f"📋 Loaded single account from OANDA_ACCOUNT_ID: {aid_single[-3:]}")
        # Priority 3: No accounts configured
        else:
            if execution_unlock_ok:
                # If execution is unlocked but account ID missing, fail closed
                raise RuntimeError(
                    "EXECUTION_UNLOCK_OK=true requires accounts to be configured. "
                    "Set ACCOUNT_SUFFIX_ALLOWLIST (e.g., '001,002') or OANDA_ACCOUNT_ID, "
                    "or set EXECUTION_UNLOCK_OK=false for signals-only mode."
                )
            # Paper-safe: allow no-account mode for scanning-only when execution is locked
            logger.warning("⚠️ No accounts configured - running in paper mode with zero accounts (signals-only)")
            self._accounts = []
            self.account_configs = {}
            return
        
        # Build account objects and configs
        self._accounts = [SimpleAccount(account_id=aid) for aid in account_ids]
        self.account_configs = {
            aid: SimpleAccountConfig(
                account_id=aid,
                strategy_name='momentum',
                instruments=['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']
            )
            for aid in account_ids
        }
        
        # Defensive logging: Log each account activation
        for account_id in account_ids:
            account_suffix = account_id[-3:] if len(account_id) >= 3 else account_id
            logger.info(f"ACCOUNT_ACTIVE account={account_suffix} full_id={account_id}")
    
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
