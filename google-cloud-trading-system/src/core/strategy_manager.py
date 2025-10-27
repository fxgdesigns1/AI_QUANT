#!/usr/bin/env python3
"""
Multi-Strategy Testing Framework - Strategy Manager
Central coordinator for all strategies with dynamic assignment and performance monitoring
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
import queue

from .dynamic_account_manager import get_account_manager
from .multi_account_data_feed import get_multi_account_data_feed
from .adaptive_system import AdaptiveTradingSystem, MarketCondition
from .strategy_factory import get_strategy_factory
from .telegram_notifier import TelegramNotifier
from .optimization_loader import (
    load_optimization_results,
    apply_per_pair_to_momentum,
    apply_per_pair_to_ultra_strict,
    apply_per_pair_to_gold,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyStatus(Enum):
    """Strategy execution status"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class StrategyPerformance(Enum):
    """Strategy performance levels"""
    EXCELLENT = "excellent"      # > 5% monthly return
    GOOD = "good"               # 2-5% monthly return
    MODERATE = "moderate"        # 0-2% monthly return
    POOR = "poor"               # < 0% monthly return
    CRITICAL = "critical"       # < -5% monthly return

@dataclass
class StrategyConfig:
    """Strategy configuration for multi-strategy testing"""
    strategy_id: str
    strategy_name: str
    strategy_class: Any
    account_id: str
    account_name: str
    instruments: List[str]
    max_positions: int
    max_daily_trades: int
    risk_per_trade: float
    stop_loss_pct: float
    take_profit_pct: float
    enabled: bool = True
    priority: int = 1
    performance_threshold: float = 0.02  # 2% monthly return threshold

@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    strategy_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    monthly_return: float
    max_drawdown: float
    sharpe_ratio: float
    avg_trade_duration: float
    last_update: datetime

@dataclass
class StrategyAssignment:
    """Strategy to account assignment"""
    strategy_id: str
    account_id: str
    assigned_at: datetime
    performance_score: float
    is_active: bool

