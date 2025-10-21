#!/usr/bin/env python3
"""
Multi-Strategy Testing Framework - Strategy Executor
Independent execution engines with isolated risk management per strategy
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

from .oanda_client import OandaClient
from .order_manager import TradeSignal, OrderSide, OrderStatus
from .account_manager import get_account_manager
from .multi_account_data_feed import get_multi_account_data_feed
from .strategy_manager import get_strategy_manager, StrategyConfig
from .telegram_notifier import TelegramNotifier

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Strategy execution status"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ExecutionMetrics:
    """Strategy execution metrics"""
    strategy_id: str
    signals_generated: int
    signals_executed: int
    signals_rejected: int
    execution_rate: float
    avg_execution_time: float
    risk_violations: int
    last_signal_time: datetime
    last_execution_time: datetime

@dataclass
class RiskLimits:
    """Risk limits for strategy execution"""
    max_position_size: float
    max_daily_loss: float
    max_concurrent_positions: int
    max_margin_usage: float
    max_trades_per_hour: int
    min_signal_confidence: float

class StrategyExecutor:
    """Independent execution engine for a single strategy"""
    
    def __init__(self, strategy_config: StrategyConfig, oanda_client: OandaClient):
        """Initialize strategy executor"""
        self.strategy_config = strategy_config
        self.oanda_client = oanda_client
        self.telegram_notifier = TelegramNotifier()
        
        # Execution state
        self.status = ExecutionStatus.STOPPED
        self.execution_thread = None
        self.signal_queue = queue.Queue()
        
        # Risk management
        self.risk_limits = self._create_risk_limits()
        self.current_positions = {}
        self.daily_pnl = 0.0
        self.hourly_trade_count = 0
        self.last_hour_reset = datetime.now()
        
        # Performance tracking
        self.execution_metrics = ExecutionMetrics(
            strategy_id=strategy_config.strategy_id,
            signals_generated=0,
            signals_executed=0,
            signals_rejected=0,
            execution_rate=0.0,
            avg_execution_time=0.0,
            risk_violations=0,
            last_signal_time=datetime.now(),
            last_execution_time=datetime.now()
        )
        
        # Data collection
        self.trade_log = []
        self.signal_log = []
        
        logger.info(f"🎯 Strategy Executor initialized for {strategy_config.strategy_name}")
    
    def _create_risk_limits(self) -> RiskLimits:
        """Create risk limits based on strategy configuration"""
        return RiskLimits(
            max_position_size=self.strategy_config.risk_per_trade,
            max_daily_loss=self.strategy_config.risk_per_trade * 10,  # 10x risk per trade
            max_concurrent_positions=self.strategy_config.max_positions,
            max_margin_usage=0.8,  # 80% max margin usage
            max_trades_per_hour=10,  # Max 10 trades per hour
            min_signal_confidence=0.6  # 60% minimum confidence
        )
    
    def start_execution(self):
        """Start strategy execution"""
        if self.status == ExecutionStatus.RUNNING:
            logger.warning(f"Strategy executor for {self.strategy_config.strategy_name} already running")
            return
        
        self.status = ExecutionStatus.RUNNING
        self.execution_thread = threading.Thread(
            target=self._execution_loop,
            daemon=True
        )
        self.execution_thread.start()
        
        logger.info(f"🚀 Started execution for {self.strategy_config.strategy_name}")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_message(
                f"🎯 Strategy Execution Started\n"
                f"📊 Strategy: {self.strategy_config.strategy_name}\n"
                f"🏦 Account: {self.strategy_config.account_name}\n"
                f"📈 Instruments: {', '.join(self.strategy_config.instruments)}"
            )
    
    def stop_execution(self):
        """Stop strategy execution"""
        self.status = ExecutionStatus.STOPPED
        
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        
        logger.info(f"🛑 Stopped execution for {self.strategy_config.strategy_name}")
    
    def pause_execution(self):
        """Pause strategy execution"""
        self.status = ExecutionStatus.PAUSED
        logger.info(f"⏸️ Paused execution for {self.strategy_config.strategy_name}")
    
    def resume_execution(self):
        """Resume strategy execution"""
        self.status = ExecutionStatus.RUNNING
        logger.info(f"▶️ Resumed execution for {self.strategy_config.strategy_name}")
    
    def _execution_loop(self):
        """Main execution loop"""
        while self.status == ExecutionStatus.RUNNING:
            try:
                # Reset hourly trade count if needed
                self._reset_hourly_counters()
                
                # Get market data for strategy instruments
                market_data = self._get_market_data()
                
                if not market_data:
                    time.sleep(5)
                    continue
                
                # Generate signals from strategy
                signals = self._generate_strategy_signals(market_data)
                
                # Process signals
                for signal in signals:
                    self._process_signal(signal)
                
                # Update positions
                self._update_positions()
                
                # Check risk limits
                self._check_risk_limits()
                
                # Sleep for strategy update interval
                time.sleep(30)  # 30 seconds between signal checks
                
            except Exception as e:
                logger.error(f"❌ Execution error for {self.strategy_config.strategy_name}: {e}")
                self.status = ExecutionStatus.ERROR
                time.sleep(60)  # Wait longer on error
    
    def _reset_hourly_counters(self):
        """Reset hourly trade counters"""
        current_time = datetime.now()
        if (current_time - self.last_hour_reset).total_seconds() >= 3600:  # 1 hour
            self.hourly_trade_count = 0
            self.last_hour_reset = current_time
    
    def _get_market_data(self) -> Optional[Dict[str, Any]]:
        """Get market data for strategy instruments"""
        try:
            multi_data_feed = get_multi_account_data_feed()
            market_data = multi_data_feed.get_market_data(self.strategy_config.account_id)
            
            # Filter data for strategy instruments
            filtered_data = {}
            for instrument in self.strategy_config.instruments:
                if instrument in market_data:
                    filtered_data[instrument] = market_data[instrument]
            
            return filtered_data if filtered_data else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get market data for {self.strategy_config.strategy_name}: {e}")
            return None
    
    def _generate_strategy_signals(self, market_data: Dict[str, Any]) -> List[TradeSignal]:
        """Generate signals from strategy"""
        try:
            # Get strategy instance
            strategy = self.strategy_config.strategy_class
            
            # Generate signals
            signals = strategy.analyze_market(market_data)
            
            # Update metrics
            self.execution_metrics.signals_generated += len(signals)
            if signals:
                self.execution_metrics.last_signal_time = datetime.now()
            
            # Log signals
            for signal in signals:
                self.signal_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'strategy_id': self.strategy_config.strategy_id,
                    'signal': asdict(signal),
                    'processed': False
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Failed to generate signals for {self.strategy_config.strategy_name}: {e}")
            return []
    
    def _process_signal(self, signal: TradeSignal):
        """Process a trading signal"""
        try:
            # Check if signal meets minimum confidence
            if signal.confidence < self.risk_limits.min_signal_confidence:
                self.execution_metrics.signals_rejected += 1
                logger.info(f"❌ Signal rejected: confidence {signal.confidence:.2f} < {self.risk_limits.min_signal_confidence}")
                return
            
            # Check risk limits before execution
            if not self._check_signal_risk_limits(signal):
                self.execution_metrics.signals_rejected += 1
                return
            
            # Execute signal
            execution_start = time.time()
            
            # Place order
            order_result = self._place_order(signal)
            
            execution_time = time.time() - execution_start
            
            if order_result:
                self.execution_metrics.signals_executed += 1
                self.execution_metrics.last_execution_time = datetime.now()
                self.hourly_trade_count += 1
                
                # Update average execution time
                total_executions = self.execution_metrics.signals_executed
                current_avg = self.execution_metrics.avg_execution_time
                self.execution_metrics.avg_execution_time = (
                    (current_avg * (total_executions - 1) + execution_time) / total_executions
                )
                
                # Log trade
                self.trade_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'strategy_id': self.strategy_config.strategy_id,
                    'signal': asdict(signal),
                    'order_result': order_result,
                    'execution_time': execution_time
                })
                
                logger.info(f"✅ Signal executed for {self.strategy_config.strategy_name}: {signal.instrument} {signal.side.value}")
                
                # Send notification for significant trades
                if signal.confidence > 0.8:
                    if self.telegram_notifier:
                        self.telegram_notifier.send_message(
                            f"🎯 High Confidence Trade Executed\n"
                            f"📊 Strategy: {self.strategy_config.strategy_name}\n"
                            f"📈 {signal.instrument} {signal.side.value}\n"
                            f"🎯 Confidence: {signal.confidence:.1%}\n"
                            f"💰 Units: {signal.units}"
                        )
            else:
                self.execution_metrics.signals_rejected += 1
                logger.warning(f"❌ Failed to execute signal for {self.strategy_config.strategy_name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing signal for {self.strategy_config.strategy_name}: {e}")
            self.execution_metrics.signals_rejected += 1
    
    def _check_signal_risk_limits(self, signal: TradeSignal) -> bool:
        """Check if signal violates risk limits"""
        try:
            # Check hourly trade limit
            if self.hourly_trade_count >= self.risk_limits.max_trades_per_hour:
                logger.warning(f"⚠️ Hourly trade limit reached for {self.strategy_config.strategy_name}")
                return False
            
            # Check daily trade limit
            if self.execution_metrics.signals_executed >= self.strategy_config.max_daily_trades:
                logger.warning(f"⚠️ Daily trade limit reached for {self.strategy_config.strategy_name}")
                return False
            
            # Check position size
            position_value = abs(signal.units) * signal.stop_loss
            max_position_value = self.risk_limits.max_position_size * 10000  # Convert to units
            
            if position_value > max_position_value:
                logger.warning(f"⚠️ Position size too large for {self.strategy_config.strategy_name}")
                return False
            
            # Check concurrent positions
            current_position_count = len([p for p in self.current_positions.values() if p != 0])
            if current_position_count >= self.risk_limits.max_concurrent_positions:
                logger.warning(f"⚠️ Max concurrent positions reached for {self.strategy_config.strategy_name}")
                return False
            
            # Check margin usage
            account_info = self.oanda_client.get_account_info()
            if account_info:
                margin_usage = account_info.margin_used / account_info.balance if account_info.balance > 0 else 0
                if margin_usage >= self.risk_limits.max_margin_usage:
                    logger.warning(f"⚠️ Margin usage too high for {self.strategy_config.strategy_name}: {margin_usage:.1%}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking risk limits: {e}")
            return False
    
    def _place_order(self, signal: TradeSignal) -> Optional[Dict[str, Any]]:
        """Place order for signal"""
        try:
            # Determine order side
            units = signal.units if signal.side == OrderSide.BUY else -signal.units
            
            # Place market order
            order_result = self.oanda_client.place_market_order(
                instrument=signal.instrument,
                units=units,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            if order_result:
                return {
                    'order_id': order_result.get('orderID'),
                    'instrument': signal.instrument,
                    'units': units,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to place order for {signal.instrument}: {e}")
            return None
    
    def _update_positions(self):
        """Update current positions"""
        try:
            positions = self.oanda_client.get_positions()
            
            for instrument, position in positions.items():
                if instrument in self.strategy_config.instruments:
                    total_units = position.long_units + position.short_units
                    self.current_positions[instrument] = total_units
            
        except Exception as e:
            logger.error(f"❌ Failed to update positions: {e}")
    
    def _check_risk_limits(self):
        """Check overall risk limits"""
        try:
            account_info = self.oanda_client.get_account_info()
            if not account_info:
                return
            
            # Check daily loss limit
            daily_pnl = account_info.unrealized_pl + account_info.realized_pl
            if daily_pnl < -self.risk_limits.max_daily_loss:
                logger.error(f"🚨 Daily loss limit exceeded for {self.strategy_config.strategy_name}")
                self.execution_metrics.risk_violations += 1
                
                # Pause execution
                self.pause_execution()
                
                if self.telegram_notifier:
                    self.telegram_notifier.send_message(
                        f"🚨 RISK LIMIT EXCEEDED\n"
                        f"📊 Strategy: {self.strategy_config.strategy_name}\n"
                        f"💰 Daily P&L: ${daily_pnl:.2f}\n"
                        f"⚠️ Limit: ${self.risk_limits.max_daily_loss:.2f}\n"
                        f"⏸️ Execution paused automatically"
                    )
            
        except Exception as e:
            logger.error(f"❌ Error checking risk limits: {e}")
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get execution status and metrics"""
        try:
            # Calculate execution rate
            total_signals = self.execution_metrics.signals_generated
            if total_signals > 0:
                self.execution_metrics.execution_rate = (
                    self.execution_metrics.signals_executed / total_signals
                )
            
            return {
                'strategy_id': self.strategy_config.strategy_id,
                'strategy_name': self.strategy_config.strategy_name,
                'status': self.status.value,
                'metrics': asdict(self.execution_metrics),
                'risk_limits': asdict(self.risk_limits),
                'current_positions': self.current_positions,
                'daily_pnl': self.daily_pnl,
                'hourly_trade_count': self.hourly_trade_count,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get execution status: {e}")
            return {}
    
    def export_execution_data(self) -> Dict[str, Any]:
        """Export execution data for analysis"""
        try:
            return {
                'strategy_config': asdict(self.strategy_config),
                'execution_metrics': asdict(self.execution_metrics),
                'risk_limits': asdict(self.risk_limits),
                'trade_log': self.trade_log[-100:],  # Last 100 trades
                'signal_log': self.signal_log[-100:],  # Last 100 signals
                'current_positions': self.current_positions,
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to export execution data: {e}")
            return {}

class MultiStrategyExecutor:
    """Manager for multiple strategy executors"""
    
    def __init__(self):
        """Initialize multi-strategy executor"""
        self.strategy_manager = get_strategy_manager()
        self.account_manager = get_account_manager()
        self.telegram_notifier = TelegramNotifier()
        
        # Executors
        self.executors: Dict[str, StrategyExecutor] = {}
        
        logger.info("🎯 Multi-Strategy Executor initialized")
    
    def initialize_executors(self):
        """Initialize executors for all active strategies"""
        try:
            # Get strategy configurations
            strategies = self.strategy_manager.strategies
            
            for strategy_id, strategy_config in strategies.items():
                if not strategy_config.enabled:
                    continue
                
                # Get OANDA client for strategy account
                account_clients = self.account_manager.accounts
                oanda_client = account_clients.get(strategy_config.account_name)
                
                if not oanda_client:
                    logger.error(f"❌ No OANDA client found for account {strategy_config.account_name}")
                    continue
                
                # Create executor
                executor = StrategyExecutor(strategy_config, oanda_client)
                self.executors[strategy_id] = executor
                
                logger.info(f"✅ Executor created for {strategy_config.strategy_name}")
            
            logger.info(f"🎯 Initialized {len(self.executors)} strategy executors")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize executors: {e}")
    
    def start_all_executors(self):
        """Start all strategy executors"""
        try:
            for strategy_id, executor in self.executors.items():
                executor.start_execution()
            
            logger.info(f"🚀 Started {len(self.executors)} strategy executors")
            
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    f"🎯 Multi-Strategy Execution Started\n"
                    f"📊 Active Executors: {len(self.executors)}\n"
                    f"🏦 Accounts: {len(set(exec.strategy_config.account_name for exec in self.executors.values()))}\n"
                    f"📈 All strategies running independently"
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to start executors: {e}")
    
    def stop_all_executors(self):
        """Stop all strategy executors"""
        try:
            for strategy_id, executor in self.executors.items():
                executor.stop_execution()
            
            logger.info(f"🛑 Stopped {len(self.executors)} strategy executors")
                
        except Exception as e:
            logger.error(f"❌ Failed to stop executors: {e}")
    
    def pause_executor(self, strategy_id: str):
        """Pause specific executor"""
        try:
            if strategy_id in self.executors:
                self.executors[strategy_id].pause_execution()
                logger.info(f"⏸️ Paused executor for {strategy_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to pause executor {strategy_id}: {e}")
    
    def resume_executor(self, strategy_id: str):
        """Resume specific executor"""
        try:
            if strategy_id in self.executors:
                self.executors[strategy_id].resume_execution()
                logger.info(f"▶️ Resumed executor for {strategy_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to resume executor {strategy_id}: {e}")
    
    def get_all_execution_status(self) -> Dict[str, Any]:
        """Get execution status for all executors"""
        try:
            status_data = {}
            
            for strategy_id, executor in self.executors.items():
                status_data[strategy_id] = executor.get_execution_status()
            
            return {
                'total_executors': len(self.executors),
                'active_executors': sum(1 for exec in self.executors.values() if exec.status == ExecutionStatus.RUNNING),
                'paused_executors': sum(1 for exec in self.executors.values() if exec.status == ExecutionStatus.PAUSED),
                'executors': status_data,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get execution status: {e}")
            return {}
    
    def export_all_execution_data(self) -> Dict[str, Any]:
        """Export execution data for all executors"""
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_executors': len(self.executors),
                'executors': {}
            }
            
            for strategy_id, executor in self.executors.items():
                export_data['executors'][strategy_id] = executor.export_execution_data()
            
            return export_data
            
        except Exception as e:
            logger.error(f"❌ Failed to export execution data: {e}")
            return {}

# Global multi-strategy executor instance
multi_strategy_executor = MultiStrategyExecutor()

def get_multi_strategy_executor() -> MultiStrategyExecutor:
    """Get the global multi-strategy executor instance"""
    return multi_strategy_executor

