#!/usr/bin/env python3
"""
Optimization loader utilities.

Loads per-pair optimized parameters from optimization_results.json and
applies them to strategy instances at runtime.
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_optimization_results(path: str = 'optimization_results.json') -> Dict[str, Any]:
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        logger.info("✅ Loaded optimization_results.json")
        return data
    except FileNotFoundError:
        logger.warning("⚠️ optimization_results.json not found; using defaults")
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to load optimization results: {e}")
        return {}

def apply_per_pair_to_momentum(strategy, results: Dict[str, Any]) -> None:
    """Apply per-pair params to MomentumTradingStrategy if available."""
    try:
        per_pair = results.get('Momentum', {})
        mapping = {}
        for instrument, cfg in per_pair.items():
            if not cfg:
                continue
            mapping[instrument] = {
                'min_momentum': float(cfg.get('min_momentum', strategy.min_momentum)),
                'stop_loss_atr': float(cfg.get('sl_atr', strategy.stop_loss_atr)),
                'take_profit_atr': float(cfg.get('tp_atr', strategy.take_profit_atr)),
            }
        if hasattr(strategy, 'set_per_instrument_overrides'):
            strategy.set_per_instrument_overrides(mapping)
            logger.info(f"✅ Applied momentum per-pair overrides for {len(mapping)} instruments")
    except Exception as e:
        logger.error(f"❌ Failed to apply momentum per-pair overrides: {e}")

def apply_per_pair_to_ultra_strict(strategy, results: Dict[str, Any]) -> None:
    """Apply per-pair params to UltraStrictForexStrategy if available."""
    try:
        per_pair = results.get('UltraStrictForex', {})
        mapping = {}
        for instrument, cfg in per_pair.items():
            if not cfg:
                continue
            mapping[instrument] = {
                'min_signal_strength': float(cfg.get('min_signal_strength', strategy.min_signal_strength if hasattr(strategy, 'min_signal_strength') else 0.5))
            }
        if hasattr(strategy, 'set_per_instrument_overrides'):
            strategy.set_per_instrument_overrides(mapping)
            logger.info(f"✅ Applied ultra-strict per-pair overrides for {len(mapping)} instruments")
    except Exception as e:
        logger.error(f"❌ Failed to apply ultra-strict per-pair overrides: {e}")

def apply_per_pair_to_gold(strategy, results: Dict[str, Any]) -> None:
    """Apply per-pair params to GoldScalpingStrategy if available (XAU_USD)."""
    try:
        gold = results.get('Gold', {}).get('XAU_USD')
        if not gold:
            return
        mapping = {
            'XAU_USD': {
                # Gold strategy primarily uses pips; keep pips but we may in future map ATR → pips heuristically
                'min_signal_strength': float(getattr(strategy, 'min_signal_strength', 0.5))
            }
        }
        if hasattr(strategy, 'set_per_instrument_overrides'):
            strategy.set_per_instrument_overrides(mapping)
            logger.info("✅ Applied gold per-pair overrides for XAU_USD")
    except Exception as e:
        logger.error(f"❌ Failed to apply gold per-pair overrides: {e}")


