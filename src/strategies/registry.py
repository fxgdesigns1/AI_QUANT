#!/usr/bin/env python3
"""
Central strategy registry.

Exposes a single source of truth for strategy factories and metadata so that
account managers, dashboards, and orchestration layers stay in sync.
"""

from __future__ import annotations

import sys
import os

# Ensure 'src' is importable by adding project root to sys.path
_REGISTRY_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_REGISTRY_DIR, "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import importlib
import logging
import os
_CANONICAL_CONFIG_PATH = os.environ.get("TRADE_CANONICAL_CONFIG_PATH")
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Any

logger = logging.getLogger(__name__)


class MockStrategy:
    def __init__(self, name: str):
        self.name = name
        print(f"MockStrategy '{self.name}' created. This strategy cannot be used.")

    def __getattr__(self, item):
        raise RuntimeError(f"Attempted to access '{item}' on unavailable strategy '{self.name}'.")


def _optional_import(module_name: str, import_callable: Callable) -> Any:
    """Lazily imports a module or returns a mock if import fails."""
    # If a canonical path is configured, enforce single source of truth
    if _CANONICAL_CONFIG_PATH:
        print(f"Info: Enforcing canonical strategy path at {_CANONICAL_CONFIG_PATH}")
        return lambda: MockStrategy(_CANONICAL_CONFIG_PATH)
    try:
        return import_callable()
    except ImportError as e:
        print(f"Warning: Could not import strategy module {module_name}. Error: {e}")
        # Return a factory that will create a MockStrategy when invoked. This
        # preserves the expected 'callable factory' contract for strategy
        # definitions so registry entries remain callable even when modules are
        # missing.
        return lambda: MockStrategy(module_name)


get_ultra_strict_forex_strategy = _optional_import(
    "ultra_strict_forex",
    lambda: __import__("src.strategies.ultra_strict_forex", fromlist=["get_ultra_strict_forex_strategy"]).get_ultra_strict_forex_strategy,
)

get_gold_scalping_strategy = _optional_import(
    "gold_scalping",
    lambda: __import__("src.strategies.gold_scalping", fromlist=["get_gold_scalping_strategy"]).get_gold_scalping_strategy,
)

# Gold Scalping variants (uncomment and wire as available)
get_gold_scalping_winrate_strategy = _optional_import(
    "gold_scalping_winrate",
    lambda: __import__("src.strategies.gold_scalping_winrate", fromlist=["get_gold_scalping_winrate_strategy"]).get_gold_scalping_winrate_strategy,
)

get_gold_scalping_strict1_strategy = _optional_import(
    "gold_scalping_strict1",
    lambda: __import__("src.strategies.gold_scalping_strict1", fromlist=["get_gold_scalping_strict1_strategy"]).get_gold_scalping_strict1_strategy,
)

get_gold_scalping_topdown_strategy = _optional_import(
    "gold_scalping_topdown",
    lambda: __import__("src.strategies.gold_scalping_topdown", fromlist=["get_gold_scalping_topdown_strategy"]).get_gold_scalping_topdown_strategy,
)

get_momentum_trading_strategy = _optional_import(
    "momentum_trading",
    lambda: __import__("src.strategies.momentum_trading", fromlist=["get_momentum_trading_strategy"]).get_momentum_trading_strategy,
)

get_alpha_strategy = _optional_import(
    "alpha",
    lambda: __import__("src.strategies.alpha", fromlist=["get_alpha_strategy"]).get_alpha_strategy,
)

# get_pattern_discovery_v11_strategy = _optional_import(
#     "pattern_discovery_v11",
#     lambda: __import__("src.strategies.pattern_discovery_v11", fromlist=["get_pattern_discovery_v11_strategy"]).get_pattern_discovery_v11_strategy,
# )

# def _import_gbp_rank(rank: str) -> Callable[[], object]:
#     module = __import__("src.strategies.gbp_usd_optimized", fromlist=["get_strategy_rank_1", "get_strategy_rank_2", "get_strategy_rank_3"])
#     return getattr(module, f"get_strategy_rank_{rank}")


# get_strategy_rank_1 = _optional_import("gbp_rank_1", lambda: _import_gbp_rank("1"))
# get_strategy_rank_2 = _optional_import("gbp_rank_2", lambda: _import_gbp_rank("2"))
# get_strategy_rank_3 = _optional_import("gbp_rank_3", lambda: _import_gbp_rank("3"))

