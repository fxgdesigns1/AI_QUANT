"""Policy Store - Read-only policy lookup for session/regime alignment

FAIL-CLOSED: If policy not found, returns None (blocks trading).
NO DEFAULTS that allow trading.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class TradingPolicy:
    """Trading policy for a specific session/regime combination"""
    participation_score: float  # 0.0-1.0, threshold is 0.6
    max_position_size_multiplier: float
    allowed_instruments: list[str]
    notes: str


class PolicyStore:
    """Read-only policy store - fail-closed design"""
    
    def __init__(self):
        # In-memory policy cache
        # Format: (session, regime, news_state, bias_alignment) -> Policy
        self._policies: Dict[tuple, TradingPolicy] = {}
        self._initialized = False
        
    def _initialize_defaults(self):
        """Initialize with conservative defaults (fail-closed)"""
        if self._initialized:
            return
            
        # Conservative policies - most combinations are blocked by default
        # Only explicitly safe combinations are allowed
        
        # London session + TRENDING + normal news + aligned -> HIGH PARTICIPATION
        self._policies[("london", "TRENDING", "normal", "aligned")] = TradingPolicy(
            participation_score=0.85,
            max_position_size_multiplier=1.0,
            allowed_instruments=["EUR_USD", "GBP_USD", "USD_JPY"],
            notes="High participation: London trending aligned"
        )
        
        # London-NY overlap + TRENDING + normal news + aligned -> HIGH PARTICIPATION
        self._policies[("london_ny_overlap", "TRENDING", "normal", "aligned")] = TradingPolicy(
            participation_score=0.90,
            max_position_size_multiplier=1.0,
            allowed_instruments=["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"],
            notes="Highest participation: Overlap trending aligned"
        )
        
        # NY session + TRENDING + normal news + aligned -> MEDIUM-HIGH PARTICIPATION
        self._policies[("new_york", "TRENDING", "normal", "aligned")] = TradingPolicy(
            participation_score=0.75,
            max_position_size_multiplier=1.0,
            allowed_instruments=["EUR_USD", "USD_JPY", "XAU_USD"],
            notes="Medium-high participation: NY trending aligned"
        )
        
        # RANGING regimes get lower scores
        self._policies[("london", "RANGING", "normal", "aligned")] = TradingPolicy(
            participation_score=0.55,  # Below threshold (0.6) - blocks trading
            max_position_size_multiplier=0.8,
            allowed_instruments=["EUR_USD", "GBP_USD"],
            notes="Ranging market - below threshold"
        )
        
        # CHOPPY regimes are blocked (implicitly via None)
        # No policy = None = blocked
        
        self._initialized = True
        logger.info(f"PolicyStore initialized with {len(self._policies)} policies")
    
    def lookup(
        self,
        session: str,
        regime: str,
        news_state: str,
        bias_alignment: str,
    ) -> Optional[TradingPolicy]:
        """Look up policy - returns None if not found (fail-closed)
        
        Args:
            session: Session name (asia, london, london_ny_overlap, new_york, transition)
            regime: Market regime (TRENDING, RANGING, CHOPPY, UNKNOWN)
            news_state: News state (normal, elevated, embargo)
            bias_alignment: Bias alignment status (aligned, misaligned)
            
        Returns:
            TradingPolicy if found, None otherwise (blocks trading)
        """
        if not self._initialized:
            self._initialize_defaults()
        
        # Normalize inputs
        session = session.lower()
        regime = regime.upper()
        news_state = news_state.lower()
        bias_alignment = bias_alignment.lower()
        
        key = (session, regime, news_state, bias_alignment)
        policy = self._policies.get(key)
        
        if policy is None:
            logger.debug(
                f"PolicyStore: No policy found for session={session} regime={regime} "
                f"news={news_state} alignment={bias_alignment} - BLOCKED"
            )
        
        return policy
    
    def reload_from_file(self, file_path: str) -> None:
        """
        Reload policies from JSON file (manual-call only).
        
        NO auto-reload at runtime. Must be explicitly called.
        Format expected: {"policies": {key: {participation_score, enabled, ...}, ...}}
        
        Args:
            file_path: Path to JSON policy file
        """
        from pathlib import Path
        import json
        
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Policy file not found: {file_path}")
            return
        
        try:
            data = json.loads(path.read_text())
            policies_data = data.get("policies", {})
            
            # Clear existing policies
            self._policies.clear()
            
            # Load policies from file
            for key_str, policy_data in policies_data.items():
                # Parse key: "session|regime|news_state|bias_alignment"
                parts = key_str.split("|")
                if len(parts) == 4:
                    session, regime, news_state, bias_alignment = parts
                    key = (session.lower(), regime.upper(), news_state.lower(), bias_alignment.lower())
                    
                    participation_score = float(policy_data.get("participation_score", 0.0))
                    enabled = bool(policy_data.get("enabled", False))
                    
                    # Only add enabled policies (fail-closed)
                    if enabled and participation_score >= 0.6:
                        self._policies[key] = TradingPolicy(
                            participation_score=participation_score,
                            max_position_size_multiplier=float(policy_data.get("max_position_size_multiplier", 1.0)),
                            allowed_instruments=list(policy_data.get("allowed_instruments", [])),
                            notes=str(policy_data.get("notes", "Loaded from file")),
                        )
            
            logger.info(f"PolicyStore: Reloaded {len(self._policies)} policies from {file_path}")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Error reloading policies from {file_path}: {e}")
            # Fail-closed: if reload fails, policies remain in current state
            # (either defaults or previous loaded state)


# Singleton instance
_policy_store: Optional[PolicyStore] = None


def get_policy_store() -> PolicyStore:
    """Get singleton PolicyStore instance"""
    global _policy_store
    if _policy_store is None:
        _policy_store = PolicyStore()
    return _policy_store
