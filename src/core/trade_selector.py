"""
Trade Selection Module - Top-N Daily Selection
Implements rolling daily pool to select best trades regardless of timing.
"""

import logging
import time
import json
import os
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
    executed_at: Optional[float] = None

    # Stable key for dedupe/updates (must include account/instrument/strategy/side)
    key: Optional[Tuple[str, str, str, str]] = None

class TradeSelector:
    """
    Selects the best trades of the day.
    Maintains a rolling pool of top-N candidates.
    Executes at session cutoff OR immediately if exceptional quality.
    """
    
    DEFAULT_CONFIG: Dict[str, Any] = {
        "mode": "TOP_N_DAILY",
        "daily_trade_limit": 3,
        "min_confidence_threshold": 0.60,  # safe-but-not-overly-strict default
        "early_session_penalty_minutes": 60,
        "re_rank_on_each_scan": True,
        "execution_cutoff": "NY_CLOSE",  # NY_CLOSE|IMMEDIATE
        "allow_exceptional_early_execution": True,
        "exceptional_confidence_threshold": 0.60,
        # New controls
        "confidence_missing_policy": "reject",  # allow|reject
        "max_execute_per_account_per_cycle": 1,
        "executed_ttl_seconds": 6 * 60 * 60,  # 6h
    }

    def __init__(self, config: dict | None = None):
        # Pool storage: account_id -> List[Candidate]
        self.pool: Dict[str, List[Candidate]] = {}
        
        self.config: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
        self.update_config(config)
        logger.info("TradeSelector initialized")

    def _normalize_config(self, config: Any) -> Dict[str, Any]:
        """
        Normalize config shape.

        Accepts either:
        - Full runtime config dict containing key 'trade_selection' (dict)
        - trade_selection dict itself
        - RuntimeConfig/TradeSelectionSettings dataclass-like object (best-effort)
        """
        if not config:
            return {}

        # dict: accept full runtime config or already-trade_selection
        if isinstance(config, dict):
            ts = config.get("trade_selection")
            if isinstance(ts, dict):
                return ts
            return config

        # object (dataclass-like): best-effort extraction
        # If it has trade_selection attribute, unwrap it first.
        try:
            if hasattr(config, "trade_selection"):
                inner = getattr(config, "trade_selection")
                if isinstance(inner, dict):
                    return inner
                config = inner
        except Exception:
            pass

        src: Dict[str, Any] = {}
        for k in self.DEFAULT_CONFIG.keys():
            try:
                if hasattr(config, k):
                    src[k] = getattr(config, k)
            except Exception:
                continue
        return src

    def update_config(self, config: dict | None):
        """
        Update selector config WITHOUT resetting pool state.
        Merges normalized config over defaults and rejects unknown keys silently (safe).
        """
        normalized = self._normalize_config(config)
        if not normalized:
            return

        allowed = set(self.DEFAULT_CONFIG.keys())
        src = {k: v for k, v in normalized.items() if k in allowed and v is not None}

        old_mode = self.config.get("mode")
        new_mode = src.get("mode", old_mode)
        if old_mode != new_mode:
            logger.info(f"Trade Selection Mode changed: {old_mode} -> {new_mode}")

        merged = dict(self.DEFAULT_CONFIG)
        merged.update(self.config or {})
        merged.update(src)
        self.config = merged

    def _side_value(self, signal: Any) -> str:
        side = getattr(signal, "side", None)
        if side is None:
            return "UNKNOWN"
        return side.value if hasattr(side, "value") else str(side)

    def _candidate_key(self, signal: Any) -> Tuple[str, str, str, str]:
        account_id = getattr(signal, "account_id", "") or ""
        instrument = getattr(signal, "instrument", "UNKNOWN") or "UNKNOWN"
        strategy_key = getattr(signal, "strategy_key", "unknown") or "unknown"
        side = self._side_value(signal)
        return (account_id, instrument, str(strategy_key), str(side))

    def _extract_confidence(self, signal: Any) -> Optional[float]:
        # 1) metadata.confidence
        meta = getattr(signal, "metadata", {}) or {}
        try:
            if isinstance(meta, dict) and meta.get("confidence") is not None:
                return float(meta.get("confidence"))
        except Exception:
            pass

        # 2) signal.confidence / confidence_score / score
        for attr in ("confidence", "confidence_score", "score"):
            try:
                v = getattr(signal, attr, None)
                if v is not None:
                    return float(v)
            except Exception:
                continue

        # 3) metadata.confidence_score (fallback)
        try:
            if isinstance(meta, dict) and meta.get("confidence_score") is not None:
                return float(meta.get("confidence_score"))
        except Exception:
            pass

        return None

    def _effective_confidence(self, signal: Any) -> float:
        conf = self._extract_confidence(signal)
        if conf is not None:
            return conf
        policy = str(self.config.get("confidence_missing_policy", "reject")).lower()
        return 1.0 if policy == "allow" else 0.0

    def calculate_score(self, signal: Any) -> float:
        """Calculate quality score (0-100)"""
        # Extract metadata (safe access)
        meta = getattr(signal, 'metadata', {}) or {}
        confidence = float(self._effective_confidence(signal))
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
        max_execute_per_cycle = int(self.config.get("max_execute_per_account_per_cycle", 1) or 1)
        executed_ttl_seconds = float(self.config.get("executed_ttl_seconds", 6 * 60 * 60) or (6 * 60 * 60))
        
        # 1. Update Pool with Current Signals
        # -----------------------------------
        
        # Group current signals by account
        signals_by_account = {}
        for s in current_signals:
            acc_id = getattr(s, "account_id", None) or "UNKNOWN"
            if acc_id not in signals_by_account:
                signals_by_account[acc_id] = []
            signals_by_account[acc_id].append(s)
            
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
                key = self._candidate_key(s)
                current_map[key] = s
                
            # Update Pool
            # A. Remove stale candidates (not in current scan)
            # Only keep if they are still valid. If strategy stops sending it, it's invalid.
            pruned: List[Candidate] = []
            for c in self.pool[acc_id]:
                # prune executed beyond TTL
                if c.executed and c.executed_at is not None and (now - c.executed_at) > executed_ttl_seconds:
                    continue
                # keep executed (within TTL) to prevent re-execution spam
                if c.executed:
                    pruned.append(c)
                    continue
                # keep only if still present in current scan
                c_key = c.key or self._candidate_key(c.signal)
                if c_key in current_map:
                    pruned.append(c)
            self.pool[acc_id] = pruned
            
            # B. Update/Add new candidates
            for s in account_signals:
                score = self.calculate_score(s)
                
                # Check min confidence
                conf = float(self._effective_confidence(s))
                if conf < float(min_conf):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"CONF_REJECT instrument={getattr(s, 'instrument', 'UNKNOWN')} "
                            f"conf={conf:.3f} threshold={float(min_conf):.3f}"
                        )
                    continue
                    
                key = self._candidate_key(s)
                
                # Check if already in pool
                existing = next((c for c in self.pool[acc_id] if (c.key or self._candidate_key(c.signal)) == key), None)
                
                if existing:
                    existing.last_seen_at = now
                    existing.score = score
                    existing.signal = s # Update signal object
                    existing.metadata = getattr(s, "metadata", {}) or {}
                    existing.key = key
                else:
                    # New candidate. 
                    # If pool full, check if we replace lowest.
                    active = [c for c in self.pool[acc_id] if not c.executed]
                    if len(active) < int(limit):
                        new_cand = Candidate(s, score, now, now, getattr(s, 'metadata', {}) or {}, executed=False, executed_at=None, key=key)
                        self.pool[acc_id].append(new_cand)
                        logger.info(
                            f"POOL ADD instrument={getattr(s,'instrument','UNKNOWN')} score={score:.1f} "
                            f"conf={conf:.3f} acc=***{str(acc_id)[-3:]} pool={len(active)+1}/{int(limit)}"
                        )
                    else:
                        # Pool full. Find lowest score.
                        lowest = min(active, key=lambda c: c.score)
                        if score > lowest.score:
                            logger.info(
                                f"POOL REPLACE instrument={getattr(s,'instrument','UNKNOWN')} score={score:.1f} "
                                f"replaces={getattr(lowest.signal,'instrument','UNKNOWN')} prev_score={lowest.score:.1f} "
                                f"acc=***{str(acc_id)[-3:]}"
                            )
                            self.pool[acc_id].remove(lowest)
                            new_cand = Candidate(s, score, now, now, getattr(s, 'metadata', {}) or {}, executed=False, executed_at=None, key=key)
                            self.pool[acc_id].append(new_cand)
                        else:
                            # Rejected
                            logger.info(
                                f"POOL REJECT instrument={getattr(s,'instrument','UNKNOWN')} score={score:.1f} "
                                f"cutoff={lowest.score:.1f} acc=***{str(acc_id)[-3:]} reason=DAILY_RANK_CUTOFF"
                            )
                            pass
                            
            # 2. Check Execution Triggers
            # ---------------------------
            
            # Sort pool by score
            self.pool[acc_id].sort(key=lambda c: c.score, reverse=True)
            
            cutoff_reached = self._is_cutoff_reached()

            executed_this_cycle = 0
            for cand in self.pool[acc_id]:
                if cand.executed:
                    continue
                if executed_this_cycle >= max_execute_per_cycle:
                    break
                
                should_execute = False
                reason = ""
                
                # Exceptional Early Execution
                if self.config.get("allow_exceptional_early_execution"):
                    thresh = self.config.get("exceptional_confidence_threshold", 0.85)
                    conf = float(self._effective_confidence(cand.signal))
                    if conf >= thresh:
                        should_execute = True
                        reason = "EXCEPTIONAL_IMMEDIATE"
                
                # Session Cutoff Execution
                if not should_execute and cutoff_reached:
                    should_execute = True
                    reason = "DAILY_BEST_SELECTED"
                    
                if should_execute:
                    acc_suffix = str(acc_id)[-3:] if acc_id else "***"
                    conf = float(self._effective_confidence(cand.signal))
                    logger.info(
                        f"EXECUTING instrument={getattr(cand.signal,'instrument','UNKNOWN')} "
                        f"score={cand.score:.1f} conf={conf:.3f} reason={reason} acc=***{acc_suffix}"
                    )
                    cand.executed = True  # Mark as executed so we don't re-emit
                    cand.executed_at = now
                    executed_this_cycle += 1
                    # Add execution metadata to signal?
                    # s.metadata['execution_reason'] = reason
                    executable_trades.append(cand.signal)
        
        # 3. Audit Logging
        self._audit_daily_rankings()
                    
        return executable_trades

    def _audit_daily_rankings(self):
        """Dump current ranking table to disk for audit"""
        try:
            ranking_data = {}
            for acc_id, candidates in self.pool.items():
                ranking_data[acc_id] = []
                for i, cand in enumerate(sorted(candidates, key=lambda c: c.score, reverse=True)):
                    ranking_data[acc_id].append({
                        "rank": i + 1,
                        "instrument": getattr(cand.signal, "instrument", "UNKNOWN"),
                        "strategy": getattr(cand.signal, "strategy_key", "unknown"),
                        "score": float(cand.score),
                        "executed": cand.executed
                    })
            
            audit_path = os.getenv("RUNTIME_PATH", "runtime") + "/daily_trade_ranking.json"
            # Ensure directory exists
            os.makedirs(os.path.dirname(audit_path), exist_ok=True)
            
            with open(audit_path, 'w') as f:
                json.dump(ranking_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to write ranking audit: {e}")

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
                side_val = self._side_value(c.signal)
                acc_suffix = str(acc)[-3:] if acc else "***"
                items.append({
                    "account_id_masked": f"***{acc_suffix}",
                    "account_suffix": acc_suffix,
                    "instrument": getattr(c.signal, "instrument", "UNKNOWN"),
                    "strategy_key": getattr(c.signal, "strategy_key", "unknown"),
                    "side": side_val,
                    "score": float(c.score),
                    "confidence": float(self._effective_confidence(c.signal)),
                    "regime": meta.get("regime", "UNKNOWN"),
                    "condition": meta.get("condition", "NORMAL"),
                    "first_seen_at": c.first_seen_at,
                    "last_seen_at": c.last_seen_at,
                    "executed": bool(c.executed),
                    "executed_at": c.executed_at,
                })

        # Sort by score desc and trim to eff_limit
        items.sort(key=lambda x: x["score"], reverse=True)
        return items[:eff_limit]
