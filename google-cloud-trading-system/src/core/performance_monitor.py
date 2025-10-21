#!/usr/bin/env python3
"""
Multi-Strategy Testing Framework - Performance Monitor
Real-time performance monitoring and comparison tools with comprehensive analytics
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd

from .strategy_manager import get_strategy_manager
from .strategy_executor import get_multi_strategy_executor
from .data_collector import get_data_collector
from .backtesting_integration import get_backtesting_integration
from .telegram_notifier import TelegramNotifier

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class PerformanceMetric(Enum):
    """Performance metrics to monitor"""
    RETURN = "return"
    DRAWDOWN = "drawdown"
    SHARPE_RATIO = "sharpe_ratio"
    WIN_RATE = "win_rate"
    TRADE_COUNT = "trade_count"
    MARGIN_USAGE = "margin_usage"
    RISK_EXPOSURE = "risk_exposure"

@dataclass
class PerformanceAlert:
    """Performance alert configuration"""
    metric: PerformanceMetric
    threshold: float
    comparison: str  # 'above', 'below', 'equals'
    alert_level: AlertLevel
    message: str
    enabled: bool = True

@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time"""
    timestamp: datetime
    strategy_id: str
    account_id: str
    balance: float
    unrealized_pl: float
    realized_pl: float
    total_pnl: float
    daily_return: float
    monthly_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    margin_used: float
    margin_available: float
    open_positions: int

@dataclass
class StrategyComparison:
    """Strategy performance comparison"""
    timestamp: datetime
    strategy_id: str
    strategy_name: str
    monthly_return: float
    total_pnl: float
    win_rate: float
    total_trades: int
    rank: int
    performance_score: float
    risk_score: float

