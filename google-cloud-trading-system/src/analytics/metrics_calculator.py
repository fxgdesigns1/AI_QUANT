#!/usr/bin/env python3
"""
Metrics Calculator - Comprehensive Trading Metrics
Calculates all standard and advanced trading performance metrics
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate comprehensive trading metrics from trade data"""
    
    def __init__(self):
        """Initialize metrics calculator"""
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 60  # Cache for 60 seconds
        logger.info("✅ Metrics calculator initialized")
    
    def calculate_all_metrics(self, trades: List[Dict[str, Any]], 
                             strategy_id: str = None) -> Dict[str, Any]:
        """
        Calculate all metrics for a list of trades
        
        Args:
            trades: List of trade dictionaries (must include closed trades)
            strategy_id: Optional strategy ID for caching
            
        Returns:
            Dictionary with all calculated metrics
        """
        # Check cache
        if strategy_id:
            cache_key = f"{strategy_id}_{len(trades)}"
            cached = self._get_cached_metrics(cache_key)
            if cached:
                return cached
        
        # Filter to closed trades only
        closed_trades = [t for t in trades if t.get('is_closed') == 1]
        
        if not closed_trades:
            return self._empty_metrics()
        
        # Calculate all metrics
        metrics = {}
        
        # Basic metrics
        metrics.update(self._calculate_basic_metrics(closed_trades))
        
        # Win/Loss analysis
        metrics.update(self._calculate_win_loss_metrics(closed_trades))
        
        # Risk metrics
        metrics.update(self._calculate_risk_metrics(closed_trades))
        
        # Time-based analysis
        metrics.update(self._calculate_time_metrics(closed_trades))
        
        # Advanced ratios
        metrics.update(self._calculate_advanced_ratios(closed_trades, metrics))
        
        # Streak analysis
        metrics.update(self._calculate_streak_metrics(closed_trades))
        
        # Session analysis
        metrics.update(self._calculate_session_metrics(closed_trades))
        
        # Drawdown analysis
        metrics.update(self._calculate_drawdown_metrics(closed_trades))
        
        # Cache results
        if strategy_id:
            self._cache_metrics(cache_key, metrics)
        
        return metrics
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': None,
            'sortino_ratio': None,
            'calmar_ratio': None,
            'max_drawdown': 0.0,
            'avg_trade_duration_seconds': 0,
        }
    
    def _calculate_basic_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic trade statistics"""
        total_trades = len(trades)
        wins = [t for t in trades if t.get('realized_pnl', 0) > 0]
        losses = [t for t in trades if t.get('realized_pnl', 0) <= 0]
        
        total_pnl = sum(t.get('realized_pnl', 0) for t in trades)
        
        return {
            'total_trades': total_trades,
            'closed_trades': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': (len(wins) / total_trades * 100) if total_trades > 0 else 0.0,
            'total_pnl': total_pnl,
        }
    
    def _calculate_win_loss_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate win/loss analysis metrics"""
        wins = [t.get('realized_pnl', 0) for t in trades if t.get('realized_pnl', 0) > 0]
        losses = [t.get('realized_pnl', 0) for t in trades if t.get('realized_pnl', 0) <= 0]
        
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = abs(np.mean(losses)) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = abs(min(losses)) if losses else 0.0
        
        # Profit factor = total wins / total losses
        total_wins = sum(wins) if wins else 0.0
        total_losses = abs(sum(losses)) if losses else 0.0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0.0
        
        return {
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'total_wins_sum': total_wins,
            'total_losses_sum': total_losses,
            'profit_factor': profit_factor,
        }
    
    def _calculate_risk_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk-adjusted metrics"""
        # Risk/Reward ratio (actual)
        risk_reward_ratios = []
        for t in trades:
            if t.get('stop_loss') and t.get('take_profit'):
                entry = t.get('entry_price', 0)
                sl = t.get('stop_loss', 0)
                tp = t.get('take_profit', 0)
                
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                
                if risk > 0:
                    risk_reward_ratios.append(reward / risk)
        
        avg_rr_ratio = np.mean(risk_reward_ratios) if risk_reward_ratios else 0.0
        
        # Slippage analysis
        slippages = [t.get('execution_slippage', 0) for t in trades]
        avg_slippage = np.mean(slippages) if slippages else 0.0
        
        # Commission analysis
        commissions = [t.get('commission', 0) for t in trades]
        total_commission = sum(commissions)
        
        return {
            'risk_reward_ratio': avg_rr_ratio,
            'avg_slippage': avg_slippage,
            'total_commission': total_commission,
        }
    
    def _calculate_time_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time-based metrics"""
        durations = [t.get('trade_duration_seconds', 0) for t in trades 
                    if t.get('trade_duration_seconds')]
        
        avg_duration = int(np.mean(durations)) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # Calculate PnL by hour of day
        hourly_pnl = defaultdict(list)
        for t in trades:
            if t.get('entry_time'):
                try:
                    entry_dt = datetime.fromisoformat(t['entry_time'])
                    hour = entry_dt.hour
                    hourly_pnl[hour].append(t.get('realized_pnl', 0))
                except:
                    pass
        
        best_hour = None
        worst_hour = None
        if hourly_pnl:
            hour_avg = {h: np.mean(pnls) for h, pnls in hourly_pnl.items()}
            best_hour = max(hour_avg.items(), key=lambda x: x[1])[0]
            worst_hour = min(hour_avg.items(), key=lambda x: x[1])[0]
        
        # Calculate PnL by day of week
        daily_pnl = defaultdict(list)
        for t in trades:
            if t.get('entry_time'):
                try:
                    entry_dt = datetime.fromisoformat(t['entry_time'])
                    day = entry_dt.strftime('%A')
                    daily_pnl[day].append(t.get('realized_pnl', 0))
                except:
                    pass
        
        return {
            'avg_trade_duration_seconds': avg_duration,
            'min_trade_duration_seconds': min_duration,
            'max_trade_duration_seconds': max_duration,
            'best_hour': best_hour,
            'worst_hour': worst_hour,
            'hourly_performance': dict(hourly_pnl),
            'daily_performance': dict(daily_pnl),
        }
    
    def _calculate_advanced_ratios(self, trades: List[Dict[str, Any]], 
                                  basic_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate advanced performance ratios"""
        pnls = [t.get('realized_pnl', 0) for t in trades]
        
        if not pnls or len(pnls) < 2:
            return {
                'sharpe_ratio': None,
                'sortino_ratio': None,
                'calmar_ratio': None,
                'recovery_factor': None,
            }
        
        # Sharpe Ratio (assuming risk-free rate = 0)
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls)
        sharpe_ratio = (mean_pnl / std_pnl) if std_pnl > 0 else None
        
        # Sortino Ratio (downside deviation only)
        negative_pnls = [p for p in pnls if p < 0]
        downside_std = np.std(negative_pnls) if negative_pnls else std_pnl
        sortino_ratio = (mean_pnl / downside_std) if downside_std > 0 else None
        
        # Calmar Ratio = Annual Return / Max Drawdown
        max_dd = basic_metrics.get('max_drawdown', 0)
        total_pnl = basic_metrics.get('total_pnl', 0)
        calmar_ratio = (total_pnl / abs(max_dd)) if max_dd != 0 else None
        
        # Recovery Factor = Net Profit / Max Drawdown
        recovery_factor = (total_pnl / abs(max_dd)) if max_dd != 0 else None
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'recovery_factor': recovery_factor,
        }
    
    def _calculate_streak_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consecutive win/loss streaks"""
        # Sort by exit time
        sorted_trades = sorted(trades, key=lambda t: t.get('exit_time', ''))
        
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for t in sorted_trades:
            pnl = t.get('realized_pnl', 0)
            
            if pnl > 0:
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        return {
            'consecutive_wins': current_win_streak,
            'consecutive_losses': current_loss_streak,
            'max_consecutive_wins': max_win_streak,
            'max_consecutive_losses': max_loss_streak,
        }
    
    def _calculate_session_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance by trading session"""
        london_pnl = []
        ny_pnl = []
        asian_pnl = []
        
        for t in trades:
            if t.get('entry_time'):
                try:
                    entry_dt = datetime.fromisoformat(t['entry_time'])
                    hour = entry_dt.hour
                    pnl = t.get('realized_pnl', 0)
                    
                    # London: 8-16 (GMT)
                    if 8 <= hour < 16:
                        london_pnl.append(pnl)
                    # NY: 13-21 (GMT)
                    elif 13 <= hour < 21:
                        ny_pnl.append(pnl)
                    # Asian: 22-8 (GMT)
                    else:
                        asian_pnl.append(pnl)
                except:
                    pass
        
        return {
            'london_session_pnl': sum(london_pnl),
            'london_session_trades': len(london_pnl),
            'london_session_win_rate': (len([p for p in london_pnl if p > 0]) / len(london_pnl) * 100) if london_pnl else 0,
            'ny_session_pnl': sum(ny_pnl),
            'ny_session_trades': len(ny_pnl),
            'ny_session_win_rate': (len([p for p in ny_pnl if p > 0]) / len(ny_pnl) * 100) if ny_pnl else 0,
            'asian_session_pnl': sum(asian_pnl),
            'asian_session_trades': len(asian_pnl),
            'asian_session_win_rate': (len([p for p in asian_pnl if p > 0]) / len(asian_pnl) * 100) if asian_pnl else 0,
        }
    
    def _calculate_drawdown_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate drawdown analysis"""
        # Sort by exit time
        sorted_trades = sorted(trades, key=lambda t: t.get('exit_time', ''))
        
        # Calculate equity curve
        equity_curve = [0]
        for t in sorted_trades:
            equity_curve.append(equity_curve[-1] + t.get('realized_pnl', 0))
        
        # Calculate drawdowns
        peak = equity_curve[0]
        max_drawdown = 0
        current_drawdown = 0
        drawdowns = []
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
                current_drawdown = 0
            else:
                current_drawdown = equity - peak
                drawdowns.append(current_drawdown)
                max_drawdown = min(max_drawdown, current_drawdown)
        
        avg_drawdown = np.mean(drawdowns) if drawdowns else 0.0
        
        return {
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown,
            'avg_drawdown': avg_drawdown,
            'equity_curve': equity_curve,
        }
    
    def calculate_daily_breakdown(self, trades: List[Dict[str, Any]], 
                                  days: int = 30) -> Dict[str, Dict[str, Any]]:
        """Calculate daily performance breakdown"""
        daily_data = defaultdict(list)
        
        for t in trades:
            if t.get('entry_time') and t.get('is_closed') == 1:
                try:
                    entry_dt = datetime.fromisoformat(t['entry_time'])
                    date_key = entry_dt.strftime('%Y-%m-%d')
                    daily_data[date_key].append(t)
                except:
                    pass
        
        daily_metrics = {}
        for date, day_trades in daily_data.items():
            daily_metrics[date] = self.calculate_all_metrics(day_trades)
        
        return daily_metrics
    
    def calculate_weekly_breakdown(self, trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Calculate weekly performance breakdown"""
        weekly_data = defaultdict(list)
        
        for t in trades:
            if t.get('entry_time') and t.get('is_closed') == 1:
                try:
                    entry_dt = datetime.fromisoformat(t['entry_time'])
                    week_key = entry_dt.strftime('%Y-W%W')
                    weekly_data[week_key].append(t)
                except:
                    pass
        
        weekly_metrics = {}
        for week, week_trades in weekly_data.items():
            weekly_metrics[week] = self.calculate_all_metrics(week_trades)
        
        return weekly_metrics
    
    def calculate_monthly_breakdown(self, trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Calculate monthly performance breakdown"""
        monthly_data = defaultdict(list)
        
        for t in trades:
            if t.get('entry_time') and t.get('is_closed') == 1:
                try:
                    entry_dt = datetime.fromisoformat(t['entry_time'])
                    month_key = entry_dt.strftime('%Y-%m')
                    monthly_data[month_key].append(t)
                except:
                    pass
        
        monthly_metrics = {}
        for month, month_trades in monthly_data.items():
            monthly_metrics[month] = self.calculate_all_metrics(month_trades)
        
        return monthly_metrics
    
    def compare_strategies(self, strategy1_trades: List[Dict[str, Any]], 
                          strategy2_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare metrics between two strategies"""
        metrics1 = self.calculate_all_metrics(strategy1_trades, None)
        metrics2 = self.calculate_all_metrics(strategy2_trades, None)
        
        comparison = {
            'strategy1': metrics1,
            'strategy2': metrics2,
            'differences': {}
        }
        
        # Calculate differences for key metrics
        for key in ['win_rate', 'total_pnl', 'profit_factor', 'sharpe_ratio', 'max_drawdown']:
            val1 = metrics1.get(key, 0) or 0
            val2 = metrics2.get(key, 0) or 0
            comparison['differences'][key] = val1 - val2
        
        return comparison
    
    def _get_cached_metrics(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get metrics from cache if still valid"""
        with self._cache_lock:
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self._cache_ttl:
                    return cached_data
        return None
    
    def _cache_metrics(self, cache_key: str, metrics: Dict[str, Any]):
        """Cache metrics with timestamp"""
        with self._cache_lock:
            self._cache[cache_key] = (metrics, datetime.now())
    
    def clear_cache(self):
        """Clear metrics cache"""
        with self._cache_lock:
            self._cache.clear()
            logger.info("✅ Metrics cache cleared")


# Singleton instance
_metrics_calculator_instance = None
_metrics_calculator_lock = threading.Lock()


def get_metrics_calculator() -> MetricsCalculator:
    """Get singleton metrics calculator instance"""
    global _metrics_calculator_instance
    
    if _metrics_calculator_instance is None:
        with _metrics_calculator_lock:
            if _metrics_calculator_instance is None:
                _metrics_calculator_instance = MetricsCalculator()
    
    return _metrics_calculator_instance



