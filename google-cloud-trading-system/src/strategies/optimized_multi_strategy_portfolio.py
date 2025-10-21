"""
OPTIMIZED MULTI-STRATEGY PORTFOLIO
Combines all 3 strategy groups with shared data feeds for maximum efficiency
50% API reduction vs individual strategies, 95% vs REST polling
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from .group_1_5m_high_frequency import get_group_1_strategy, get_group_1_performance_targets
    from .group_2_15m_zero_drawdown import get_group_2_strategy, get_group_2_performance_targets
    from .group_3_high_win_rate import get_group_3_strategy, get_group_3_performance_targets
except ImportError:
    from group_1_5m_high_frequency import get_group_1_strategy, get_group_1_performance_targets
    from group_2_15m_zero_drawdown import get_group_2_strategy, get_group_2_performance_targets
    from group_3_high_win_rate import get_group_3_strategy, get_group_3_performance_targets

logger = logging.getLogger(__name__)

@dataclass
class OptimizedMultiStrategyPortfolio:
    """Optimized Multi-Strategy Portfolio with 50% API reduction"""
    
    # Portfolio identification
    portfolio_name: str = "optimized_multi_strategy_portfolio"
    portfolio_description: str = "3-group portfolio with shared data feeds and 50% API reduction"
    
    # Strategy groups
    groups: Dict[str, Any] = None
    
    # Combined performance targets
    total_strategies: int = 6
    total_instruments: int = 6  # GBP_USD, NZD_USD, XAU_USD, EUR_JPY, USD_CAD (XAU_USD appears twice)
    unique_instruments: List[str] = None
    
    # Risk management
    total_risk_per_trade: float = 200.0  # Fixed risk across all groups
    max_total_concurrent_positions: int = 9  # 3 per group
    max_total_daily_trades: int = 350  # Combined limit
    
    # API optimization
    api_streams: int = 3  # One per group (vs 6 individual)
    api_reduction_pct: float = 50.0  # 50% reduction vs individual strategies
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = {
                "group_1": get_group_1_strategy(),
                "group_2": get_group_2_strategy(),
                "group_3": get_group_3_strategy()
            }
        
        if self.unique_instruments is None:
            all_instruments = []
            for group in self.groups.values():
                all_instruments.extend(group.instruments)
            self.unique_instruments = list(set(all_instruments))  # Remove duplicates

def get_optimized_multi_strategy_portfolio() -> OptimizedMultiStrategyPortfolio:
    """Get the complete optimized multi-strategy portfolio"""
    
    portfolio = OptimizedMultiStrategyPortfolio()
    
    logger.info("✅ Optimized Multi-Strategy Portfolio initialized")
    logger.info(f"📊 Total Strategies: {portfolio.total_strategies}")
    logger.info(f"📊 Unique Instruments: {portfolio.unique_instruments}")
    logger.info(f"📊 API Streams: {portfolio.api_streams} (vs {portfolio.total_strategies} individual)")
    logger.info(f"📊 API Reduction: {portfolio.api_reduction_pct}%")
    logger.info(f"📊 Max Concurrent Positions: {portfolio.max_total_concurrent_positions}")
    logger.info(f"📊 Max Daily Trades: {portfolio.max_total_daily_trades}")
    
    # Log each group
    for group_name, group in portfolio.groups.items():
        logger.info(f"📊 {group_name}: {group.instruments} ({group.timeframe})")
    
    return portfolio

def get_portfolio_performance_targets() -> Dict[str, Any]:
    """Get combined performance targets for the entire portfolio"""
    
    portfolio = get_optimized_multi_strategy_portfolio()
    
    # Get individual group targets
    group_1_targets = get_group_1_performance_targets()
    group_2_targets = get_group_2_performance_targets()
    group_3_targets = get_group_3_performance_targets()
    
    # Calculate combined targets (weighted by weekly wins)
    total_weekly_wins = (
        group_1_targets["targets"]["weekly_wins"] +
        group_2_targets["targets"]["weekly_wins"] +
        group_3_targets["targets"]["weekly_wins"]
    )
    
    combined_sharpe = (
        (group_1_targets["targets"]["sharpe_ratio"] * group_1_targets["targets"]["weekly_wins"] +
         group_2_targets["targets"]["sharpe_ratio"] * group_2_targets["targets"]["weekly_wins"] +
         group_3_targets["targets"]["sharpe_ratio"] * group_3_targets["targets"]["weekly_wins"]) /
        total_weekly_wins
    )
    
    combined_win_rate = (
        (group_1_targets["targets"]["win_rate_pct"] * group_1_targets["targets"]["weekly_wins"] +
         group_2_targets["targets"]["win_rate_pct"] * group_2_targets["targets"]["weekly_wins"] +
         group_3_targets["targets"]["win_rate_pct"] * group_3_targets["targets"]["weekly_wins"]) /
        total_weekly_wins
    )
    
    combined_annual_return = (
        (group_1_targets["targets"]["annual_return_pct"] * group_1_targets["targets"]["weekly_wins"] +
         group_2_targets["targets"]["annual_return_pct"] * group_2_targets["targets"]["weekly_wins"] +
         group_3_targets["targets"]["annual_return_pct"] * group_3_targets["targets"]["weekly_wins"]) /
        total_weekly_wins
    )
    
    combined_max_drawdown = max(
        group_1_targets["targets"]["max_drawdown_pct"],
        group_2_targets["targets"]["max_drawdown_pct"],
        group_3_targets["targets"]["max_drawdown_pct"]
    )
    
    return {
        "portfolio_name": portfolio.portfolio_name,
        "total_strategies": portfolio.total_strategies,
        "unique_instruments": portfolio.unique_instruments,
        "api_optimization": {
            "api_streams": portfolio.api_streams,
            "api_reduction_pct": portfolio.api_reduction_pct,
            "individual_strategies": portfolio.total_strategies,
            "optimization_ratio": f"{portfolio.api_reduction_pct}% reduction"
        },
        "combined_targets": {
            "sharpe_ratio": round(combined_sharpe, 2),
            "win_rate_pct": round(combined_win_rate, 1),
            "annual_return_pct": round(combined_annual_return, 1),
            "weekly_wins": total_weekly_wins,
            "max_drawdown_pct": combined_max_drawdown
        },
        "risk_management": {
            "risk_per_trade": portfolio.total_risk_per_trade,
            "max_concurrent_positions": portfolio.max_total_concurrent_positions,
            "max_daily_trades": portfolio.max_total_daily_trades,
            "position_allocation": "Equal across all groups"
        },
        "strategy_groups": {
            "group_1": group_1_targets,
            "group_2": group_2_targets,
            "group_3": group_3_targets
        }
    }

def analyze_portfolio_signal(instrument: str, market_data: Any) -> Optional[Dict[str, Any]]:
    """Analyze signal for any strategy in the portfolio"""
    
    portfolio = get_optimized_multi_strategy_portfolio()
    
    # Check each group for the instrument
    for group_name, group in portfolio.groups.items():
        if instrument in group.instruments:
            if group_name == "group_1":
                from .group_1_5m_high_frequency import analyze_group_1_signal
                return analyze_group_1_signal(instrument, market_data, group)
            elif group_name == "group_2":
                from .group_2_15m_zero_drawdown import analyze_group_2_signal
                return analyze_group_2_signal(instrument, market_data, group)
            elif group_name == "group_3":
                from .group_3_high_win_rate import analyze_group_3_signal
                return analyze_group_3_signal(instrument, market_data, group)
    
    return None

def get_portfolio_status() -> Dict[str, Any]:
    """Get current portfolio status and statistics"""
    
    portfolio = get_optimized_multi_strategy_portfolio()
    targets = get_portfolio_performance_targets()
    
    return {
        "portfolio_name": portfolio.portfolio_name,
        "status": "initialized",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "total_strategies": portfolio.total_strategies,
            "unique_instruments": portfolio.unique_instruments,
            "api_streams": portfolio.api_streams,
            "api_reduction_pct": portfolio.api_reduction_pct
        },
        "performance_targets": targets["combined_targets"],
        "risk_management": targets["risk_management"],
        "strategy_groups": {
            group_name: {
                "instruments": group.instruments,
                "timeframe": group.timeframe,
                "target_sharpe": group.target_sharpe,
                "target_win_rate": group.target_win_rate
            }
            for group_name, group in portfolio.groups.items()
        }
    }

if __name__ == "__main__":
    # Test the portfolio configuration
    portfolio = get_optimized_multi_strategy_portfolio()
    targets = get_portfolio_performance_targets()
    status = get_portfolio_status()
    
    print("Optimized Multi-Strategy Portfolio Configuration:")
    print(f"- Total Strategies: {portfolio.total_strategies}")
    print(f"- Unique Instruments: {portfolio.unique_instruments}")
    print(f"- API Streams: {portfolio.api_streams} (vs {portfolio.total_strategies} individual)")
    print(f"- API Reduction: {portfolio.api_reduction_pct}%")
    print(f"- Combined Sharpe: {targets['combined_targets']['sharpe_ratio']}")
    print(f"- Combined Win Rate: {targets['combined_targets']['win_rate_pct']}%")
    print(f"- Combined Annual Return: {targets['combined_targets']['annual_return_pct']}%")
    print(f"- Expected Weekly Wins: {targets['combined_targets']['weekly_wins']}")
    print(f"- Max Drawdown: {targets['combined_targets']['max_drawdown_pct']}%")
    
    print("\nStrategy Groups:")
    for group_name, group in portfolio.groups.items():
        print(f"- {group_name}: {group.instruments} ({group.timeframe})")