# get_all_weather_70wr_strategy = _optional_import(
#     "all_weather_70wr",
#     lambda: __import__("src.strategies.all_weather_70wr", fromlist=["get_all_weather_70wr_strategy"]).get_all_weather_70wr_strategy,
# )

get_dynamic_multi_pair_unified_strategy = _optional_import(
    "dynamic_multi_pair_unified",
    lambda: __import__("src.strategies.dynamic_multi_pair_unified", fromlist=["get_dynamic_multi_pair_unified_strategy"]).get_dynamic_multi_pair_unified_strategy,
)

get_trade_with_pat_orb_dual_strategy = _optional_import(
    "trade_with_pat_orb_dual",
    lambda: __import__("src.strategies.trade_with_pat_orb_dual", fromlist=["get_trade_with_pat_orb_dual_strategy"]).get_trade_with_pat_orb_dual_strategy,
)

# get_optimized_multi_pair_live_strategy = _optional_import(
#     "optimized_multi_pair_live",
#     lambda: __import__("src.strategies.optimized_multi_pair_live", fromlist=["get_optimized_multi_pair_live_strategy"]).get_optimized_multi_pair_live_strategy,
# )

get_eur_calendar_optimized_strategy = _optional_import(
    "eur_calendar_optimized",
    lambda: __import__("src.strategies.eur_calendar_optimized", fromlist=["get_eur_calendar_optimized_strategy"]).get_eur_calendar_optimized_strategy,
)


@dataclass(frozen=True)
class StrategyDefinition:
    """Metadata and factory for an executable trading strategy."""

    key: str
    display_name: str
    factory: Callable[[], object]
    description: str = ""

    def create(self) -> object:
        """Instantiate a fresh strategy instance."""
        instance = self.factory()
        # Backwards-compatibility shim:
        # If a strategy implements analyze_market but not generate_signals,
        # expose a generate_signals wrapper that delegates to analyze_market.
        # This allows older strategies to be treated as 'signal-capable'
        # without modifying their original source.
        try:
            if not hasattr(instance, "generate_signals") and hasattr(instance, "analyze_market"):
                def _generate_signals_wrapper(*args, **kwargs):
                    try:
                        res = instance.analyze_market(*args, **kwargs)
                        return res or []
                    except Exception as _e:
                        logger.exception("generate_signals wrapper failed")
                        return []
                setattr(instance, "generate_signals", _generate_signals_wrapper)
        except Exception:
            # Non-fatal: return instance even if shim failed
            pass
        return instance


# Canonical registry keyed by normalized identifiers
STRATEGY_REGISTRY: Dict[str, StrategyDefinition] = {
    "ultra_strict_forex": StrategyDefinition(
        key="ultra_strict_forex",
        display_name="Ultra Strict Forex",
        factory=get_ultra_strict_forex_strategy,
        description="High-precision FX swing strategy with strict entry filters.",
    ),
    "gold_scalping": StrategyDefinition(
        key="gold_scalping",
        display_name="Gold Scalping",
        factory=get_gold_scalping_strategy,
        description="XAU/USD scalping framework tuned for London/NY overlap.",
    ),
    "gold_scalping_winrate": StrategyDefinition(
        key="gold_scalping_winrate",
        display_name="Gold Scalper (Winrate)",
        factory=get_gold_scalping_winrate_strategy,
        description="Gold scalper profile emphasizing maximum win-rate and tighter filters.",
    ),
    "gold_scalping_strict1": StrategyDefinition(
        key="gold_scalping_strict1",
        display_name="Gold Scalper (Strict1)",
        factory=get_gold_scalping_strict1_strategy,
        description="Gold scalper strict profile with conservative entries and risk.",
    ),
    "gold_scalping_topdown": StrategyDefinition(
        key="gold_scalping_topdown",
        display_name="Gold Scalper (Topdown)",
        factory=get_gold_scalping_topdown_strategy,
        description="Gold scalper top-down profile aligning higher timeframe bias with entries.",
    ),
    "momentum_trading": StrategyDefinition(
        key="momentum_trading",
        display_name="Momentum Trading",
        factory=get_momentum_trading_strategy,
        description="Multi-instrument momentum engine with adaptive risk."
    ),
    "alpha": StrategyDefinition(
        key="alpha",
        display_name="Alpha EMA Momentum",
        factory=get_alpha_strategy,
        description="EMA(3/8/21) crossover with momentum confirmation.",
    ),
    "dynamic_multi_pair_unified": StrategyDefinition(
        key="dynamic_multi_pair_unified",
        display_name="Dynamic Multi-Pair Unified",
        factory=get_dynamic_multi_pair_unified_strategy,
        description="Monte Carlo optimized multi-pair strategy."
    ),
    "eur_calendar_optimized": StrategyDefinition(
        key="eur_calendar_optimized",
        display_name="EUR Calendar Optimized",
        factory=get_eur_calendar_optimized_strategy,
        description="EUR Calendar optimized strategy with calendar integration."
    ),
    "trade_with_pat_orb_dual": StrategyDefinition(
        key="trade_with_pat_orb_dual",
        display_name="Trade With Pat ORB (Dual)",
        factory=get_trade_with_pat_orb_dual_strategy,
        description="Open range breakout with dual-session setup."
    ),
}

