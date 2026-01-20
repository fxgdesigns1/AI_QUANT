"""
Execution Gate - Single Source of Truth for Live Trading Guards

SAFETY FIRST:
- Paper is default; live requires explicit dual-confirmation
- Kill-switch blocks all execution
- Max daily loss circuit breaker
- All decisions logged with reason codes
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, Callable
from datetime import datetime, timezone, timedelta

@dataclass
class ExecutionDecision:
    """Execution gate decision result"""
    allowed: bool
    mode: str  # 'paper' or 'live'
    reason_code: str  # Standardized reason code
    details: Optional[Dict[str, Any]] = None  # Non-secret context


class ExecutionGuard:
    """
    Single source of truth for execution guards.
    
    Canonical controls (env vars):
    - TRADING_MODE=paper|live (default: paper)
    - LIVE_TRADING_ENABLED=true|false (must be true for live)
    - LIVE_CONFIRM_TOKEN (must be non-empty for live; sourced from env/Secret Manager)
    - KILL_SWITCH=true|false (blocks all execution)
    - MAX_DAILY_LOSS_USD=<number> (circuit breaker threshold)
    - EXECUTION_UNLOCK_OK=true|false (paper execution gate from M3)
    """
    
    def __init__(self):
        """Initialize guard (reads env at decision time, not init)"""
        pass
    
    def _get_env(self, key: str, default: str = "") -> str:
        """Get env var safely"""
        return os.getenv(key, default).strip()
    
    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get env var as boolean"""
        val = self._get_env(key, "").lower()
        return val in ("true", "1", "yes", "on")
    
    def _get_env_float(self, key: str, default: float = 0.0) -> float:
        """Get env var as float"""
        try:
            return float(self._get_env(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def _check_daily_pnl(self, max_daily_loss_usd: float) -> Tuple[bool, Optional[str]]:
        """
        Check if daily PnL has exceeded max loss threshold.
        
        Returns:
            (is_blocked, reason_code)
            - If PnL data unavailable: (False, None) for paper, (True, "PNL_UNAVAILABLE") for live
            - If threshold exceeded: (True, "MAX_DAILY_LOSS_TRIPPED")
            - Otherwise: (False, None)
        """
        if max_daily_loss_usd <= 0:
            return (False, None)  # No limit set
        
        # Try to read from trade ledger if available
        try:
            from src.control_plane.trade_ledger import get_trade_ledger
            ledger = get_trade_ledger()
            
            # Read recent trades (last 24 hours)
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            all_trades = ledger.read_trades(limit=1000, offset=0)
            
            daily_pnl = 0.0
            for trade in all_trades:
                trade_time_str = trade.get("logged_at") or trade.get("entry_time")
                if trade_time_str:
                    try:
                        trade_time = datetime.fromisoformat(trade_time_str.replace('Z', '+00:00'))
                        if trade_time >= cutoff and trade.get("pnl") is not None:
                            daily_pnl += float(trade.get("pnl", 0))
                    except (ValueError, AttributeError, TypeError):
                        continue
            
            if daily_pnl <= -max_daily_loss_usd:
                return (True, "MAX_DAILY_LOSS_TRIPPED")
            return (False, None)
            
        except (ImportError, AttributeError, Exception):
            # PnL data not available - block only in live mode
            trading_mode = self._get_env("TRADING_MODE", "paper").lower()
            if trading_mode == "live":
                return (True, "PNL_UNAVAILABLE")
            return (False, None)  # Allow paper if PnL unavailable
    
    def decision(self) -> ExecutionDecision:
        """
        Make execution decision based on canonical controls.
        
        Decision order:
        1. KILL_SWITCH => block (KILL_SWITCH_ON)
        2. TRADING_MODE != 'live' => allow paper path (PAPER_MODE)
        3. TRADING_MODE == 'live' requires LIVE_TRADING_ENABLED == 'true' => else block (LIVE_FLAG_OFF)
        4. LIVE_CONFIRM_TOKEN must be present and non-empty => else block (LIVE_CONFIRM_MISSING)
        5. MAX_DAILY_LOSS_USD check => block if tripped (MAX_DAILY_LOSS_TRIPPED or PNL_UNAVAILABLE)
        
        Returns:
            ExecutionDecision with allowed, mode, reason_code
        """
        # 1. Kill switch check (highest priority)
        kill_switch = self._get_env_bool("KILL_SWITCH", False)
        if kill_switch:
            return ExecutionDecision(
                allowed=False,
                mode="paper",  # Default to paper when blocked
                reason_code="KILL_SWITCH_ON",
                details={"kill_switch": True}
            )
        
        # 2. Trading mode check
        trading_mode = self._get_env("TRADING_MODE", "paper").lower()
        
        if trading_mode != "live":
            # Paper mode - allow if EXECUTION_ENABLED=true OR PAPER_EXECUTION_ENABLED=true
            # OR if EXECUTION_UNLOCK_OK=true (backward compatibility)
            execution_enabled = self._get_env_bool("EXECUTION_ENABLED", False)
            paper_execution_enabled = self._get_env_bool("PAPER_EXECUTION_ENABLED", False)
            execution_unlock = self._get_env_bool("EXECUTION_UNLOCK_OK", False)
            
            if execution_enabled or paper_execution_enabled or execution_unlock:
                return ExecutionDecision(
                    allowed=True,
                    mode="paper",
                    reason_code="PAPER_MODE",
                    details={
                        "execution_enabled": execution_enabled,
                        "paper_execution_enabled": paper_execution_enabled,
                        "execution_unlock_ok": execution_unlock
                    }
                )
            else:
                return ExecutionDecision(
                    allowed=False,
                    mode="paper",
                    reason_code="PAPER_EXECUTION_LOCKED",
                    details={
                        "execution_enabled": False,
                        "paper_execution_enabled": False,
                        "execution_unlock_ok": False
                    }
                )
        
        # 3. Live mode - require LIVE_TRADING_ENABLED
        live_enabled = self._get_env_bool("LIVE_TRADING_ENABLED", False)
        if not live_enabled:
            return ExecutionDecision(
                allowed=False,
                mode="live",
                reason_code="LIVE_FLAG_OFF",
                details={"live_trading_enabled": False}
            )
        
        # 4. Dual confirmation - require LIVE_CONFIRM_TOKEN
        live_confirm_token = self._get_env("LIVE_CONFIRM_TOKEN", "")
        if not live_confirm_token:
            return ExecutionDecision(
                allowed=False,
                mode="live",
                reason_code="LIVE_CONFIRM_MISSING",
                details={"live_confirm_token_present": False}
            )
        
        # 5. Max daily loss check
        max_daily_loss_usd = self._get_env_float("MAX_DAILY_LOSS_USD", 0.0)
        is_blocked, loss_reason = self._check_daily_pnl(max_daily_loss_usd)
        if is_blocked:
            return ExecutionDecision(
                allowed=False,
                mode="live",
                reason_code=loss_reason or "MAX_DAILY_LOSS_TRIPPED",
                details={"max_daily_loss_usd": max_daily_loss_usd}
            )
        
        # All checks passed - live trading allowed
        return ExecutionDecision(
            allowed=True,
            mode="live",
            reason_code="LIVE_ALLOWED",
            details={
                "live_trading_enabled": True,
                "live_confirm_token_present": True
            }
        )
    
    def get_guard_status(self) -> Dict[str, Any]:
        """
        Get guard status for /api/status endpoint (no secrets).
        
        Returns:
            Dict with allowed, reason_code, mode
        """
        decision = self.decision()
        return {
            "allowed": decision.allowed,
            "reason_code": decision.reason_code,
            "mode": decision.mode
        }
    
    def place_market_order(
        self,
        *,
        instrument: str,
        units: int,
        account_id: str,
        exec_fn: Callable[[], Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Place a market order through the execution gate.
        
        CONTRACT: OANDA-ONLY execution path. Paper uses OANDA Practice API (real orders).
        No mock/sim broker. All orders go to OANDA.
        
        Args:
            instrument: Trading instrument (e.g., 'EUR_USD')
            units: Order size (positive for buy, negative for sell)
            account_id: OANDA account ID
            exec_fn: Callable that executes the OANDA API call and returns result
            meta: Optional metadata dict
        
        Returns:
            OANDA API response (orderCreateTransaction or orderFillTransaction)
        
        Raises:
            RuntimeError: If execution is blocked by guard
        """
        decision = self.decision()
        
        if not decision.allowed:
            raise RuntimeError(f"Execution blocked by gate: {decision.reason_code}")
        
        # Execute real OANDA order (Practice for paper, Live for live)
        # Contract: No simulation - all orders go to OANDA
        try:
            result = exec_fn()
            return result
        except Exception as e:
            # Log error but don't expose secrets
            error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
            raise RuntimeError(f"OANDA order execution failed: {error_msg}")


# Compatibility alias
class ExecutionGate(ExecutionGuard):
    """Compatibility alias for existing code"""
    pass
