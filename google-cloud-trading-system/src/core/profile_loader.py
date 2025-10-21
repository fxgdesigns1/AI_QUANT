"""
Profile Loader

Loads modular strategy/risk/scheduling profiles from JSON and applies them
to live strategy instances without hard-coding thresholds. Profiles enable
safe, reversible, session-specific tuning.
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class Profile:
    name: str
    description: str
    strategies: Dict[str, Dict[str, Any]]
    risk: Dict[str, Any]
    guardrails: Dict[str, Any]
    schedule: Dict[str, Any]


def load_profile(profile_path: str) -> Optional[Profile]:
    try:
        with open(profile_path, "r") as f:
            cfg = json.load(f)
        prof = Profile(
            name=cfg.get("name", "Unnamed"),
            description=cfg.get("description", ""),
            strategies=cfg.get("strategies", {}),
            risk=cfg.get("risk", {}),
            guardrails=cfg.get("guardrails", {}),
            schedule=cfg.get("schedule", {}),
        )
        logger.info(f"✅ Loaded profile: {prof.name}")
        return prof
    except FileNotFoundError:
        logger.error(f"❌ Profile not found: {profile_path}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to load profile {profile_path}: {e}")
        return None


def _apply_ultra_strict(cfg: Dict[str, Any], strategy: Any):
    # Thresholds
    if "min_signal_strength" in cfg:
        strategy.min_signal_strength = float(cfg["min_signal_strength"])
    # Trade caps
    if "max_trades_per_day" in cfg:
        strategy.max_trades_per_day = int(cfg["max_trades_per_day"])


def _apply_momentum(cfg: Dict[str, Any], strategy: Any):
    if "min_adx" in cfg:
        strategy.min_adx = float(cfg["min_adx"])
    if "min_momentum" in cfg:
        strategy.min_momentum = float(cfg["min_momentum"])
    if "min_volume" in cfg:
        strategy.min_volume = float(cfg["min_volume"])
    if "max_trades_per_day" in cfg:
        strategy.max_trades_per_day = int(cfg["max_trades_per_day"])


def _apply_gold(cfg: Dict[str, Any], strategy: Any):
    if "min_signal_strength" in cfg:
        strategy.min_signal_strength = float(cfg["min_signal_strength"])
    if "max_spread" in cfg:
        strategy.max_spread = float(cfg["max_spread"])
    if "min_volatility" in cfg:
        strategy.min_volatility = float(cfg["min_volatility"])
    if "max_trades_per_day" in cfg:
        strategy.max_trades_per_day = int(cfg["max_trades_per_day"])


def apply_profile_to_strategies(profile: Profile, strategies: Dict[str, Any]):
    """Apply a loaded Profile object to instantiated strategies.

    strategies: mapping of human-readable names to instances, e.g.:
      {
        'Ultra Strict Forex': ultra_strict_instance,
        'Momentum Trading': momentum_instance,
        'Gold Scalping': gold_instance,
      }
    """
    if not profile:
        logger.warning("⚠️ No profile to apply")
        return

    strat_cfg = profile.strategies or {}

    for name, strat in strategies.items():
        cfg = strat_cfg.get(name) or {}
        if not cfg:
            logger.info(f"ℹ️ Profile has no overrides for {name}; using current settings")
            continue
        try:
            if "Ultra Strict" in name:
                _apply_ultra_strict(cfg, strat)
            elif "Momentum" in name:
                _apply_momentum(cfg, strat)
            elif "Gold" in name:
                _apply_gold(cfg, strat)
            else:
                logger.info(f"ℹ️ Unknown strategy name for profile mapping: {name}")
            logger.info(f"✅ Applied profile overrides to {name}: {cfg}")
        except Exception as e:
            logger.error(f"❌ Failed applying profile to {name}: {e}")


def profile_summary(profile: Profile) -> str:
    if not profile:
        return "No profile loaded"
    parts = [
        f"Profile: {profile.name}",
        profile.description,
        f"Strategies: {list(profile.strategies.keys())}",
        f"Risk: {profile.risk}",
        f"Guardrails: {profile.guardrails}",
        f"Schedule: {profile.schedule}",
    ]
    return " | ".join(parts)