# Synonyms map legacy names to canonical registry keys
_STRATEGY_SYNONYMS: Dict[str, str] = {
    "ultra_strict": "ultra_strict_forex",
    "ultra_forex": "ultra_strict_forex",
    "multi_strategy_portfolio": "ultra_strict_forex",  # legacy config alias
    "gold_scalp": "gold_scalping",
    "gold_scalping": "gold_scalping",
    "gold_scalping_5m": "gold_scalping",
    "gold_scalping_winrate": "gold_scalping_winrate",
    "gold_winrate": "gold_scalping_winrate",
    "gold_scalper_winrate": "gold_scalping_winrate",
    "gold_scalping_strict1": "gold_scalping_strict1",
    "gold_strict1": "gold_scalping_strict1",
    "gold_scalper_strict1": "gold_scalping_strict1",
    "gold_scalping_topdown": "gold_scalping_topdown",
    "gold_topdown": "gold_scalping_topdown",
    "gold_scalper_topdown": "gold_scalping_topdown",
    "momentum": "momentum_trading",
    "adaptive_momentum": "momentum_trading",
    "momentum_alpha": "momentum_trading",
    "alpha_momentum": "alpha",
    "alpha_strategy": "alpha",
    "dynamic_multi_pair_unified": "dynamic_multi_pair_unified",
    "dynamic_multi_pair": "dynamic_multi_pair_unified",
    "multi_pair_unified": "dynamic_multi_pair_unified",
    "trade_with_pat": "trade_with_pat_orb_dual",
    "trade_with_pat_orb": "trade_with_pat_orb_dual",
    "orb_dual": "trade_with_pat_orb_dual",
    "orb_strategy": "trade_with_pat_orb_dual",
    "ny_orb": "trade_with_pat_orb_dual",
    "eur_calendar_optimized": "eur_calendar_optimized",
    "eur_calendar": "eur_calendar_optimized",
    "eur_optimized_v2": "eur_calendar_optimized",
    "champion_75wr_eur": "eur_calendar_optimized",
    "optimized_multi_pair_live": "optimized_multi_pair_live",
}


def _normalize_key(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = raw.strip().lower()
    if key in STRATEGY_REGISTRY:
        return key
    return _STRATEGY_SYNONYMS.get(key)


def resolve_strategy_key(raw: Optional[str]) -> Optional[str]:
    """Resolve a raw identifier (env/YAML/UI) to a canonical registry key."""
    return _normalize_key(raw)


def get_strategy_definition(raw: Optional[str]) -> Optional[StrategyDefinition]:
    """Return the StrategyDefinition for the requested identifier."""
    key = resolve_strategy_key(raw)
    if not key:
        return None
    return STRATEGY_REGISTRY.get(key)


def create_strategy(raw: Optional[str]) -> Optional[object]:
    """Instantiate a strategy using a raw identifier."""
    definition = get_strategy_definition(raw)
    return definition.create() if definition else None


def available_strategies() -> Iterable[StrategyDefinition]:
    """Iterate over all registered strategy definitions."""
    return STRATEGY_REGISTRY.values()