class StrategyManager:
    """Central coordinator for multi-strategy testing framework"""
    
    def __init__(self):
        """Initialize strategy manager"""
        self.account_manager = get_account_manager()
        self.data_feed = get_multi_account_data_feed()
        self.telegram_notifier = TelegramNotifier()
        
        # Strategy registry
        self.strategies: Dict[str, StrategyConfig] = {}
        self.strategy_assignments: Dict[str, StrategyAssignment] = {}
        self.strategy_metrics: Dict[str, StrategyMetrics] = {}
        
        # Performance tracking
        self.performance_history: Dict[str, List[Dict]] = {}
        self.comparison_data: Dict[str, Any] = {}
        
        # System state
        self.is_running = False
        self.monitoring_thread = None
        self.assignment_lock = threading.Lock()
        
        # Initialize strategies
        self._initialize_strategies()
        
        logger.info("🎯 Strategy Manager initialized")
        logger.info(f"📊 Registered {len(self.strategies)} strategies")
    
    def _initialize_strategies(self):
        """Initialize all available strategies using strategy factory"""
        try:
            # Get available accounts
            active_accounts = self.account_manager.get_active_accounts()
            
            if not active_accounts:
                logger.warning("⚠️ No active accounts found for strategy assignment")
                return
            
            # Get strategy factory
            strategy_factory = get_strategy_factory()
            
            # Load strategies dynamically based on accounts.yaml
            from src.core.yaml_manager import get_yaml_manager
            yaml_mgr = get_yaml_manager()
            accounts = yaml_mgr.get_all_accounts()
            active_account_configs = [a for a in accounts if a.get('active', False)]
            
            logger.info(f"📊 Found {len(active_account_configs)} active account configurations")
            
            for account_config in active_account_configs:
                strategy_name = account_config.get('strategy')
                account_id = account_config.get('id')
                
                if strategy_name and account_id:
                    try:
                        # Load strategy using factory
                        strategy_instance = strategy_factory.get_strategy(
                            strategy_name, 
                            account_config=account_config
                        )
                        
                        # Create strategy config
                        strategy_id = f"{strategy_name.upper()}_{account_id[-3:]}"
                        self.strategies[strategy_id] = StrategyConfig(
                            strategy_id=strategy_id,
                            strategy_name=strategy_name.replace('_', ' ').title(),
                            strategy_class=strategy_instance,
                            account_id=account_id,
                            account_name=account_config.get('name', 'Unknown'),
                            instruments=account_config.get('instruments', []),
                            max_positions=account_config.get('risk_settings', {}).get('max_positions', 3),
                            max_daily_trades=account_config.get('risk_settings', {}).get('daily_trade_limit', 50),
                            risk_per_trade=account_config.get('risk_settings', {}).get('max_risk_per_trade', 0.02),
                            stop_loss_pct=0.002,  # Default
                            take_profit_pct=0.003,  # Default
                            priority=1,
                            performance_threshold=0.02
                        )
                        
                        logger.info(f"✅ Initialized strategy: {strategy_name} for account {account_id}")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to initialize {strategy_name} for {account_id}: {e}")
            
            # Initialize metrics for all strategies
            for strategy_id in self.strategies:
                self.strategy_metrics[strategy_id] = StrategyMetrics(
                    strategy_id=strategy_id,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    total_pnl=0.0,
                    monthly_return=0.0,
                    max_drawdown=0.0,
                    sharpe_ratio=0.0,
                    avg_trade_duration=0.0,
                    last_update=datetime.now()
                )
            
            logger.info(f"✅ All {len(self.strategies)} strategies initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize strategies: {e}")
    
    def start_multi_strategy_testing(self):
        """Start multi-strategy testing framework"""
        if self.is_running:
            logger.warning("Multi-strategy testing already running")
            return
        
        self.is_running = True
        
        # Start data collection
        self.data_feed.start()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        # Assign strategies to accounts
        self._assign_strategies_to_accounts()
        
        # Apply optimization results to live strategy instances after assignment
        try:
            results = load_optimization_results()
            for cfg in self.strategies.values():
                name = cfg.strategy_name
                strat = cfg.strategy_class
                if name == 'Ultra Strict Forex':
                    apply_per_pair_to_ultra_strict(strat, results)
                elif name in ('Alpha Momentum', 'Momentum Trading'):
                    # Alpha is ema-based; if Momentum strategy is used elsewhere, this keeps flexibility
                    apply_per_pair_to_momentum(strat, results)
                elif name == 'Gold Scalping':
                    apply_per_pair_to_gold(strat, results)
            logger.info("✅ Per-pair optimization overrides applied to active strategies")
        except Exception as e:
            logger.warning(f"⚠️ Failed to apply optimization overrides: {e}")
        
        logger.info("🚀 Multi-strategy testing framework started")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_message(
                "🎯 Multi-Strategy Testing Framework Started\n"
                f"📊 Active Strategies: {len(self.strategies)}\n"
                f"🏦 Accounts: {len(self.account_manager.get_active_accounts())}\n"
                "📈 Performance monitoring and comparison active"
            )
    
    def stop_multi_strategy_testing(self):
        """Stop multi-strategy testing framework"""
        self.is_running = False
        
        # Stop data collection
        self.data_feed.stop()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("🛑 Multi-strategy testing framework stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop for strategy performance"""
        while self.is_running:
            try:
                # Update strategy metrics
                self._update_strategy_metrics()
                
                # Check for strategy reassignment
                self._check_strategy_reassignment()
                
                # Update performance comparison
                self._update_performance_comparison()
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(60)
    
    def _assign_strategies_to_accounts(self):
        """Assign strategies to accounts for testing"""
        with self.assignment_lock:
            try:
                active_accounts = self.account_manager.get_active_accounts()
                
                for strategy_id, strategy_config in self.strategies.items():
                    if strategy_config.enabled:
                        # Assign strategy to account
                        assignment = StrategyAssignment(
                            strategy_id=strategy_id,
                            account_id=strategy_config.account_id,
                            assigned_at=datetime.now(),
                            performance_score=1.0,  # Initial score
                            is_active=True
                        )
                        
                        self.strategy_assignments[strategy_id] = assignment
                        
                        logger.info(f"✅ Assigned {strategy_config.strategy_name} to {strategy_config.account_name}")
                
                logger.info(f"🎯 Strategy assignment completed: {len(self.strategy_assignments)} assignments")
                
            except Exception as e:
                logger.error(f"❌ Failed to assign strategies: {e}")
    
    def _update_strategy_metrics(self):
        """Update performance metrics for all strategies"""
        try:
            for strategy_id, assignment in self.strategy_assignments.items():
                if not assignment.is_active:
                    continue
                
                # Get account performance data
                account_info = self.account_manager.get_account_info(assignment.account_id)
                if not account_info:
                    continue
                
                # Calculate metrics
                metrics = self.strategy_metrics[strategy_id]
                
                # Update trade statistics (simplified - in real implementation, 
                # you'd track individual trades)
                total_pnl = account_info.unrealized_pl + account_info.realized_pl
                balance = account_info.balance
                
                # Calculate monthly return (simplified)
                monthly_return = (total_pnl / balance * 100) if balance > 0 else 0
                
                # Update metrics
                metrics.total_pnl = total_pnl
                metrics.monthly_return = monthly_return
                metrics.last_update = datetime.now()
                
                # Estimate win rate (simplified)
                if metrics.total_trades > 0:
                    metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
                
                # Update performance history
                if strategy_id not in self.performance_history:
                    self.performance_history[strategy_id] = []
                
                self.performance_history[strategy_id].append({
                    'timestamp': datetime.now().isoformat(),
                    'pnl': total_pnl,
                    'return': monthly_return,
                    'balance': balance,
                    'positions': account_info.open_position_count
                })
                
                # Keep only last 100 entries
                if len(self.performance_history[strategy_id]) > 100:
                    self.performance_history[strategy_id] = self.performance_history[strategy_id][-100:]
                
        except Exception as e:
            logger.error(f"❌ Failed to update strategy metrics: {e}")
    
    def _check_strategy_reassignment(self):
        """Check if strategies need reassignment based on performance"""
        try:
            current_time = datetime.now()
            
            for strategy_id, assignment in self.strategy_assignments.items():
                if not assignment.is_active:
                    continue
                
                # Check if assignment is older than 2 days (testing period)
                if (current_time - assignment.assigned_at).total_seconds() > 172800:  # 2 days
                    
                    # Get current performance
                    metrics = self.strategy_metrics.get(strategy_id)
                    if not metrics:
                        continue
                    
                    # Check if performance meets threshold
                    strategy_config = self.strategies[strategy_id]
                    performance_met = metrics.monthly_return >= strategy_config.performance_threshold
                    
                    if performance_met:
                        logger.info(f"✅ {strategy_config.strategy_name} meets performance threshold")
                        # Keep strategy active
                        assignment.performance_score = 1.0
                    else:
                        logger.warning(f"⚠️ {strategy_config.strategy_name} below performance threshold")
                        # Consider reassignment or pausing
                        assignment.performance_score = 0.5
                        
                        # Send notification
                        if self.telegram_notifier:
                            self.telegram_notifier.send_message(
                                f"⚠️ Strategy Performance Alert\n"
                                f"📊 Strategy: {strategy_config.strategy_name}\n"
                                f"📉 Current Return: {metrics.monthly_return:.2f}%\n"
                                f"🎯 Threshold: {strategy_config.performance_threshold:.2f}%\n"
                                f"💡 Consider strategy adjustment"
                            )
                    
                    # Reset assignment time for next evaluation
                    assignment.assigned_at = current_time
                
        except Exception as e:
            logger.error(f"❌ Failed to check strategy reassignment: {e}")
    
    def _update_performance_comparison(self):
        """Update performance comparison data"""
        try:
            comparison_data = {
                'timestamp': datetime.now().isoformat(),
                'strategies': {}
            }
            
            for strategy_id, metrics in self.strategy_metrics.items():
                strategy_config = self.strategies[strategy_id]
                
                comparison_data['strategies'][strategy_id] = {
                    'name': strategy_config.strategy_name,
                    'monthly_return': metrics.monthly_return,
                    'total_pnl': metrics.total_pnl,
                    'win_rate': metrics.win_rate,
                    'total_trades': metrics.total_trades,
                    'performance_score': self.strategy_assignments.get(strategy_id, {}).get('performance_score', 0),
                    'status': 'active' if self.strategy_assignments.get(strategy_id, {}).get('is_active', False) else 'inactive'
                }
            
            self.comparison_data = comparison_data
            
        except Exception as e:
            logger.error(f"❌ Failed to update performance comparison: {e}")
    
    def get_strategy_performance_comparison(self) -> Dict[str, Any]:
        """Get current strategy performance comparison"""
        return self.comparison_data
    
    def get_best_performing_strategy(self) -> Optional[str]:
        """Get the best performing strategy based on monthly return"""
        try:
            best_strategy = None
            best_return = float('-inf')
            
            for strategy_id, metrics in self.strategy_metrics.items():
                if metrics.monthly_return > best_return:
                    best_return = metrics.monthly_return
                    best_strategy = strategy_id
            
            return best_strategy
            
        except Exception as e:
            logger.error(f"❌ Failed to get best performing strategy: {e}")
            return None
    
    def pause_strategy(self, strategy_id: str):
        """Pause a specific strategy"""
        try:
            if strategy_id in self.strategy_assignments:
                self.strategy_assignments[strategy_id].is_active = False
                logger.info(f"⏸️ Paused strategy: {strategy_id}")
                
                if self.telegram_notifier:
                    strategy_name = self.strategies.get(strategy_id, {}).get('strategy_name', strategy_id)
                    self.telegram_notifier.send_message(
                        f"⏸️ Strategy Paused\n"
                        f"📊 Strategy: {strategy_name}\n"
                        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Failed to pause strategy {strategy_id}: {e}")
    
    def resume_strategy(self, strategy_id: str):
        """Resume a specific strategy"""
        try:
            if strategy_id in self.strategy_assignments:
                self.strategy_assignments[strategy_id].is_active = True
                logger.info(f"▶️ Resumed strategy: {strategy_id}")
                
                if self.telegram_notifier:
                    strategy_name = self.strategies.get(strategy_id, {}).get('strategy_name', strategy_id)
                    self.telegram_notifier.send_message(
                        f"▶️ Strategy Resumed\n"
                        f"📊 Strategy: {strategy_name}\n"
                        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Failed to resume strategy {strategy_id}: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            active_strategies = sum(1 for assignment in self.strategy_assignments.values() if assignment.is_active)
            total_strategies = len(self.strategies)
            
            return {
                'is_running': self.is_running,
                'total_strategies': total_strategies,
                'active_strategies': active_strategies,
                'strategy_assignments': len(self.strategy_assignments),
                'performance_data_available': len(self.comparison_data.get('strategies', {})),
                'last_update': datetime.now().isoformat(),
                'strategies': {
                    strategy_id: {
                        'name': config.strategy_name,
                        'account': config.account_name,
                        'enabled': config.enabled,
                        'status': 'active' if self.strategy_assignments.get(strategy_id, {}).get('is_active', False) else 'inactive'
                    }
                    for strategy_id, config in self.strategies.items()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {}
    
    def export_performance_data(self, filename: str = None) -> str:
        """Export performance data for backtesting integration"""
        try:
            if filename is None:
                filename = f"strategy_performance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'system_status': self.get_system_status(),
                'performance_comparison': self.comparison_data,
                'strategy_metrics': {
                    strategy_id: asdict(metrics) for strategy_id, metrics in self.strategy_metrics.items()
                },
                'performance_history': self.performance_history,
                'strategy_configurations': {
                    strategy_id: {
                        'strategy_id': config.strategy_id,
                        'strategy_name': config.strategy_name,
                        'account_name': config.account_name,
                        'instruments': config.instruments,
                        'max_positions': config.max_positions,
                        'max_daily_trades': config.max_daily_trades,
                        'risk_per_trade': config.risk_per_trade,
                        'stop_loss_pct': config.stop_loss_pct,
                        'take_profit_pct': config.take_profit_pct,
                        'performance_threshold': config.performance_threshold
                    }
                    for strategy_id, config in self.strategies.items()
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"📊 Performance data exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to export performance data: {e}")
            return ""

# Global strategy manager instance
strategy_manager = StrategyManager()

def get_strategy_manager() -> StrategyManager:
    """Get the global strategy manager instance"""
    return strategy_manager

