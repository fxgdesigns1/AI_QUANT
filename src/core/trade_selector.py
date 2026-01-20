"""
Trade Selection Module - Top-N Daily Selection
Implements rolling daily pool to select best trades regardless of timing.
"""

import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class Candidate:
    signal: Any
    score: float
    first_seen_at: float
    last_seen_at: float
    metadata: Dict[str, Any]
    
    # Track if this candidate has already been executed
    executed: bool = False

class TradeSelector:
    """
    Selects the best trades of the day.
    Maintains a rolling pool of top-N candidates.
    Executes at session cutoff OR immediately if exceptional quality.
    """
    
    def __init__(self):
        # Pool storage: account_id -> List[Candidate]
        self.pool: Dict[str, List[Candidate]] = {}
        
        self.config = {
            "mode": "TOP_N_DAILY", 
            "daily_trade_limit": 3,
            "min_confidence_threshold": 0.65,
            "early_session_penalty_minutes": 60,
            "re_rank_on_each_scan": True,
            "execution_cutoff": "NY_CLOSE", # 16:55 ET approx
            "allow_exceptional_early_execution": True,
            "exceptional_confidence_threshold": 0.85
        }
        logger.info("TradeSelector initialized (Default: TOP_N_DAILY)")

    def update_config(self, trade_selection_config: Any):
        """Update config from RuntimeConfig object"""
        if not trade_selection_config:
            return
            
        # Handle both dict and object (dataclass)
        if isinstance(trade_selection_config, dict):
            src = trade_selection_config
        else:
            # Assume dataclass
            src = {
                "mode": trade_selection_config.mode,
                "daily_trade_limit": trade_selection_config.daily_trade_limit,
                "min_confidence_threshold": trade_selection_config.min_confidence_threshold,
                "early_session_penalty_minutes": trade_selection_config.early_session_penalty_minutes,
                "re_rank_on_each_scan": trade_selection_config.re_rank_on_each_scan,
                "execution_cutoff": trade_selection_config.execution_cutoff,
                "allow_exceptional_early_execution": trade_selection_config.allow_exceptional_early_execution,
                "exceptional_confidence_threshold": trade_selection_config.exceptional_confidence_threshold
            }
            
        # Log mode change
        old_mode = self.config.get("mode")
        new_mode = src.get("mode")
        if old_mode != new_mode:
            logger.info(f"🔄 Trade Selection Mode changed: {old_mode} -> {new_mode}")
            
        self.config.update(src)

    def calculate_score(self, signal: Any) -> float:
        """Calculate quality score (0-100)"""
        # Extract metadata (safe access)
        meta = getattr(signal, 'metadata', {}) or {}
        confidence = float(meta.get('confidence', 0.0))
        regime = meta.get('regime', 'UNKNOWN')
        condition = meta.get('condition', 'NORMAL')
        
        # Base score from confidence (0.0-1.0 -> 0-100)
        score = confidence * 100.0
        
        # Regime Bonus
        if regime in ['TRENDING_UP', 'TRENDING_DOWN']:
            score += 10
        elif regime == 'RANGING' and 'range' in str(getattr(signal, 'strategy_key', '')).lower():
            score += 15 # Strong fit for range strategy
            
        # Volatility Bonus/Penalty
        if condition == 'VOLATILE':
            if confidence < 0.6:
                score -= 5
                
        return score

    def _is_cutoff_reached(self) -> bool:
        """Check if execution cutoff time is reached"""
        cutoff_setting = self.config.get("execution_cutoff", "NY_CLOSE")
        
        # Simple NY_CLOSE logic (approx 21:00 UTC)
        # TODO: Make this robust with timezone awareness if needed
        if cutoff_setting == "NY_CLOSE":
            now_utc = datetime.now(timezone.utc)
            # Execute near close (20:00 - 21:00 UTC is roughly 3-4pm ET)
            # Let's say execution window opens at 20:00 UTC
            return now_utc.hour >= 20
            
        if cutoff_setting == "IMMEDIATE": # For testing
            return True
            
        return False

    def select_trades(self, current_signals: List[Any], 
                      daily_trades: Dict[str, int], 
                      daily_limits: Dict[str, int]) -> List[Any]:
        """
        Process signals, update pool, and return trades ready for execution.
        """
        
        mode = self.config.get("mode")
        
        # Legacy Mode Support
        if mode == "SPEED":
            return current_signals
        elif mode == "QUALITY_OVER_SPEED":
            # Fallback to buffer logic if config hasn't updated to TOP_N fully?
            # Or simplified: just return nothing if we are refactoring.
            # But wait, I'm REPLACING the file. So I should implement TOP_N.
            pass

        now = time.time()
        daily_limit_default = self.config.get("daily_trade_limit", 3)
        min_conf = self.config.get("min_confidence_threshold", 0.65)
        
        # 1. Update Pool with Current Signals
        # -----------------------------------
        
        # Group current signals by account
        signals_by_account = {}
        for s in current_signals:
            if s.account_id not in signals_by_account:
                signals_by_account[s.account_id] = []
            signals_by_account[s.account_id].append(s)
            
        # Process each account's pool
        # Accounts that have no current signals but have a pool need to be checked too?
        # Yes, candidates remain valid even if not in current scan? 
        # Actually, "Discard candidates that no longer validate on subsequent scans"
        # So if a signal is NOT in current_signals, we should remove it from pool?
        # That might be too strict if scans are intermittent. 
        # Let's assume current_signals contains ALL active valid signals.
        
        # We iterate over all accounts we know about (keys in pool + keys in current signals)
        all_accounts = set(self.pool.keys()) | set(signals_by_account.keys())
        
        executable_trades = []
        
        for acc_id in all_accounts:
            if acc_id not in self.pool:
                self.pool[acc_id] = []
                
            account_signals = signals_by_account.get(acc_id, [])
            limit = daily_limits.get(acc_id, daily_limit_default)
            
            # Map current signals by key for easy lookup
            current_map = {}
            for s in account_signals:
                key = (s.instrument, getattr(s, 'strategy_key', 'unknown'))
                current_map[key] = s
                
            # Update Pool
            # A. Remove stale candidates (not in current scan)
            # Only keep if they are still valid. If strategy stops sending it, it's invalid.
            self.pool[acc_id] = [c for c in self.pool[acc_id] 
                                 if (c.signal.instrument, getattr(c.signal, 'strategy_key', 'unknown')) in current_map
                                 and not c.executed] # Also remove already executed
            
            # B. Update/Add new candidates
            for s in account_signals:
                score = self.calculate_score(s)
                
                # Check min confidence
                conf = float(getattr(s, 'metadata', {}).get('confidence', 0))
                if conf < min_conf:
                    continue
                    
                key = (s.instrument, getattr(s, 'strategy_key', 'unknown'))
                
                # Check if already in pool
                existing = next((c for c in self.pool[acc_id] if (c.signal.instrument, getattr(c.signal, 'strategy_key', 'unknown')) == key), None)
                
                if existing:
                    existing.last_seen_at = now
                    existing.score = score
                    existing.signal = s # Update signal object
                else:
                    # New candidate. 
                    # If pool full, check if we replace lowest.
                    if len(self.pool[acc_id]) < limit:
                        new_cand = Candidate(s, score, now, now, getattr(s, 'metadata', {}))
                        self.pool[acc_id].append(new_cand)
                        logger.info(f"📥 POOL ADD: {s.instrument} Score={score:.1f} (Pool {len(self.pool[acc_id])}/{limit})")
                    else:
                        # Pool full. Find lowest score.
                        lowest = min(self.pool[acc_id], key=lambda c: c.score)
                        if score > lowest.score:
                            logger.info(f"🔄 POOL REPLACE: {s.instrument} ({score:.1f}) replaces {lowest.signal.instrument} ({lowest.score:.1f})")
                            self.pool[acc_id].remove(lowest)
                            new_cand = Candidate(s, score, now, now, getattr(s, 'metadata', {}))
                            self.pool[acc_id].append(new_cand)
                        else:
                            # Rejected
                            pass
                            
            # 2. Check Execution Triggers
            # ---------------------------
            
            # Sort pool by score
            self.pool[acc_id].sort(key=lambda c: c.score, reverse=True)
            
            cutoff_reached = self._is_cutoff_reached()
            
            for cand in self.pool[acc_id]:
                if cand.executed: continue
                
                should_execute = False
                reason = ""
                
                # Exceptional Early Execution
                if self.config.get("allow_exceptional_early_execution"):
                    thresh = self.config.get("exceptional_confidence_threshold", 0.85)
                    conf = float(cand.metadata.get('confidence', 0))
                    if conf >= thresh:
                        should_execute = True
                        reason = "EXCEPTIONAL_IMMEDIATE"
                
                # Session Cutoff Execution
                if not should_execute and cutoff_reached:
                    should_execute = True
                    reason = "DAILY_BEST_SELECTED"
                    
                if should_execute:
                    logger.info(f"🚀 EXECUTING {cand.signal.instrument}: Score {cand.score:.1f} Reason: {reason}")
                    cand.executed = True # Mark as executed so we don't re-emit
                    # Add execution metadata to signal?
                    # s.metadata['execution_reason'] = reason
                    executable_trades.append(cand.signal)
                    
        return executable_trades

    def get_top_candidates(self, limit: int = None, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Introspect what the selector currently 'thinks' are the best trades.

        Args:
            limit: Max number of candidates to return. If None, uses config.daily_trade_limit.
            account_id: If provided, only show candidates for that account.
                        If None, show across all accounts.

        Returns:
            List of dicts sorted by score desc.
        """
        # Determine effective limit
        cfg_limit = self.config.get("daily_trade_limit", 3)
        eff_limit = cfg_limit if limit is None else int(limit)
        if eff_limit <= 0:
            return []

        # Flatten pool into a list
        items = []
        for acc, candidates in self.pool.items():
            if account_id is not None and acc != account_id:
                continue
            for c in candidates:
                meta = c.metadata or {}
                items.append({
                    "account_id": acc,
                    "instrument": getattr(c.signal, "instrument", "UNKNOWN"),
                    "strategy_key": getattr(c.signal, "strategy_key", "unknown"),
                    "score": float(c.score),
                    "confidence": float(meta.get("confidence", 0.0)),
                    "regime": meta.get("regime", "UNKNOWN"),
                    "condition": meta.get("condition", "NORMAL"),
                    "first_seen_at": c.first_seen_at,
                    "last_seen_at": c.last_seen_at,
                    "executed": bool(c.executed),
                })

        # Sort by score desc and trim to eff_limit
        items.sort(key=lambda x: x["score"], reverse=True)
        return items[:eff_limit]
