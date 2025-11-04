#!/usr/bin/env python3
"""
Comprehensive Trade Tracking and Logging System
Tracks all trades, signals, and system performance for analysis and backtesting
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class TradeStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class SignalStatus(Enum):
    GENERATED = "generated"
    SENT = "sent"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

@dataclass
class TradeEntry:
    """Complete trade entry record"""
    trade_id: str
    timestamp: datetime
    account: str
    instrument: str
    side: str  # BUY/SELL
    order_type: str  # LIMIT/MARKET
    units: int
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy: str
    confidence: float
    session: str
    status: TradeStatus
    fill_price: Optional[float] = None
    fill_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pips_profit: Optional[float] = None
    pips_drawdown: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    max_drawdown_pips: Optional[float] = None
    max_profit_pips: Optional[float] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None

@dataclass
class SignalEntry:
    """Signal generation and execution record"""
    signal_id: str
    timestamp: datetime
    instrument: str
    signal_type: str  # BUY/SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy: str
    reasoning: str
    session: str
    status: SignalStatus
    trade_id: Optional[str] = None
    execution_time: Optional[datetime] = None
    notes: Optional[str] = None

@dataclass
class SystemLog:
    """System performance and status log"""
    log_id: str
    timestamp: datetime
    log_type: str  # signal, trade, error, status, performance
    level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    data: Optional[Dict[str, Any]] = None
    account: Optional[str] = None
    instrument: Optional[str] = None

class TradeTracker:
    """Comprehensive trade tracking and logging system"""
    
    def __init__(self, db_path: str = None):
        # Prefer GAE-writable tmp for cloud; allow override via env
        default_db = os.getenv('TRADE_DB_PATH', '/tmp/trading_system.db')
        self.db_path = db_path or default_db
        self.log_file = f"trading_system_{datetime.now().strftime('%Y%m%d')}.log"
        self.setup_database()
        self.setup_logging()
        
        logger.info("📊 Trade Tracker initialized")
    
    def setup_database(self):
        """Setup SQLite database for trade tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    account TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    units INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    strategy TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    session TEXT NOT NULL,
                    status TEXT NOT NULL,
                    fill_price REAL,
                    fill_time TEXT,
                    exit_price REAL,
                    exit_time TEXT,
                    pips_profit REAL,
                    pips_drawdown REAL,
                    profit_loss REAL,
                    profit_loss_pct REAL,
                    max_drawdown_pips REAL,
                    max_profit_pips REAL,
                    duration_minutes INTEGER,
                    notes TEXT
                )
            ''')
            
            # Create signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    confidence REAL NOT NULL,
                    strategy TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    session TEXT NOT NULL,
                    status TEXT NOT NULL,
                    trade_id TEXT,
                    execution_time TEXT,
                    notes TEXT
                )
            ''')
            
            # Create system logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    log_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    log_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    account TEXT,
                    instrument TEXT
                )
            ''')
            
            # Create performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    account TEXT NOT NULL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    total_pips REAL,
                    total_profit_loss REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    avg_trade_duration REAL,
                    session TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Database setup completed")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
    
    def setup_logging(self):
        """Setup file logging for system logs"""
        try:
            # Create logs directory; prefer tmp on cloud
            logs_root = os.getenv('TRADE_LOG_DIR', '/tmp/logs')
            os.makedirs(logs_root, exist_ok=True)
            
            # Setup file handler
            file_handler = logging.FileHandler(os.path.join(logs_root, self.log_file))
            file_handler.setLevel(logging.INFO)
            
            # Setup formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            # Add handler to logger
            logger.addHandler(file_handler)
            
            logger.info("✅ File logging setup completed")
            
        except Exception as e:
            logger.error(f"❌ Logging setup failed: {e}")
    
    def log_signal(self, signal: SignalEntry) -> bool:
        """Log a trading signal"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO signals (
                    signal_id, timestamp, instrument, signal_type, entry_price,
                    stop_loss, take_profit, confidence, strategy, reasoning,
                    session, status, trade_id, execution_time, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.signal_id,
                signal.timestamp.isoformat(),
                signal.instrument,
                signal.signal_type,
                signal.entry_price,
                signal.stop_loss,
                signal.take_profit,
                signal.confidence,
                signal.strategy,
                signal.reasoning,
                signal.session,
                signal.status.value,
                signal.trade_id,
                signal.execution_time.isoformat() if signal.execution_time else None,
                signal.notes
            ))
            
            conn.commit()
            conn.close()
            
            # Log to file
            logger.info(f"📊 Signal logged: {signal.instrument} {signal.signal_type} "
                       f"at {signal.entry_price} (Confidence: {signal.confidence:.2f})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to log signal: {e}")
            return False
    
    def log_trade(self, trade: TradeEntry) -> bool:
        """Log a trade entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (
                    trade_id, timestamp, account, instrument, side, order_type,
                    units, entry_price, stop_loss, take_profit, strategy,
                    confidence, session, status, fill_price, fill_time,
                    exit_price, exit_time, pips_profit, pips_drawdown,
                    profit_loss, profit_loss_pct, max_drawdown_pips,
                    max_profit_pips, duration_minutes, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.trade_id,
                trade.timestamp.isoformat(),
                trade.account,
                trade.instrument,
                trade.side,
                trade.order_type,
                trade.units,
                trade.entry_price,
                trade.stop_loss,
                trade.take_profit,
                trade.strategy,
                trade.confidence,
                trade.session,
                trade.status.value,
                trade.fill_price,
                trade.fill_time.isoformat() if trade.fill_time else None,
                trade.exit_price,
                trade.exit_time.isoformat() if trade.exit_time else None,
                trade.pips_profit,
                trade.pips_drawdown,
                trade.profit_loss,
                trade.profit_loss_pct,
                trade.max_drawdown_pips,
                trade.max_profit_pips,
                trade.duration_minutes,
                trade.notes
            ))
            
            conn.commit()
            conn.close()
            
            # Log to file
            logger.info(f"💰 Trade logged: {trade.instrument} {trade.side} "
                       f"{trade.units} units at {trade.entry_price} "
                       f"(SL: {trade.stop_loss}, TP: {trade.take_profit})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to log trade: {e}")
            return False
    
    def update_trade_status(self, trade_id: str, status: TradeStatus, 
                          fill_price: Optional[float] = None,
                          exit_price: Optional[float] = None,
                          notes: Optional[str] = None) -> bool:
        """Update trade status and prices"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current trade data
            cursor.execute('SELECT * FROM trades WHERE trade_id = ?', (trade_id,))
            trade_data = cursor.fetchone()
            
            if not trade_data:
                logger.error(f"❌ Trade {trade_id} not found")
                return False
            
            # Calculate pips and P&L
            entry_price = trade_data[7]  # entry_price
            side = trade_data[4]  # side
            
            if fill_price:
                # Calculate pips from entry to fill
                pips = self._calculate_pips(entry_price, fill_price, side)
                
                cursor.execute('''
                    UPDATE trades SET 
                        status = ?, fill_price = ?, fill_time = ?,
                        pips_profit = ?, notes = ?
                    WHERE trade_id = ?
                ''', (status.value, fill_price, datetime.now().isoformat(), 
                      pips, notes, trade_id))
            
            if exit_price:
                # Calculate final P&L
                pips = self._calculate_pips(entry_price, exit_price, side)
                profit_loss = self._calculate_profit_loss(entry_price, exit_price, side, trade_data[6])  # units
                profit_loss_pct = (profit_loss / (entry_price * trade_data[6])) * 100
                
                # Calculate duration
                entry_time = datetime.fromisoformat(trade_data[1])
                duration_minutes = int((datetime.now() - entry_time).total_seconds() / 60)
                
                cursor.execute('''
                    UPDATE trades SET 
                        status = ?, exit_price = ?, exit_time = ?,
                        pips_profit = ?, profit_loss = ?, profit_loss_pct = ?,
                        duration_minutes = ?, notes = ?
                    WHERE trade_id = ?
                ''', (status.value, exit_price, datetime.now().isoformat(),
                      pips, profit_loss, profit_loss_pct, duration_minutes, notes, trade_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📊 Trade {trade_id} updated: {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update trade {trade_id}: {e}")
            return False
    
    def _calculate_pips(self, entry_price: float, current_price: float, side: str) -> float:
        """Calculate pips difference"""
        if side == "BUY":
            return (current_price - entry_price) * 10000  # For major pairs
        else:  # SELL
            return (entry_price - current_price) * 10000
    
    def _calculate_profit_loss(self, entry_price: float, exit_price: float, 
                             side: str, units: int) -> float:
        """Calculate profit/loss in account currency"""
        if side == "BUY":
            return (exit_price - entry_price) * units
        else:  # SELL
            return (entry_price - exit_price) * units
    
    def get_active_trades(self) -> List[Dict[str, Any]]:
        """Get all active trades with current status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                WHERE status IN ('pending', 'filled', 'partially_filled')
                ORDER BY timestamp DESC
            ''')
            
            trades = []
            for row in cursor.fetchall():
                trade = {
                    'trade_id': row[0],
                    'timestamp': row[1],
                    'account': row[2],
                    'instrument': row[3],
                    'side': row[4],
                    'order_type': row[5],
                    'units': row[6],
                    'entry_price': row[7],
                    'stop_loss': row[8],
                    'take_profit': row[9],
                    'strategy': row[10],
                    'confidence': row[11],
                    'session': row[12],
                    'status': row[13],
                    'fill_price': row[14],
                    'fill_time': row[15],
                    'pips_profit': row[18],
                    'pips_drawdown': row[19],
                    'profit_loss': row[20],
                    'profit_loss_pct': row[21]
                }
                trades.append(trade)
            
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"❌ Failed to get active trades: {e}")
            return []
    
    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            trades = []
            for row in cursor.fetchall():
                trade = {
                    'trade_id': row[0],
                    'timestamp': row[1],
                    'account': row[2],
                    'instrument': row[3],
                    'side': row[4],
                    'order_type': row[5],
                    'units': row[6],
                    'entry_price': row[7],
                    'stop_loss': row[8],
                    'take_profit': row[9],
                    'strategy': row[10],
                    'confidence': row[11],
                    'session': row[12],
                    'status': row[13],
                    'fill_price': row[14],
                    'exit_price': row[16],
                    'pips_profit': row[18],
                    'profit_loss': row[20],
                    'profit_loss_pct': row[21],
                    'duration_minutes': row[24]
                }
                trades.append(trade)
            
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"❌ Failed to get trade history: {e}")
            return []
    
    def get_performance_metrics(self, account: Optional[str] = None, 
                              days: int = 30) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Base query
            base_query = '''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                    AVG(profit_loss) as avg_profit_loss,
                    SUM(profit_loss) as total_profit_loss,
                    AVG(pips_profit) as avg_pips,
                    SUM(pips_profit) as total_pips,
                    MIN(profit_loss) as max_drawdown,
                    AVG(duration_minutes) as avg_duration
                FROM trades 
                WHERE status = 'filled' 
                AND timestamp >= datetime('now', '-{} days')
            '''.format(days)
            
            if account:
                base_query += f" AND account = '{account}'"
            
            cursor.execute(base_query)
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                total_trades = result[0]
                winning_trades = result[1]
                losing_trades = result[2]
                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                
                metrics = {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'avg_profit_loss': result[3] or 0,
                    'total_profit_loss': result[4] or 0,
                    'avg_pips': result[5] or 0,
                    'total_pips': result[6] or 0,
                    'max_drawdown': result[7] or 0,
                    'avg_duration_minutes': result[8] or 0
                }
            else:
                metrics = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'avg_profit_loss': 0,
                    'total_profit_loss': 0,
                    'avg_pips': 0,
                    'total_pips': 0,
                    'max_drawdown': 0,
                    'avg_duration_minutes': 0
                }
            
            conn.close()
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance metrics: {e}")
            return {}
    
    def log_system_event(self, log_type: str, level: str, message: str, 
                        data: Optional[Dict[str, Any]] = None,
                        account: Optional[str] = None,
                        instrument: Optional[str] = None):
        """Log system event"""
        try:
            log_entry = SystemLog(
                log_id=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{log_type}",
                timestamp=datetime.now(),
                log_type=log_type,
                level=level,
                message=message,
                data=data,
                account=account,
                instrument=instrument
            )
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_logs (
                    log_id, timestamp, log_type, level, message, data, account, instrument
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_entry.log_id,
                log_entry.timestamp.isoformat(),
                log_entry.log_type,
                log_entry.level,
                log_entry.message,
                json.dumps(log_entry.data) if log_entry.data else None,
                log_entry.account,
                log_entry.instrument
            ))
            
            conn.commit()
            conn.close()
            
            # Log to file
            log_level = getattr(logging, level.upper(), logging.INFO)
            logger.log(log_level, f"[{log_type}] {message}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log system event: {e}")
    
    def export_for_backtesting(self, days: int = 30) -> Dict[str, Any]:
        """Export trade data for backtesting analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all trades from last N days
            cursor.execute('''
                SELECT * FROM trades 
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp ASC
            '''.format(days))
            
            trades_data = []
            for row in cursor.fetchall():
                trade = {
                    'timestamp': row[1],
                    'instrument': row[3],
                    'side': row[4],
                    'entry_price': row[7],
                    'exit_price': row[16],
                    'stop_loss': row[8],
                    'take_profit': row[9],
                    'units': row[6],
                    'strategy': row[10],
                    'session': row[12],
                    'profit_loss': row[20],
                    'pips_profit': row[18],
                    'duration_minutes': row[24]
                }
                trades_data.append(trade)
            
            # Get signals data
            cursor.execute('''
                SELECT * FROM signals 
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp ASC
            '''.format(days))
            
            signals_data = []
            for row in cursor.fetchall():
                signal = {
                    'timestamp': row[1],
                    'instrument': row[2],
                    'signal_type': row[3],
                    'entry_price': row[4],
                    'stop_loss': row[5],
                    'take_profit': row[6],
                    'confidence': row[7],
                    'strategy': row[8],
                    'session': row[10],
                    'status': row[11]
                }
                signals_data.append(signal)
            
            conn.close()
            
            # Create export data
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'period_days': days,
                'trades': trades_data,
                'signals': signals_data,
                'summary': {
                    'total_trades': len(trades_data),
                    'total_signals': len(signals_data),
                    'date_range': {
                        'start': trades_data[0]['timestamp'] if trades_data else None,
                        'end': trades_data[-1]['timestamp'] if trades_data else None
                    }
                }
            }
            
            # Save to file
            export_filename = f"backtesting_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(export_filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"📊 Backtesting data exported: {export_filename}")
            return export_data
            
        except Exception as e:
            logger.error(f"❌ Failed to export backtesting data: {e}")
            return {}
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard display"""
        try:
            active_trades = self.get_active_trades()
            recent_trades = self.get_trade_history(20)
            performance = self.get_performance_metrics()
            
            # Calculate current pips for active trades
            for trade in active_trades:
                if trade['fill_price']:
                    # Calculate current pips (simplified - would need current price)
                    trade['current_pips'] = trade['pips_profit'] or 0
                    trade['current_drawdown'] = abs(trade['pips_drawdown']) if trade['pips_drawdown'] and trade['pips_drawdown'] < 0 else 0
                else:
                    trade['current_pips'] = 0
                    trade['current_drawdown'] = 0
            
            return {
                'active_trades': active_trades,
                'recent_trades': recent_trades,
                'performance': performance,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            return {}

