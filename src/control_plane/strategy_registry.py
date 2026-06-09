"""Strategy registry - static registry of available strategies

NO DYNAMIC CODE LOADING - security first
Maps strategy keys to metadata for UI
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class StrategyInfo:
    """Strategy metadata for UI"""
    key: str
    name: str
    description: str
    instruments: List[str]  # Preferred instruments
    tunables: Dict[str, Any]  # Editable parameters (for future use)
    risk_level: str  # low|medium|high
    session_preference: str  # any|london|ny|asia


# Static strategy registry
STRATEGIES: Dict[str, StrategyInfo] = {
    "momentum": StrategyInfo(
        key="momentum",
        name="Momentum Trading",
        description="Trend-following strategy using momentum indicators (RSI, MACD, moving averages)",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"],
        tunables={
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "use_macd": True,
        },
        risk_level="medium",
        session_preference="any"
    ),
    "gold": StrategyInfo(
        key="gold",
        name="Gold Scalping",
        description="Scalping strategy optimized for XAU_USD with tight stops and quick exits",
        instruments=["XAU_USD"],
        tunables={
            "scalp_pip_target": 5,
            "stop_loss_pips": 3,
            "use_volume_filter": True,
        },
        risk_level="high",
        session_preference="london"
    ),
    "range": StrategyInfo(
        key="range",
        name="Range Trading",
        description="Mean-reversion strategy for sideways markets",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY"],
        tunables={
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "range_breakout_filter": True,
        },
        risk_level="low",
        session_preference="asia"
    ),
    "eur_usd_5m_safe": StrategyInfo(
        key="eur_usd_5m_safe",
        name="EUR/USD 5M Safe",
        description="Conservative EUR/USD strategy on 5-minute timeframe with strict risk controls",
        instruments=["EUR_USD"],
        tunables={
            "min_pip_distance": 10,
            "max_spread_pips": 2,
        },
        risk_level="low",
        session_preference="london"
    ),
    "momentum_v2": StrategyInfo(
        key="momentum_v2",
        name="Momentum V2 (Enhanced)",
        description="Enhanced momentum strategy with adaptive filters and volatility adjustment",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "XAU_USD"],
        tunables={
            "adaptive_rsi": True,
            "volatility_filter": True,
            "min_trend_strength": 0.6,
        },
        risk_level="medium",
        session_preference="any"
    ),
    "mean_rev_v2": StrategyInfo(
        key="mean_rev_v2",
        name="Mean Reversion V2",
        description="Enhanced mean reversion strategy with adaptive Bollinger Bands and volatility filters",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY"],
        tunables={
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adaptive_filter": True,
            "volatility_threshold": 0.5,
            "min_range_width": 10,
        },
        risk_level="low",
        session_preference="asia"
    ),
}


def get_strategy_registry() -> Dict[str, StrategyInfo]:
    """Get full strategy registry for API"""
    return STRATEGIES.copy()


def get_strategy_info(key: str) -> StrategyInfo | None:
    """Get info for specific strategy"""
    return STRATEGIES.get(key)


def validate_strategy_key(key: str) -> bool:
    """Check if strategy key is valid"""
    return key in STRATEGIES
