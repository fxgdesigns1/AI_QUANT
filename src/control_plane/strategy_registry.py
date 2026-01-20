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
    "alpha": StrategyInfo(
        key="alpha",
        name="Alpha EMA Strategy",
        description="EMA crossover strategy with momentum confirmation for FX majors",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"],
        tunables={
            "ema_fast": 3,
            "ema_slow": 21,
            "sl_pct": 0.002,
        },
        risk_level="medium",
        session_preference="any"
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
    "xau_usd_session_bias_1": StrategyInfo(
        key="xau_usd_session_bias_1",
        name="Gold Scalping - Session Bias #1",
        description="XAU_USD scalping strategy optimized for session bias (fitness: 2.28, win rate: 46.7%)",
        instruments=["XAU_USD"],
        tunables={
            "stop_loss_pips": 9.5,
            "take_profit_pips": 55.0,
            "risk_reward_ratio": 5.79,
            "directional_bias": "short_only",
        },
        risk_level="high",
        session_preference="london"
    ),
    "xau_usd_session_bias_2": StrategyInfo(
        key="xau_usd_session_bias_2",
        name="Gold Scalping - Session Bias #2",
        description="XAU_USD scalping strategy with trend filter (fitness: 2.24, win rate: 50%)",
        instruments=["XAU_USD"],
        tunables={
            "stop_loss_pips": 10.3,
            "take_profit_pips": 50.0,
            "risk_reward_ratio": 4.85,
            "directional_bias": "short_only",
        },
        risk_level="high",
        session_preference="london"
    ),
    "xau_usd_session_bias_3": StrategyInfo(
        key="xau_usd_session_bias_3",
        name="Gold Scalping - Session Bias #3",
        description="XAU_USD scalping strategy - both directions (fitness: 2.10, win rate: 46.7%)",
        instruments=["XAU_USD"],
        tunables={
            "stop_loss_pips": 8.0,
            "take_profit_pips": 50.0,
            "risk_reward_ratio": 6.25,
            "directional_bias": "both",
        },
        risk_level="high",
        session_preference="london"
    ),
    "ultra_strict_forex": StrategyInfo(
        key="ultra_strict_forex",
        name="Ultra Strict Forex Optimized",
        description="Ultra strict forex strategy with maximum 10 trades per day, high quality filters",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"],
        tunables={
            "max_trades_per_day": 10,
            "min_signal_strength": 0.85,
            "stop_loss_pct": 0.004,
            "take_profit_pct": 0.020,
        },
        risk_level="medium",
        session_preference="any"
    ),
    "pat_orb_dual_session": StrategyInfo(
        key="pat_orb_dual_session",
        name="PAT ORB Dual Session",
        description="Opening Range Breakout strategy for London and NY sessions",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY"],
        tunables={
            "range_window_minutes": 15,
            "per_session_trade_cap": 2,
            "tp_multiple_of_range": 0.8,
        },
        risk_level="medium",
        session_preference="london"
    ),
    "trump_dna": StrategyInfo(
        key="trump_dna",
        name="Trump DNA Strategy",
        description="Trump DNA framework: Weekly planning, sniper entry zones, fixed tight stops, quick exits, selective trading (5-15 trades/day). Optimized for XAU_USD, EUR_USD, GBP_USD with 2-hour max hold and news awareness.",
        instruments=["XAU_USD", "EUR_USD", "GBP_USD", "USD_JPY"],
        tunables={
            "weekly_target": 2500.0,
            "max_trades_per_day": 10,
            "fixed_stop_pips": 8.0,
            "max_hold_hours": 2.0,
            "sniper_zone_tolerance": 5.0,
            "news_pause_minutes": 15,
        },
        risk_level="medium",
        session_preference="london"
    ),
    "session_execution": StrategyInfo(
        key="session_execution",
        name="Session Execution Strategy",
        description="Hybrid session execution for account 006 using Roadmap bias + EMA confirmation + regime filters",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "XAU_USD"],
        tunables={},
        risk_level="medium",
        session_preference="london"
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
