#!/usr/bin/env python3
"""
Performance Analytics Engine
World-class performance calculations for trading strategies
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from scipy import stats

logger = logging.getLogger(__name__)


class PerformanceAnalytics:
    """
    Comprehensive performance analytics calculator
    All calculations use real data - no dummy values
    """
    
    def __init__(self, db):
        """Initialize analytics engine with database connection"""
        self.db = db
        logger.info("✅ PerformanceAnalytics initialized")
    
    # ========================================================================
    # CORE RISK-ADJUSTED RETURNS
    # ========================================================================
    
    def calculate_sharpe_ratio(self, 
                               returns: List[float], 
                               risk_free_rate: float = 0.0,
                               periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe Ratio (risk-adjusted returns)
        
        Formula: (Mean Return - Risk Free Rate) / Std Deviation * sqrt(periods/year)
        
        Args:
            returns: List of period returns
            risk_free_rate: Annual risk-free rate (default 0%)
            periods_per_year: Trading periods per year (252 for daily)
        
        Returns:
            Sharpe ratio (higher is better, >1 is good, >2 is excellent)
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        
        # Calculate excess returns
        daily_rf_rate = risk_free_rate / periods_per_year
        excess_returns = returns_array - daily_rf_rate
        
        # Calculate mean and std
        mean_return = np.mean(excess_returns)
        std_return = np.std(excess_returns, ddof=1)  # Sample std
        
        if std_return == 0 or np.isnan(std_return):
            return 0.0
        
        # Annualize
        sharpe = (mean_return / std_return) * np.sqrt(periods_per_year)
        
        return float(sharpe)
    
    def calculate_sortino_ratio(self, 
                                returns: List[float], 
                                risk_free_rate: float = 0.0,
                                periods_per_year: int = 252) -> float:
        """
        Calculate Sortino Ratio (downside risk-adjusted returns)
        
        Like Sharpe but only penalizes downside volatility
        
        Args:
            returns: List of period returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Trading periods per year
        
        Returns:
            Sortino ratio (higher is better)
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        
        # Calculate excess returns
        daily_rf_rate = risk_free_rate / periods_per_year
        excess_returns = returns_array - daily_rf_rate
        
        # Calculate mean
        mean_return = np.mean(excess_returns)
        
        # Calculate downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')  # No downside = infinite Sortino
        
        downside_std = np.std(downside_returns, ddof=1)
        
        if downside_std == 0 or np.isnan(downside_std):
            return 0.0
        
        # Annualize
        sortino = (mean_return / downside_std) * np.sqrt(periods_per_year)
        
        return float(sortino)
    
    def calculate_calmar_ratio(self, 
                               returns: List[float], 
                               max_drawdown: float) -> float:
        """
        Calculate Calmar Ratio (return / max drawdown)
        
        Measures return relative to worst drawdown
        
        Args:
            returns: List of period returns
            max_drawdown: Maximum drawdown as positive decimal (e.g., 0.15 for 15%)
        
        Returns:
            Calmar ratio (higher is better, >3 is excellent)
        """
        if not returns or max_drawdown == 0:
            return 0.0
        
        # Annualized return
        total_return = np.prod([1 + r for r in returns]) - 1
        periods = len(returns)
        annual_return = (1 + total_return) ** (252 / periods) - 1
        
        # Calmar = Annual Return / Max Drawdown
        calmar = annual_return / max_drawdown
        
        return float(calmar)
    
    # ========================================================================
    # DRAWDOWN ANALYSIS
    # ========================================================================
    
    def calculate_drawdowns(self, equity_curve: List[float]) -> Dict[str, float]:
        """
        Calculate comprehensive drawdown statistics
        
        Args:
            equity_curve: List of equity values over time
        
        Returns:
            Dictionary with max_drawdown, current_drawdown, avg_drawdown, etc.
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'current_drawdown': 0.0,
                'current_drawdown_pct': 0.0,
                'avg_drawdown': 0.0,
                'drawdown_duration': 0,
                'max_drawdown_duration': 0,
                'recovery_factor': 0.0
            }
        
        equity = np.array(equity_curve)
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(equity)
        
        # Calculate drawdown at each point
        drawdown = running_max - equity
        drawdown_pct = drawdown / running_max
        
        # Max drawdown
        max_dd = np.max(drawdown)
        max_dd_pct = np.max(drawdown_pct)
        
        # Current drawdown
        current_dd = drawdown[-1]
        current_dd_pct = drawdown_pct[-1]
        
        # Average drawdown (only non-zero)
        nonzero_dd = drawdown[drawdown > 0]
        avg_dd = np.mean(nonzero_dd) if len(nonzero_dd) > 0 else 0.0
        
        # Drawdown duration (consecutive periods in drawdown)
        in_drawdown = drawdown > 0
        drawdown_duration = np.sum(in_drawdown[-20:])  # Last 20 periods
        
        # Max drawdown duration
        max_duration = 0
        current_duration = 0
        for dd in in_drawdown:
            if dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        # Recovery factor (total return / max drawdown)
        total_return = (equity[-1] - equity[0]) / equity[0] if equity[0] > 0 else 0.0
        recovery_factor = total_return / max_dd_pct if max_dd_pct > 0 else 0.0
        
        return {
            'max_drawdown': float(max_dd),
            'max_drawdown_pct': float(max_dd_pct),
            'current_drawdown': float(current_dd),
            'current_drawdown_pct': float(current_dd_pct),
            'avg_drawdown': float(avg_dd),
            'drawdown_duration': int(drawdown_duration),
            'max_drawdown_duration': int(max_duration),
            'recovery_factor': float(recovery_factor)
        }
    
    # ========================================================================
    # TRADE STATISTICS
    # ========================================================================
    
    def calculate_profit_factor(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate Profit Factor (gross profit / gross loss)
        
        Args:
            trades: List of trade dictionaries with 'net_pl' field
        
        Returns:
            Profit factor (>1 is profitable, >2 is excellent)
        """
        if not trades:
            return 0.0
        
        gross_profit = sum(t['net_pl'] for t in trades if t.get('net_pl', 0) > 0)
        gross_loss = abs(sum(t['net_pl'] for t in trades if t.get('net_pl', 0) < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def calculate_expectancy(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate trade expectancy (average $ per trade)
        
        Args:
            trades: List of trade dictionaries
        
        Returns:
            Average profit per trade
        """
        if not trades:
            return 0.0
        
        total_pl = sum(t.get('net_pl', 0) for t in trades)
        return total_pl / len(trades)
    
    def calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate win rate (% of profitable trades)
        
        Args:
            trades: List of trade dictionaries
        
        Returns:
            Win rate as percentage (0-100)
        """
        if not trades:
            return 0.0
        
        winners = sum(1 for t in trades if t.get('net_pl', 0) > 0)
        return (winners / len(trades)) * 100
    
    def calculate_consecutive_stats(self, trades: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Calculate consecutive wins/losses statistics
        
        Args:
            trades: List of trades ordered by time
        
        Returns:
            Dict with current_streak, max_win_streak, max_loss_streak
        """
        if not trades:
            return {
                'current_streak': 0,
                'current_streak_type': 'none',
                'max_win_streak': 0,
                'max_loss_streak': 0
            }
        
        current_streak = 0
        current_type = None
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in trades:
            pl = trade.get('net_pl', 0)
            
            if pl > 0:
                if current_type == 'win':
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = 'win'
                max_win_streak = max(max_win_streak, current_streak)
                
            elif pl < 0:
                if current_type == 'loss':
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = 'loss'
                max_loss_streak = max(max_loss_streak, current_streak)
            
            else:  # Break even
                current_streak = 0
                current_type = 'none'
        
        return {
            'current_streak': current_streak,
            'current_streak_type': current_type or 'none',
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak
        }
    
    # ========================================================================
    # COMPREHENSIVE METRICS CALCULATION
    # ========================================================================
    
    def calculate_comprehensive_metrics(self, 
                                       account_id: Optional[str] = None,
                                       strategy_name: Optional[str] = None,
                                       days: int = 30) -> Dict[str, Any]:
        """
        Calculate all performance metrics for an account or strategy
        
        Args:
            account_id: Filter by account
            strategy_name: Filter by strategy
            days: Number of days to analyze
        
        Returns:
            Comprehensive metrics dictionary
        """
        try:
            # Get trades
            start_date = datetime.now() - timedelta(days=days)
            trades = self.db.get_trades(
                account_id=account_id,
                strategy_name=strategy_name,
                start_date=start_date,
                status='closed'
            )
            
            if not trades:
                return self._empty_metrics()
            
            # Get equity curve
            equity_curve = []
            if account_id:
                equity_data = self.db.get_equity_curve(account_id, days)
                equity_curve = [eq for _, eq in equity_data]
            
            # Calculate daily returns
            daily_returns = self.db.get_daily_returns(
                strategy_name=strategy_name,
                account_id=account_id,
                days=days
            )
            
            # Basic trade statistics
            winning_trades = [t for t in trades if t.get('net_pl', 0) > 0]
            losing_trades = [t for t in trades if t.get('net_pl', 0) < 0]
            break_even = [t for t in trades if t.get('net_pl', 0) == 0]
            
            gross_profit = sum(t['net_pl'] for t in winning_trades)
            gross_loss = abs(sum(t['net_pl'] for t in losing_trades))
            net_profit = gross_profit - gross_loss
            
            # Risk metrics
            sharpe = self.calculate_sharpe_ratio(daily_returns) if daily_returns else 0.0
            sortino = self.calculate_sortino_ratio(daily_returns) if daily_returns else 0.0
            
            drawdown_stats = {}
            if equity_curve:
                drawdown_stats = self.calculate_drawdowns(equity_curve)
            
            calmar = 0.0
            if drawdown_stats.get('max_drawdown_pct', 0) > 0:
                calmar = self.calculate_calmar_ratio(daily_returns, drawdown_stats['max_drawdown_pct'])
            
            # Consecutive statistics
            consecutive = self.calculate_consecutive_stats(trades)
            
            # Duration metrics
            durations = [t.get('duration_seconds', 0) for t in trades if t.get('duration_seconds')]
            avg_duration = np.mean(durations) if durations else 0.0
            
            # Market condition performance
            trending_trades = [t for t in trades if t.get('market_regime') == 'trending']
            ranging_trades = [t for t in trades if t.get('market_regime') == 'ranging']
            volatile_trades = [t for t in trades if t.get('market_regime') == 'volatile']
            
            trending_wr = self.calculate_win_rate(trending_trades) if trending_trades else 0.0
            ranging_wr = self.calculate_win_rate(ranging_trades) if ranging_trades else 0.0
            volatile_wr = self.calculate_win_rate(volatile_trades) if volatile_trades else 0.0
            
            # Compile comprehensive metrics
            metrics = {
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'break_even_trades': len(break_even),
                'win_rate': self.calculate_win_rate(trades),
                
                # P&L
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'net_profit': net_profit,
                'profit_factor': self.calculate_profit_factor(trades),
                'expectancy': self.calculate_expectancy(trades),
                'avg_win': gross_profit / len(winning_trades) if winning_trades else 0.0,
                'avg_loss': gross_loss / len(losing_trades) if losing_trades else 0.0,
                'largest_win': max((t['net_pl'] for t in winning_trades), default=0.0),
                'largest_loss': min((t['net_pl'] for t in losing_trades), default=0.0),
                
                # Risk metrics
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'calmar_ratio': calmar,
                **drawdown_stats,
                
                # Duration
                'avg_trade_duration': avg_duration,
                'avg_bars_held': np.mean([t.get('bars_held', 0) for t in trades if t.get('bars_held')]) or 0.0,
                'trades_per_day': len(trades) / days if days > 0 else 0.0,
                
                # R-multiple
                'avg_r_multiple': np.mean([t.get('r_multiple', 0) for t in trades if t.get('r_multiple')]) or 0.0,
                
                # Consecutive
                **consecutive,
                
                # Market conditions
                'trending_win_rate': trending_wr,
                'ranging_win_rate': ranging_wr,
                'volatile_win_rate': volatile_wr,
                
                # Time-based
                'best_day': max(daily_returns) if daily_returns else 0.0,
                'worst_day': min(daily_returns) if daily_returns else 0.0,
                'avg_daily_return': np.mean(daily_returns) if daily_returns else 0.0,
                'volatility': np.std(daily_returns, ddof=1) if len(daily_returns) > 1 else 0.0,
                
                # Metadata
                'period_days': days,
                'calculated_at': datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate metrics: {e}")
            return self._empty_metrics()
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'win_rate': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'net_profit': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'max_drawdown': 0.0,
            'calculated_at': datetime.now().isoformat()
        }