class PerformanceMonitor:
    """Real-time performance monitoring and comparison system"""
    
    def __init__(self):
        """Initialize performance monitor"""
        self.strategy_manager = get_strategy_manager()
        self.multi_executor = get_multi_strategy_executor()
        self.data_collector = get_data_collector()
        self.backtesting_integration = get_backtesting_integration()
        self.telegram_notifier = TelegramNotifier()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_thread = None
        self.update_interval = 30  # seconds
        
        # Performance data storage
        self.performance_snapshots: Dict[str, List[PerformanceSnapshot]] = {}
        self.strategy_comparisons: List[StrategyComparison] = []
        self.performance_alerts: List[PerformanceAlert] = []
        
        # Historical data for calculations
        self.equity_curves: Dict[str, List[Dict]] = {}
        self.trade_history: Dict[str, List[Dict]] = {}
        
        # Alert thresholds
        self._setup_default_alerts()
        
        logger.info("📊 Performance Monitor initialized")
    
    def _setup_default_alerts(self):
        """Setup default performance alerts"""
        self.performance_alerts = [
            PerformanceAlert(
                metric=PerformanceMetric.DRAWDOWN,
                threshold=5.0,  # 5% drawdown
                comparison='above',
                alert_level=AlertLevel.WARNING,
                message="Strategy drawdown exceeds 5%",
                enabled=True
            ),
            PerformanceAlert(
                metric=PerformanceMetric.MARGIN_USAGE,
                threshold=80.0,  # 80% margin usage
                comparison='above',
                alert_level=AlertLevel.WARNING,
                message="Margin usage exceeds 80%",
                enabled=True
            ),
            PerformanceAlert(
                metric=PerformanceMetric.DRAWDOWN,
                threshold=10.0,  # 10% drawdown
                comparison='above',
                alert_level=AlertLevel.CRITICAL,
                message="Critical drawdown exceeds 10%",
                enabled=True
            ),
            PerformanceAlert(
                metric=PerformanceMetric.RETURN,
                threshold=5.0,  # 5% monthly return
                comparison='above',
                alert_level=AlertLevel.INFO,
                message="Strategy achieving excellent returns",
                enabled=True
            )
        ]
    
    def start_monitoring(self):
        """Start real-time performance monitoring"""
        if self.is_monitoring:
            logger.warning("Performance monitoring already running")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info("🚀 Performance monitoring started")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_message(
                "📊 Performance Monitoring Started\n"
                f"🔍 Monitoring {len(self.performance_alerts)} alert conditions\n"
                f"⏱️ Update interval: {self.update_interval} seconds\n"
                "📈 Real-time performance tracking active"
            )
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("🛑 Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect performance snapshots
                self._collect_performance_snapshots()
                
                # Update strategy comparisons
                self._update_strategy_comparisons()
                
                # Check performance alerts
                self._check_performance_alerts()
                
                # Update equity curves
                self._update_equity_curves()
                
                # Sleep for update interval
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in performance monitoring loop: {e}")
                time.sleep(60)
    
    def _collect_performance_snapshots(self):
        """Collect performance snapshots for all strategies"""
        try:
            # Get execution status from all executors
            execution_status = self.multi_executor.get_all_execution_status()
            
            for strategy_id, executor_data in execution_status.get('executors', {}).items():
                # Get account information
                account_id = executor_data.get('account_id', '')
                account_info = self.strategy_manager.account_manager.get_account_info(account_id)
                
                if not account_info:
                    continue
                
                # Calculate performance metrics
                performance_metrics = self._calculate_performance_metrics(
                    strategy_id, account_info
                )
                
                # Create performance snapshot
                snapshot = PerformanceSnapshot(
                    timestamp=datetime.now(),
                    strategy_id=strategy_id,
                    account_id=account_id,
                    balance=account_info.balance,
                    unrealized_pl=account_info.unrealized_pl,
                    realized_pl=account_info.realized_pl,
                    total_pnl=account_info.unrealized_pl + account_info.realized_pl,
                    daily_return=performance_metrics.get('daily_return', 0.0),
                    monthly_return=performance_metrics.get('monthly_return', 0.0),
                    max_drawdown=performance_metrics.get('max_drawdown', 0.0),
                    sharpe_ratio=performance_metrics.get('sharpe_ratio', 0.0),
                    win_rate=performance_metrics.get('win_rate', 0.0),
                    total_trades=performance_metrics.get('total_trades', 0),
                    margin_used=account_info.margin_used,
                    margin_available=account_info.margin_available,
                    open_positions=account_info.open_position_count
                )
                
                # Store snapshot
                if strategy_id not in self.performance_snapshots:
                    self.performance_snapshots[strategy_id] = []
                
                self.performance_snapshots[strategy_id].append(snapshot)
                
                # Keep only last 100 snapshots per strategy
                if len(self.performance_snapshots[strategy_id]) > 100:
                    self.performance_snapshots[strategy_id] = self.performance_snapshots[strategy_id][-100:]
                
        except Exception as e:
            logger.error(f"❌ Failed to collect performance snapshots: {e}")
    
    def _calculate_performance_metrics(self, strategy_id: str, account_info) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        try:
            metrics = {}
            
            # Calculate returns
            total_pnl = account_info.unrealized_pl + account_info.realized_pl
            daily_return = 0.0  # Calculate based on previous day
            monthly_return = (total_pnl / account_info.balance * 100) if account_info.balance > 0 else 0.0
            
            metrics['daily_return'] = daily_return
            metrics['monthly_return'] = monthly_return
            
            # Calculate max drawdown
            if strategy_id in self.equity_curves:
                metrics['max_drawdown'] = self._calculate_max_drawdown(self.equity_curves[strategy_id])
            else:
                metrics['max_drawdown'] = 0.0
            
            # Calculate Sharpe ratio (simplified)
            if strategy_id in self.trade_history:
                returns = [trade.get('pnl', 0) for trade in self.trade_history[strategy_id]]
                if returns:
                    mean_return = np.mean(returns)
                    std_return = np.std(returns)
                    metrics['sharpe_ratio'] = mean_return / std_return if std_return > 0 else 0.0
                else:
                    metrics['sharpe_ratio'] = 0.0
            else:
                metrics['sharpe_ratio'] = 0.0
            
            # Calculate win rate
            if strategy_id in self.trade_history:
                trades = self.trade_history[strategy_id]
                winning_trades = [trade for trade in trades if trade.get('pnl', 0) > 0]
                metrics['win_rate'] = (len(winning_trades) / len(trades)) * 100 if trades else 0.0
                metrics['total_trades'] = len(trades)
            else:
                metrics['win_rate'] = 0.0
                metrics['total_trades'] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate performance metrics for {strategy_id}: {e}")
            return {}
    
    def _update_strategy_comparisons(self):
        """Update strategy performance comparisons"""
        try:
            current_comparisons = []
            
            # Get performance comparison from strategy manager
            performance_comparison = self.strategy_manager.get_strategy_performance_comparison()
            
            if performance_comparison and 'strategies' in performance_comparison:
                strategies_data = performance_comparison['strategies']
                
                # Rank strategies by monthly return
                ranked_strategies = sorted(
                    strategies_data.items(),
                    key=lambda x: x[1].get('monthly_return', 0),
                    reverse=True
                )
                
                for rank, (strategy_id, data) in enumerate(ranked_strategies, 1):
                    # Calculate performance and risk scores
                    performance_score = self._calculate_performance_score(data)
                    risk_score = self._calculate_risk_score(data)
                    
                    comparison = StrategyComparison(
                        timestamp=datetime.now(),
                        strategy_id=strategy_id,
                        strategy_name=data.get('name', strategy_id),
                        monthly_return=data.get('monthly_return', 0.0),
                        total_pnl=data.get('total_pnl', 0.0),
                        win_rate=data.get('win_rate', 0.0),
                        total_trades=data.get('total_trades', 0),
                        rank=rank,
                        performance_score=performance_score,
                        risk_score=risk_score
                    )
                    
                    current_comparisons.append(comparison)
            
            # Update comparisons list
            self.strategy_comparisons = current_comparisons
            
            # Keep only last 50 comparisons
            if len(self.strategy_comparisons) > 50:
                self.strategy_comparisons = self.strategy_comparisons[-50:]
                
        except Exception as e:
            logger.error(f"❌ Failed to update strategy comparisons: {e}")
    
    def _calculate_performance_score(self, strategy_data: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        try:
            monthly_return = strategy_data.get('monthly_return', 0.0)
            win_rate = strategy_data.get('win_rate', 0.0)
            total_trades = strategy_data.get('total_trades', 0)
            
            # Weighted scoring system
            return_score = min(monthly_return * 10, 50)  # Max 50 points for returns
            winrate_score = min(win_rate * 0.5, 30)      # Max 30 points for win rate
            activity_score = min(total_trades * 0.1, 20)  # Max 20 points for activity
            
            total_score = return_score + winrate_score + activity_score
            return min(max(total_score, 0), 100)  # Clamp between 0-100
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate performance score: {e}")
            return 0.0
    
    def _calculate_risk_score(self, strategy_data: Dict[str, Any]) -> float:
        """Calculate risk score (0-100, lower is better)"""
        try:
            # Risk factors (simplified)
            monthly_return = strategy_data.get('monthly_return', 0.0)
            total_trades = strategy_data.get('total_trades', 0)
            
            # Calculate risk score based on volatility and activity
            volatility_risk = min(abs(monthly_return) * 2, 50)  # Higher returns = higher risk
            activity_risk = min(total_trades * 0.05, 30)        # More trades = higher risk
            
            total_risk = volatility_risk + activity_risk
            return min(max(total_risk, 0), 100)  # Clamp between 0-100
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate risk score: {e}")
            return 50.0  # Default medium risk
    
    def _check_performance_alerts(self):
        """Check performance alerts and send notifications"""
        try:
            for alert in self.performance_alerts:
                if not alert.enabled:
                    continue
                
                # Get current metric value
                current_value = self._get_current_metric_value(alert.metric)
                
                if current_value is None:
                    continue
                
                # Check alert condition
                alert_triggered = False
                
                if alert.comparison == 'above' and current_value > alert.threshold:
                    alert_triggered = True
                elif alert.comparison == 'below' and current_value < alert.threshold:
                    alert_triggered = True
                elif alert.comparison == 'equals' and current_value == alert.threshold:
                    alert_triggered = True
                
                if alert_triggered:
                    self._send_performance_alert(alert, current_value)
                    
        except Exception as e:
            logger.error(f"❌ Failed to check performance alerts: {e}")
    
    def _get_current_metric_value(self, metric: PerformanceMetric) -> Optional[float]:
        """Get current value for a specific metric"""
        try:
            # Get latest performance snapshots
            latest_snapshots = {}
            for strategy_id, snapshots in self.performance_snapshots.items():
                if snapshots:
                    latest_snapshots[strategy_id] = snapshots[-1]
            
            if not latest_snapshots:
                return None
            
            # Calculate metric based on type
            if metric == PerformanceMetric.RETURN:
                # Use best performing strategy's monthly return
                returns = [snapshot.monthly_return for snapshot in latest_snapshots.values()]
                return max(returns) if returns else 0.0
            
            elif metric == PerformanceMetric.DRAWDOWN:
                # Use worst drawdown across all strategies
                drawdowns = [snapshot.max_drawdown for snapshot in latest_snapshots.values()]
                return max(drawdowns) if drawdowns else 0.0
            
            elif metric == PerformanceMetric.MARGIN_USAGE:
                # Use highest margin usage
                margin_usage = []
                for snapshot in latest_snapshots.values():
                    if snapshot.balance > 0:
                        usage = (snapshot.margin_used / snapshot.balance) * 100
                        margin_usage.append(usage)
                return max(margin_usage) if margin_usage else 0.0
            
            elif metric == PerformanceMetric.WIN_RATE:
                # Use average win rate
                win_rates = [snapshot.win_rate for snapshot in latest_snapshots.values()]
                return np.mean(win_rates) if win_rates else 0.0
            
            elif metric == PerformanceMetric.TRADE_COUNT:
                # Use total trades across all strategies
                total_trades = sum(snapshot.total_trades for snapshot in latest_snapshots.values())
                return total_trades
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get metric value for {metric}: {e}")
            return None
    
    def _send_performance_alert(self, alert: PerformanceAlert, current_value: float):
        """Send performance alert notification"""
        try:
            # Create alert message
            alert_emoji = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.CRITICAL: "🚨",
                AlertLevel.EMERGENCY: "🆘"
            }.get(alert.alert_level, "📊")
            
            message = f"{alert_emoji} Performance Alert\n\n"
            message += f"📊 Metric: {alert.metric.value.replace('_', ' ').title()}\n"
            message += f"📈 Current Value: {current_value:.2f}\n"
            message += f"🎯 Threshold: {alert.threshold:.2f}\n"
            message += f"📝 {alert.message}\n"
            message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
            
            # Send notification
            if self.telegram_notifier:
                self.telegram_notifier.send_message(message)
            
            logger.warning(f"📊 Performance alert triggered: {alert.message}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send performance alert: {e}")
    
    def _update_equity_curves(self):
        """Update equity curves for drawdown calculations"""
        try:
            # Get latest snapshots
            for strategy_id, snapshots in self.performance_snapshots.items():
                if not snapshots:
                    continue
                
                latest_snapshot = snapshots[-1]
                
                # Update equity curve
                if strategy_id not in self.equity_curves:
                    self.equity_curves[strategy_id] = []
                
                equity_point = {
                    'timestamp': latest_snapshot.timestamp,
                    'equity': latest_snapshot.balance + latest_snapshot.unrealized_pl,
                    'balance': latest_snapshot.balance
                }
                
                self.equity_curves[strategy_id].append(equity_point)
                
                # Keep only last 1000 points
                if len(self.equity_curves[strategy_id]) > 1000:
                    self.equity_curves[strategy_id] = self.equity_curves[strategy_id][-1000:]
                
        except Exception as e:
            logger.error(f"❌ Failed to update equity curves: {e}")
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> float:
        """Calculate maximum drawdown from equity curve"""
        try:
            if not equity_curve:
                return 0.0
            
            peak = equity_curve[0]['equity']
            max_dd = 0.0
            
            for point in equity_curve:
                if point['equity'] > peak:
                    peak = point['equity']
                
                drawdown = (peak - point['equity']) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
            
            return max_dd * 100  # Convert to percentage
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate max drawdown: {e}")
            return 0.0
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        try:
            # Get latest comparisons
            latest_comparisons = self.strategy_comparisons[-5:] if self.strategy_comparisons else []
            
            # Get latest snapshots
            latest_snapshots = {}
            for strategy_id, snapshots in self.performance_snapshots.items():
                if snapshots:
                    latest_snapshots[strategy_id] = snapshots[-1]
            
            # Calculate summary statistics
            total_pnl = sum(snapshot.total_pnl for snapshot in latest_snapshots.values())
            total_balance = sum(snapshot.balance for snapshot in latest_snapshots.values())
            avg_return = np.mean([snapshot.monthly_return for snapshot in latest_snapshots.values()]) if latest_snapshots else 0.0
            max_drawdown = max([snapshot.max_drawdown for snapshot in latest_snapshots.values()]) if latest_snapshots else 0.0
            
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_pnl': total_pnl,
                    'total_balance': total_balance,
                    'avg_monthly_return': avg_return,
                    'max_drawdown': max_drawdown,
                    'active_strategies': len(latest_snapshots),
                    'total_trades': sum(snapshot.total_trades for snapshot in latest_snapshots.values())
                },
                'strategy_rankings': [
                    {
                        'rank': comp.rank,
                        'strategy_id': comp.strategy_id,
                        'strategy_name': comp.strategy_name,
                        'monthly_return': comp.monthly_return,
                        'total_pnl': comp.total_pnl,
                        'win_rate': comp.win_rate,
                        'performance_score': comp.performance_score,
                        'risk_score': comp.risk_score
                    }
                    for comp in latest_comparisons
                ],
                'latest_snapshots': {
                    strategy_id: {
                        'timestamp': snapshot.timestamp.isoformat(),
                        'balance': snapshot.balance,
                        'total_pnl': snapshot.total_pnl,
                        'monthly_return': snapshot.monthly_return,
                        'max_drawdown': snapshot.max_drawdown,
                        'win_rate': snapshot.win_rate,
                        'open_positions': snapshot.open_positions,
                        'margin_usage': (snapshot.margin_used / snapshot.balance * 100) if snapshot.balance > 0 else 0
                    }
                    for strategy_id, snapshot in latest_snapshots.items()
                },
                'alerts': {
                    'total_alerts': len(self.performance_alerts),
                    'active_alerts': len([alert for alert in self.performance_alerts if alert.enabled]),
                    'recent_alerts': []  # Could be populated with recent alert history
                },
                'monitoring_status': {
                    'is_monitoring': self.is_monitoring,
                    'update_interval': self.update_interval,
                    'last_update': datetime.now().isoformat()
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance dashboard data: {e}")
            return {}
    
    def export_performance_report(self, days: int = 7) -> str:
        """Export comprehensive performance report"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"performance_report_{days}days_{timestamp}.json"
            
            # Collect performance data for specified period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            report_data = {
                'report_info': {
                    'period_days': days,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'generated_at': datetime.now().isoformat()
                },
                'performance_summary': self.get_performance_dashboard_data(),
                'strategy_comparisons': [
                    asdict(comp) for comp in self.strategy_comparisons
                ],
                'performance_snapshots': {
                    strategy_id: [
                        asdict(snapshot) for snapshot in snapshots
                        if start_date <= snapshot.timestamp <= end_date
                    ]
                    for strategy_id, snapshots in self.performance_snapshots.items()
                },
                'equity_curves': {
                    strategy_id: [
                        point for point in curve
                        if start_date <= datetime.fromisoformat(point['timestamp']) <= end_date
                    ]
                    for strategy_id, curve in self.equity_curves.items()
                },
                'alert_history': [
                    asdict(alert) for alert in self.performance_alerts
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"📊 Performance report exported: {filename}")
            
            # Send notification
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    f"📊 Performance Report Generated\n"
                    f"📅 Period: {days} days\n"
                    f"📁 File: {filename}\n"
                    f"📈 Comprehensive performance analysis complete"
                )
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to export performance report: {e}")
            return ""
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get performance monitoring status"""
        try:
            return {
                'is_monitoring': self.is_monitoring,
                'update_interval': self.update_interval,
                'total_strategies_monitored': len(self.performance_snapshots),
                'total_snapshots': sum(len(snapshots) for snapshots in self.performance_snapshots.values()),
                'total_comparisons': len(self.strategy_comparisons),
                'active_alerts': len(self.performance_alerts),
                'equity_curves_tracked': len(self.equity_curves),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get monitoring status: {e}")
            return {}

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    return performance_monitor

