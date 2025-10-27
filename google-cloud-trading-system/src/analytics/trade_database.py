#!/usr/bin/env python3
"""
Trade Database - SQLite Schema and Operations
Persistent storage for all trade data with automatic retention management
"""

import os
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Complete trade record"""
    trade_id: str
    account_id: str
    strategy_id: str
    strategy_version: int
    instrument: str
    direction: str  # 'BUY' or 'SELL'
    position_size: float
    entry_price: float
    entry_time: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    exit_reason: Optional[str] = None  # 'TP', 'SL', 'MANUAL', 'TIMEOUT'
    realized_pnl: Optional[float] = None
    pnl_pips: Optional[float] = None
    commission: float = 0.0
    execution_slippage: float = 0.0
    trade_duration_seconds: Optional[int] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    is_closed: bool = False


class TradeDatabase:
    """SQLite database for trade tracking and analytics"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, db_path: str = None):
        """Initialize trade database"""
        if db_path is None:
            # Default path in data directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_dir = os.path.join(base_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'trading.db')
        
        self.db_path = db_path
        self._local = threading.local()
        
        # Initialize database
        self._create_schema()
        logger.info(f"✅ Trade database initialized: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get thread-safe database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        
        try:
            yield self._local.conn
        except Exception as e:
            self._local.conn.rollback()
            logger.error(f"❌ Database error: {e}")
            raise
    
    def _create_schema(self):
        """Create database schema with all tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Trades table - complete trade records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    strategy_version INTEGER NOT NULL,
                    instrument TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    position_size REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    exit_price REAL,
                    exit_time TEXT,
                    exit_reason TEXT,
                    realized_pnl REAL,
                    pnl_pips REAL,
                    commission REAL DEFAULT 0.0,
                    execution_slippage REAL DEFAULT 0.0,
                    trade_duration_seconds INTEGER,
                    tags TEXT,
                    notes TEXT,
                    is_closed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Strategy versions table - track configuration changes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    parameters_snapshot TEXT NOT NULL,
                    deployed_timestamp TEXT NOT NULL,
                    description TEXT,
                    config_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(strategy_id, version)
                )
            """)
            
            # Daily snapshots table - daily performance summaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    trades_count INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    net_pnl REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    sharpe_ratio REAL,
                    profit_factor REAL,
                    avg_win REAL,
                    avg_loss REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, strategy_id)
                )
            """)
            
            # Strategy metrics table - rolling metrics per strategy
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_metrics (
                    strategy_id TEXT PRIMARY KEY,
                    total_trades INTEGER DEFAULT 0,
                    open_trades INTEGER DEFAULT 0,
                    closed_trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    total_pnl REAL DEFAULT 0.0,
                    avg_win REAL DEFAULT 0.0,
                    avg_loss REAL DEFAULT 0.0,
                    largest_win REAL DEFAULT 0.0,
                    largest_loss REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    current_drawdown REAL DEFAULT 0.0,
                    profit_factor REAL DEFAULT 0.0,
                    sharpe_ratio REAL,
                    sortino_ratio REAL,
                    calmar_ratio REAL,
                    recovery_factor REAL,
                    avg_trade_duration_seconds INTEGER,
                    consecutive_wins INTEGER DEFAULT 0,
                    consecutive_losses INTEGER DEFAULT 0,
                    max_consecutive_wins INTEGER DEFAULT 0,
                    max_consecutive_losses INTEGER DEFAULT 0,
                    risk_reward_ratio REAL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_strategy 
                ON trades(strategy_id, is_closed)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_entry_time 
                ON trades(entry_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_account 
                ON trades(account_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_instrument 
                ON trades(instrument)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_date 
                ON daily_snapshots(date, strategy_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_versions_strategy 
                ON strategy_versions(strategy_id, version)
            """)
            
            conn.commit()
            logger.info("✅ Database schema created with all indexes")
    
    def insert_trade(self, trade: TradeRecord) -> bool:
        """Insert new trade record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                trade_dict = asdict(trade)
                trade_dict['is_closed'] = 1 if trade.is_closed else 0
                
                columns = ', '.join(trade_dict.keys())
                placeholders = ', '.join(['?' for _ in trade_dict])
                
                cursor.execute(
                    f"INSERT INTO trades ({columns}) VALUES ({placeholders})",
                    list(trade_dict.values())
                )
                
                conn.commit()
                logger.info(f"✅ Trade logged: {trade.trade_id} ({trade.strategy_id})")
                return True
                
        except sqlite3.IntegrityError:
            logger.warning(f"⚠️ Trade {trade.trade_id} already exists")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to insert trade: {e}")
            return False
    
    def update_trade_exit(self, trade_id: str, exit_price: float, 
                         exit_time: str, exit_reason: str, 
                         realized_pnl: float, pnl_pips: float,
                         trade_duration_seconds: int) -> bool:
        """Update trade with exit information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE trades 
                    SET exit_price = ?,
                        exit_time = ?,
                        exit_reason = ?,
                        realized_pnl = ?,
                        pnl_pips = ?,
                        trade_duration_seconds = ?,
                        is_closed = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE trade_id = ?
                """, (exit_price, exit_time, exit_reason, realized_pnl, 
                      pnl_pips, trade_duration_seconds, trade_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ Trade closed: {trade_id} (P&L: {realized_pnl:.2f})")
                    return True
                else:
                    logger.warning(f"⚠️ Trade {trade_id} not found for update")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to update trade exit: {e}")
            return False
    
    def get_trade(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get single trade by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Failed to get trade: {e}")
            return None
    
    def get_open_trades(self, strategy_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open trades, optionally filtered by strategy"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if strategy_id:
                    cursor.execute("""
                        SELECT * FROM trades 
                        WHERE is_closed = 0 AND strategy_id = ?
                        ORDER BY entry_time DESC
                    """, (strategy_id,))
                else:
                    cursor.execute("""
                        SELECT * FROM trades 
                        WHERE is_closed = 0 
                        ORDER BY entry_time DESC
                    """)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Failed to get open trades: {e}")
            return []
    
    def get_closed_trades(self, strategy_id: Optional[str] = None, 
                         days: int = 90) -> List[Dict[str, Any]]:
        """Get closed trades for a strategy within specified days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if strategy_id:
                    cursor.execute("""
                        SELECT * FROM trades 
                        WHERE is_closed = 1 
                        AND strategy_id = ?
                        AND entry_time >= ?
                        ORDER BY exit_time DESC
                    """, (strategy_id, cutoff_date))
                else:
                    cursor.execute("""
                        SELECT * FROM trades 
                        WHERE is_closed = 1 
                        AND entry_time >= ?
                        ORDER BY exit_time DESC
                    """, (cutoff_date,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Failed to get closed trades: {e}")
            return []
    
    def get_trades_by_date_range(self, start_date: str, end_date: str,
                                 strategy_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get trades within date range"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if strategy_id:
                    cursor.execute("""
                        SELECT * FROM trades 
                        WHERE entry_time >= ? AND entry_time <= ?
                        AND strategy_id = ?
                        ORDER BY entry_time DESC
                    """, (start_date, end_date, strategy_id))
                else:
                    cursor.execute("""
                        SELECT * FROM trades 
                        WHERE entry_time >= ? AND entry_time <= ?
                        ORDER BY entry_time DESC
                    """, (start_date, end_date))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Failed to get trades by date range: {e}")
            return []
    
    def insert_strategy_version(self, strategy_id: str, version: int,
                               parameters_snapshot: Dict[str, Any],
                               config_hash: str, description: str = "") -> bool:
        """Insert new strategy version"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO strategy_versions 
                    (strategy_id, version, parameters_snapshot, deployed_timestamp, 
                     description, config_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (strategy_id, version, json.dumps(parameters_snapshot),
                      datetime.now().isoformat(), description, config_hash))
                
                conn.commit()
                logger.info(f"✅ Strategy version saved: {strategy_id} v{version}")
                return True
                
        except sqlite3.IntegrityError:
            logger.warning(f"⚠️ Strategy version {strategy_id} v{version} already exists")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to insert strategy version: {e}")
            return False
    
    def get_latest_strategy_version(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get latest version for a strategy"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM strategy_versions 
                    WHERE strategy_id = ?
                    ORDER BY version DESC
                    LIMIT 1
                """, (strategy_id,))
                
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    result['parameters_snapshot'] = json.loads(result['parameters_snapshot'])
                    return result
                return None
        except Exception as e:
            logger.error(f"❌ Failed to get latest strategy version: {e}")
            return None
    
    def get_strategy_versions(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all versions for a strategy"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM strategy_versions 
                    WHERE strategy_id = ?
                    ORDER BY version DESC
                """, (strategy_id,))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    result['parameters_snapshot'] = json.loads(result['parameters_snapshot'])
                    results.append(result)
                return results
        except Exception as e:
            logger.error(f"❌ Failed to get strategy versions: {e}")
            return []
    
    def upsert_daily_snapshot(self, date: str, strategy_id: str, 
                             metrics: Dict[str, Any]) -> bool:
        """Insert or update daily snapshot"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO daily_snapshots 
                    (date, strategy_id, trades_count, wins, losses, win_rate,
                     net_pnl, max_drawdown, sharpe_ratio, profit_factor,
                     avg_win, avg_loss)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date, strategy_id) DO UPDATE SET
                        trades_count = excluded.trades_count,
                        wins = excluded.wins,
                        losses = excluded.losses,
                        win_rate = excluded.win_rate,
                        net_pnl = excluded.net_pnl,
                        max_drawdown = excluded.max_drawdown,
                        sharpe_ratio = excluded.sharpe_ratio,
                        profit_factor = excluded.profit_factor,
                        avg_win = excluded.avg_win,
                        avg_loss = excluded.avg_loss,
                        created_at = CURRENT_TIMESTAMP
                """, (date, strategy_id, 
                      metrics.get('trades_count', 0),
                      metrics.get('wins', 0),
                      metrics.get('losses', 0),
                      metrics.get('win_rate', 0.0),
                      metrics.get('net_pnl', 0.0),
                      metrics.get('max_drawdown', 0.0),
                      metrics.get('sharpe_ratio'),
                      metrics.get('profit_factor'),
                      metrics.get('avg_win'),
                      metrics.get('avg_loss')))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to upsert daily snapshot: {e}")
            return False
    
    def get_daily_snapshots(self, strategy_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily snapshots for a strategy"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM daily_snapshots 
                    WHERE strategy_id = ? AND date >= ?
                    ORDER BY date DESC
                """, (strategy_id, cutoff_date))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Failed to get daily snapshots: {e}")
            return []
    
    def upsert_strategy_metrics(self, strategy_id: str, 
                               metrics: Dict[str, Any]) -> bool:
        """Insert or update strategy metrics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic SQL based on provided metrics
                columns = ['strategy_id'] + list(metrics.keys()) + ['updated_at']
                values = [strategy_id] + list(metrics.values()) + [datetime.now().isoformat()]
                
                placeholders = ', '.join(['?' for _ in columns])
                update_clause = ', '.join([f"{k} = excluded.{k}" for k in metrics.keys()])
                
                cursor.execute(f"""
                    INSERT INTO strategy_metrics ({', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT(strategy_id) DO UPDATE SET
                        {update_clause},
                        updated_at = excluded.updated_at
                """, values)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to upsert strategy metrics: {e}")
            return False
    
    def get_strategy_metrics(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get current metrics for a strategy"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM strategy_metrics 
                    WHERE strategy_id = ?
                """, (strategy_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Failed to get strategy metrics: {e}")
            return None
    
    def get_all_strategy_metrics(self) -> List[Dict[str, Any]]:
        """Get metrics for all strategies"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM strategy_metrics")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Failed to get all strategy metrics: {e}")
            return []
    
    def delete_old_trades(self, days: int = 90) -> int:
        """Delete trades older than specified days (for archival)"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM trades 
                    WHERE entry_time < ? AND is_closed = 1
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"✅ Archived {deleted_count} old trades (>{days} days)")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Failed to delete old trades: {e}")
            return 0
    
    def vacuum_database(self):
        """Optimize database (reclaim space after deletions)"""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("✅ Database vacuumed and optimized")
        except Exception as e:
            logger.error(f"❌ Failed to vacuum database: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total trades
                cursor.execute("SELECT COUNT(*) FROM trades")
                stats['total_trades'] = cursor.fetchone()[0]
                
                # Open trades
                cursor.execute("SELECT COUNT(*) FROM trades WHERE is_closed = 0")
                stats['open_trades'] = cursor.fetchone()[0]
                
                # Closed trades
                cursor.execute("SELECT COUNT(*) FROM trades WHERE is_closed = 1")
                stats['closed_trades'] = cursor.fetchone()[0]
                
                # Strategies count
                cursor.execute("SELECT COUNT(DISTINCT strategy_id) FROM trades")
                stats['strategies_count'] = cursor.fetchone()[0]
                
                # Database size
                stats['db_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
                
                # Date range
                cursor.execute("SELECT MIN(entry_time), MAX(entry_time) FROM trades")
                min_date, max_date = cursor.fetchone()
                stats['earliest_trade'] = min_date
                stats['latest_trade'] = max_date
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {}


# Singleton instance
_trade_database_instance = None
_trade_database_lock = threading.Lock()


def get_trade_database() -> TradeDatabase:
    """Get singleton trade database instance"""
    global _trade_database_instance
    
    if _trade_database_instance is None:
        with _trade_database_lock:
            if _trade_database_instance is None:
                _trade_database_instance = TradeDatabase()
    
    return _trade_database_instance



