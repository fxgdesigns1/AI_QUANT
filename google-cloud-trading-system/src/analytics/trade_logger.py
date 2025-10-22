#!/usr/bin/env python3
"""
Trade Logger - Intercept and Log All Trades
Hooks into order execution pipeline and syncs with OANDA
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid

from .trade_database import get_trade_database, TradeRecord
from .strategy_version_manager import get_strategy_version_manager
from .metrics_calculator import get_metrics_calculator

logger = logging.getLogger(__name__)


class TradeLogger:
    """Log and track all trades with OANDA synchronization"""
    
    def __init__(self):
        """Initialize trade logger"""
        self.db = get_trade_database()
        self.version_manager = get_strategy_version_manager()
        self.metrics_calc = get_metrics_calculator()
        
        # Track open positions for exit detection
        self._open_positions = {}  # trade_id -> position_info
        self._position_lock = threading.Lock()
        
        # Sync monitoring
        self._sync_thread = None
        self._sync_running = False
        self._sync_interval = 30  # seconds
        
        logger.info("✅ Trade logger initialized")
    
    def log_trade_entry(self, account_id: str, strategy_id: str, 
                       signal: Any, execution: Any) -> str:
        """
        Log trade entry immediately upon execution
        
        Args:
            account_id: OANDA account ID
            strategy_id: Strategy identifier
            signal: TradeSignal object with entry details
            execution: TradeExecution object with OANDA response
            
        Returns:
            trade_id for tracking
        """
        try:
            # Extract trade details
            trade_id = self._generate_trade_id(account_id, strategy_id)
            
            # Get or create strategy version
            strategy_version = self.version_manager.get_current_version(strategy_id)
            
            # Extract signal data
            instrument = getattr(signal, 'instrument', '')
            direction = 'BUY' if getattr(signal, 'side', '').upper() in ['BUY', 'LONG'] else 'SELL'
            entry_price = getattr(signal, 'entry_price', 0.0) or getattr(signal, 'price', 0.0)
            position_size = getattr(signal, 'position_size', 0.0) or abs(getattr(signal, 'units', 0))
            stop_loss = getattr(signal, 'stop_loss', None)
            take_profit = getattr(signal, 'take_profit', None)
            
            # Extract execution data
            if hasattr(execution, 'order') and execution.order:
                # Use actual filled price if available
                entry_price = getattr(execution.order, 'price', entry_price) or entry_price
                oanda_trade_id = getattr(execution.order, 'trade_id', None)
                commission = getattr(execution.order, 'commission', 0.0)
                slippage = getattr(execution.order, 'slippage', 0.0)
            else:
                oanda_trade_id = None
                commission = 0.0
                slippage = 0.0
            
            # Create trade record
            trade_record = TradeRecord(
                trade_id=trade_id,
                account_id=account_id,
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                instrument=instrument,
                direction=direction,
                position_size=position_size,
                entry_price=entry_price,
                entry_time=datetime.now().isoformat(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                commission=commission,
                execution_slippage=slippage,
                is_closed=False
            )
            
            # Insert into database
            success = self.db.insert_trade(trade_record)
            
            if success:
                # Track open position
                with self._position_lock:
                    self._open_positions[trade_id] = {
                        'account_id': account_id,
                        'instrument': instrument,
                        'oanda_trade_id': oanda_trade_id,
                        'entry_time': trade_record.entry_time,
                        'entry_price': entry_price,
                        'direction': direction,
                        'position_size': position_size,
                    }
                
                logger.info(f"✅ Trade entry logged: {trade_id} ({strategy_id} - {instrument} {direction})")
                return trade_id
            else:
                logger.error(f"❌ Failed to log trade entry: {trade_id}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Error logging trade entry: {e}")
            logger.exception("Full traceback:")
            return ""
    
    def log_trade_exit(self, trade_id: str, exit_price: float, 
                      exit_reason: str, pnl: Optional[float] = None) -> bool:
        """
        Log trade exit
        
        Args:
            trade_id: Internal trade ID
            exit_price: Exit price
            exit_reason: 'TP', 'SL', 'MANUAL', 'TIMEOUT'
            pnl: Realized P&L (optional, will calculate if not provided)
            
        Returns:
            Success boolean
        """
        try:
            # Get trade details
            trade = self.db.get_trade(trade_id)
            if not trade:
                logger.warning(f"⚠️ Trade {trade_id} not found for exit")
                return False
            
            if trade['is_closed']:
                logger.warning(f"⚠️ Trade {trade_id} already closed")
                return False
            
            # Calculate P&L if not provided
            if pnl is None:
                pnl = self._calculate_pnl(
                    entry_price=trade['entry_price'],
                    exit_price=exit_price,
                    position_size=trade['position_size'],
                    direction=trade['direction']
                )
            
            # Calculate pips
            pnl_pips = self._calculate_pips(
                entry_price=trade['entry_price'],
                exit_price=exit_price,
                instrument=trade['instrument'],
                direction=trade['direction']
            )
            
            # Calculate duration
            entry_time = datetime.fromisoformat(trade['entry_time'])
            exit_time = datetime.now()
            duration_seconds = int((exit_time - entry_time).total_seconds())
            
            # Update database
            success = self.db.update_trade_exit(
                trade_id=trade_id,
                exit_price=exit_price,
                exit_time=exit_time.isoformat(),
                exit_reason=exit_reason,
                realized_pnl=pnl,
                pnl_pips=pnl_pips,
                trade_duration_seconds=duration_seconds
            )
            
            if success:
                # Remove from open positions
                with self._position_lock:
                    self._open_positions.pop(trade_id, None)
                
                # Update strategy metrics
                self._update_strategy_metrics(trade['strategy_id'])
                
                logger.info(f"✅ Trade exit logged: {trade_id} (P&L: {pnl:.2f}, {exit_reason})")
                return True
            else:
                logger.error(f"❌ Failed to log trade exit: {trade_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error logging trade exit: {e}")
            logger.exception("Full traceback:")
            return False
    
    def _calculate_pnl(self, entry_price: float, exit_price: float,
                      position_size: float, direction: str) -> float:
        """Calculate realized P&L"""
        if direction == 'BUY':
            pnl = (exit_price - entry_price) * position_size
        else:  # SELL
            pnl = (entry_price - exit_price) * position_size
        
        return pnl
    
    def _calculate_pips(self, entry_price: float, exit_price: float,
                       instrument: str, direction: str) -> float:
        """Calculate P&L in pips"""
        # Determine pip value based on instrument
        if 'JPY' in instrument:
            pip_multiplier = 100  # JPY pairs: 0.01 = 1 pip
        else:
            pip_multiplier = 10000  # Other pairs: 0.0001 = 1 pip
        
        if direction == 'BUY':
            pips = (exit_price - entry_price) * pip_multiplier
        else:  # SELL
            pips = (entry_price - exit_price) * pip_multiplier
        
        return pips
    
    def _generate_trade_id(self, account_id: str, strategy_id: str) -> str:
        """Generate unique trade ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"{strategy_id}_{account_id}_{timestamp}_{unique_id}"
    
    def _update_strategy_metrics(self, strategy_id: str):
        """Update cached metrics for a strategy"""
        try:
            # Get all closed trades for this strategy
            closed_trades = self.db.get_closed_trades(strategy_id, days=90)
            open_trades = self.db.get_open_trades(strategy_id)
            
            if not closed_trades:
                return
            
            # Calculate metrics
            metrics = self.metrics_calc.calculate_all_metrics(closed_trades, strategy_id)
            
            # Add open trade count
            metrics['open_trades'] = len(open_trades)
            metrics['total_trades'] = len(closed_trades) + len(open_trades)
            
            # Upsert to database
            self.db.upsert_strategy_metrics(strategy_id, metrics)
            
            logger.info(f"✅ Updated metrics for {strategy_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update strategy metrics: {e}")
    
    def sync_with_oanda_positions(self, oanda_client=None):
        """
        Sync with OANDA to detect position closes
        This should be called periodically
        """
        if oanda_client is None:
            # Try to import and get OANDA client
            try:
                from ..core.oanda_client import OandaClient
                # This is a placeholder - would need actual account IDs
                logger.debug("OANDA sync: no client provided")
                return
            except:
                logger.debug("OANDA sync: client not available")
                return
        
        try:
            with self._position_lock:
                open_positions = dict(self._open_positions)
            
            # Group by account
            accounts_to_check = {}
            for trade_id, pos_info in open_positions.items():
                account_id = pos_info['account_id']
                if account_id not in accounts_to_check:
                    accounts_to_check[account_id] = []
                accounts_to_check[account_id].append((trade_id, pos_info))
            
            # Check each account
            for account_id, positions in accounts_to_check.items():
                try:
                    # Get open positions from OANDA
                    oanda_positions = oanda_client.get_open_positions(account_id)
                    
                    if oanda_positions is None:
                        continue
                    
                    # Create set of open instruments
                    open_instruments = set()
                    for oanda_pos in oanda_positions:
                        if hasattr(oanda_pos, 'instrument'):
                            open_instruments.add(oanda_pos.instrument)
                    
                    # Check our tracked positions
                    for trade_id, pos_info in positions:
                        instrument = pos_info['instrument']
                        
                        if instrument not in open_instruments:
                            # Position closed on OANDA but we haven't logged it
                            logger.warning(f"⚠️ Detected closed position: {trade_id} ({instrument})")
                            
                            # Get current price for exit
                            price_data = oanda_client.get_latest_price(instrument)
                            if price_data:
                                exit_price = price_data.bid if pos_info['direction'] == 'BUY' else price_data.ask
                                self.log_trade_exit(trade_id, exit_price, 'MANUAL')
                
                except Exception as e:
                    logger.error(f"❌ Error syncing account {account_id}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error in OANDA sync: {e}")
    
    def start_sync_monitoring(self, oanda_client=None):
        """Start background thread for position synchronization"""
        if self._sync_running:
            logger.warning("⚠️ Sync monitoring already running")
            return
        
        self._sync_running = True
        
        def sync_loop():
            logger.info("🔄 Starting position sync monitoring...")
            while self._sync_running:
                try:
                    self.sync_with_oanda_positions(oanda_client)
                    time.sleep(self._sync_interval)
                except Exception as e:
                    logger.error(f"❌ Error in sync loop: {e}")
                    time.sleep(self._sync_interval)
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info(f"✅ Sync monitoring started (interval: {self._sync_interval}s)")
    
    def stop_sync_monitoring(self):
        """Stop background synchronization"""
        self._sync_running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        logger.info("✅ Sync monitoring stopped")
    
    def get_open_trades(self, strategy_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get currently open trades"""
        return self.db.get_open_trades(strategy_id)
    
    def get_recent_trades(self, strategy_id: Optional[str] = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent closed trades"""
        trades = self.db.get_closed_trades(strategy_id, days=30)
        return trades[:limit]
    
    def get_trade_by_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get single trade by ID"""
        return self.db.get_trade(trade_id)
    
    def get_strategy_summary(self, strategy_id: str) -> Dict[str, Any]:
        """Get comprehensive summary for a strategy"""
        try:
            # Get metrics from database
            metrics = self.db.get_strategy_metrics(strategy_id)
            
            if not metrics:
                # Calculate fresh metrics
                closed_trades = self.db.get_closed_trades(strategy_id, days=90)
                open_trades = self.db.get_open_trades(strategy_id)
                
                if closed_trades:
                    metrics = self.metrics_calc.calculate_all_metrics(closed_trades, strategy_id)
                    metrics['open_trades'] = len(open_trades)
                    self.db.upsert_strategy_metrics(strategy_id, metrics)
                else:
                    metrics = {'strategy_id': strategy_id, 'total_trades': 0}
            
            # Get version info
            latest_version = self.version_manager.get_current_version(strategy_id)
            
            # Get recent trades
            recent_trades = self.get_recent_trades(strategy_id, limit=10)
            
            return {
                'strategy_id': strategy_id,
                'current_version': latest_version,
                'metrics': metrics,
                'recent_trades': recent_trades,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting strategy summary: {e}")
            return {'strategy_id': strategy_id, 'error': str(e)}
    
    def import_historical_trades_from_oanda(self, account_id: str, strategy_id: str,
                                           oanda_client, days: int = 7) -> int:
        """
        Import historical trades from OANDA API
        
        Returns:
            Number of trades imported
        """
        try:
            logger.info(f"🔄 Importing {days} days of historical trades for {strategy_id}...")
            
            # Get strategy version
            strategy_version = self.version_manager.initialize_strategy_if_needed(strategy_id)
            
            # Get transactions from OANDA
            from_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # This would use OANDA's transaction API
            # For now, placeholder for actual implementation
            logger.warning("⚠️ Historical import from OANDA not fully implemented")
            
            # Would fetch transactions, parse them, and insert as TradeRecords
            imported_count = 0
            
            return imported_count
            
        except Exception as e:
            logger.error(f"❌ Error importing historical trades: {e}")
            return 0
    
    def generate_daily_snapshot(self, strategy_id: str, date: Optional[str] = None):
        """Generate daily performance snapshot"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Get trades for the day
            start_time = f"{date}T00:00:00"
            end_time = f"{date}T23:59:59"
            
            trades = self.db.get_trades_by_date_range(start_time, end_time, strategy_id)
            closed_trades = [t for t in trades if t['is_closed'] == 1]
            
            if not closed_trades:
                logger.debug(f"No closed trades for {strategy_id} on {date}")
                return
            
            # Calculate metrics
            metrics = self.metrics_calc.calculate_all_metrics(closed_trades)
            
            # Insert snapshot
            self.db.upsert_daily_snapshot(date, strategy_id, metrics)
            
            logger.info(f"✅ Daily snapshot created: {strategy_id} - {date}")
            
        except Exception as e:
            logger.error(f"❌ Error generating daily snapshot: {e}")
    
    def cleanup_and_report(self):
        """Cleanup and generate reports - for scheduled jobs"""
        try:
            # Get all unique strategies
            all_metrics = self.db.get_all_strategy_metrics()
            strategy_ids = [m['strategy_id'] for m in all_metrics]
            
            # Generate today's snapshots
            today = datetime.now().strftime('%Y-%m-%d')
            for strategy_id in strategy_ids:
                self.generate_daily_snapshot(strategy_id, today)
            
            # Clear metrics cache
            self.metrics_calc.clear_cache()
            
            logger.info("✅ Daily cleanup and reporting complete")
            
        except Exception as e:
            logger.error(f"❌ Error in cleanup and report: {e}")


# Singleton instance
_trade_logger_instance = None
_trade_logger_lock = threading.Lock()


def get_trade_logger() -> TradeLogger:
    """Get singleton trade logger instance"""
    global _trade_logger_instance
    
    if _trade_logger_instance is None:
        with _trade_logger_lock:
            if _trade_logger_instance is None:
                _trade_logger_instance = TradeLogger()
    
    return _trade_logger_instance

