#!/usr/bin/env python3
"""
Database models and connection management
Uses SQLite for analytics data storage
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import uuid

logger = logging.getLogger(__name__)


class PerformanceDatabase:
    """SQLite database for performance analytics"""
    
    def __init__(self, db_path: str = "analytics/analytics.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database and tables if they don't exist"""
        try:
            # Create directory if needed
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Read and execute schema
            schema_path = Path(__file__).parent / "schema.sql"
            with open(schema_path, 'r') as f:
                schema = f.read()
                self.conn.executescript(schema)
            
            self.conn.commit()
            logger.info(f"✅ Analytics database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("✅ Database connection closed")
    
    # ========================================================================
    # TRADE METHODS
    # ========================================================================
    
    def store_trade(self, trade_data: Dict[str, Any]) -> str:
        """Store a trade in the database"""
        try:
            trade_id = trade_data.get('trade_id', str(uuid.uuid4()))
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trades (
                    trade_id, account_id, account_name, instrument, strategy_name,
                    entry_time, entry_price, units, side, entry_reason,
                    exit_time, exit_price, exit_reason,
                    realized_pl, realized_pl_pct, commission, net_pl,
                    risk_amount, risk_pct, r_multiple,
                    market_regime, volatility_score, spread_at_entry, news_sentiment,
                    duration_seconds, bars_held, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                trade_data.get('account_id'),
                trade_data.get('account_name'),
                trade_data.get('instrument'),
                trade_data.get('strategy_name'),
                trade_data.get('entry_time'),
                trade_data.get('entry_price'),
                trade_data.get('units'),
                trade_data.get('side'),
                trade_data.get('entry_reason'),
                trade_data.get('exit_time'),
                trade_data.get('exit_price'),
                trade_data.get('exit_reason'),
                trade_data.get('realized_pl'),
                trade_data.get('realized_pl_pct'),
                trade_data.get('commission', 0.0),
                trade_data.get('net_pl'),
                trade_data.get('risk_amount'),
                trade_data.get('risk_pct'),
                trade_data.get('r_multiple'),
                trade_data.get('market_regime'),
                trade_data.get('volatility_score'),
                trade_data.get('spread_at_entry'),
                trade_data.get('news_sentiment'),
                trade_data.get('duration_seconds'),
                trade_data.get('bars_held'),
                trade_data.get('status', 'closed')
            ))
            
            self.conn.commit()
            logger.info(f"✅ Stored trade: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store trade: {e}")
            self.conn.rollback()
            raise
    
    def get_trades(self, 
                   account_id: Optional[str] = None,
                   strategy_name: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   status: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trades with optional filters"""
        try:
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if account_id:
                query += " AND account_id = ?"
                params.append(account_id)
            
            if strategy_name:
                query += " AND strategy_name = ?"
                params.append(strategy_name)
            
            if start_date:
                query += " AND entry_time >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND entry_time <= ?"
                params.append(end_date.isoformat())
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY entry_time DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            
            trades = [dict(row) for row in cursor.fetchall()]
            return trades
            
        except Exception as e:
            logger.error(f"❌ Failed to get trades: {e}")
            return []
    
    # ========================================================================
    # SNAPSHOT METHODS
    # ========================================================================
    
    def store_snapshot(self, snapshot_data: Dict[str, Any]) -> str:
        """Store an account snapshot"""
        try:
            snapshot_id = snapshot_data.get('snapshot_id', str(uuid.uuid4()))
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO account_snapshots (
                    snapshot_id, timestamp, account_id, account_name,
                    balance, equity, margin_used, margin_available, unrealized_pl,
                    open_positions, open_trades, pending_orders,
                    daily_pl, daily_trades, daily_wins, daily_losses,
                    total_trades, total_wins, total_losses, win_rate,
                    avg_win, avg_loss, profit_factor,
                    max_drawdown, max_drawdown_pct, current_drawdown,
                    sharpe_ratio, sortino_ratio, calmar_ratio,
                    daily_return, weekly_return, monthly_return, ytd_return,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id,
                snapshot_data.get('timestamp', datetime.now().isoformat()),
                snapshot_data.get('account_id'),
                snapshot_data.get('account_name'),
                snapshot_data.get('balance'),
                snapshot_data.get('equity'),
                snapshot_data.get('margin_used', 0.0),
                snapshot_data.get('margin_available', 0.0),
                snapshot_data.get('unrealized_pl', 0.0),
                snapshot_data.get('open_positions', 0),
                snapshot_data.get('open_trades', 0),
                snapshot_data.get('pending_orders', 0),
                snapshot_data.get('daily_pl', 0.0),
                snapshot_data.get('daily_trades', 0),
                snapshot_data.get('daily_wins', 0),
                snapshot_data.get('daily_losses', 0),
                snapshot_data.get('total_trades', 0),
                snapshot_data.get('total_wins', 0),
                snapshot_data.get('total_losses', 0),
                snapshot_data.get('win_rate', 0.0),
                snapshot_data.get('avg_win', 0.0),
                snapshot_data.get('avg_loss', 0.0),
                snapshot_data.get('profit_factor', 0.0),
                snapshot_data.get('max_drawdown', 0.0),
                snapshot_data.get('max_drawdown_pct', 0.0),
                snapshot_data.get('current_drawdown', 0.0),
                snapshot_data.get('sharpe_ratio', 0.0),
                snapshot_data.get('sortino_ratio', 0.0),
                snapshot_data.get('calmar_ratio', 0.0),
                snapshot_data.get('daily_return', 0.0),
                snapshot_data.get('weekly_return', 0.0),
                snapshot_data.get('monthly_return', 0.0),
                snapshot_data.get('ytd_return', 0.0),
                json.dumps(snapshot_data.get('metadata', {}))
            ))
            
            self.conn.commit()
            logger.info(f"✅ Stored snapshot: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store snapshot: {e}")
            self.conn.rollback()
            raise
    
    def get_latest_snapshot(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot for an account"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM account_snapshots
                WHERE account_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (account_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest snapshot: {e}")
            return None
    
    # ========================================================================
    # STRATEGY CHANGE METHODS
    # ========================================================================
    
    def store_strategy_change(self, change_data: Dict[str, Any]) -> str:
        """Store a strategy parameter change"""
        try:
            change_id = change_data.get('change_id', str(uuid.uuid4()))
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO strategy_changes (
                    change_id, timestamp, strategy_name, account_id,
                    parameter_changed, old_value, new_value, change_reason, changed_by,
                    trades_before, win_rate_before, avg_pl_before, sharpe_before,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                change_id,
                change_data.get('timestamp', datetime.now().isoformat()),
                change_data.get('strategy_name'),
                change_data.get('account_id'),
                change_data.get('parameter_changed'),
                str(change_data.get('old_value')),
                str(change_data.get('new_value')),
                change_data.get('change_reason'),
                change_data.get('changed_by', 'system'),
                change_data.get('trades_before', 0),
                change_data.get('win_rate_before', 0.0),
                change_data.get('avg_pl_before', 0.0),
                change_data.get('sharpe_before', 0.0),
                json.dumps(change_data.get('metadata', {}))
            ))
            
            self.conn.commit()
            logger.info(f"✅ Stored strategy change: {change_id}")
            return change_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store strategy change: {e}")
            self.conn.rollback()
            raise
    
    # ========================================================================
    # STRATEGY METRICS METHODS
    # ========================================================================
    
    def store_strategy_metrics(self, metrics_data: Dict[str, Any]) -> str:
        """Store calculated strategy metrics"""
        try:
            metric_id = metrics_data.get('metric_id', str(uuid.uuid4()))
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO strategy_metrics (
                    metric_id, timestamp, strategy_name, account_id, time_period,
                    total_trades, winning_trades, losing_trades, break_even_trades, win_rate,
                    gross_profit, gross_loss, net_profit, profit_factor,
                    avg_trade_pl, avg_win, avg_loss, largest_win, largest_loss,
                    max_drawdown, avg_drawdown, recovery_factor,
                    sharpe_ratio, sortino_ratio, calmar_ratio,
                    avg_trade_duration, avg_bars_held, trades_per_day, avg_r_multiple,
                    consecutive_wins, consecutive_losses, max_consecutive_wins, max_consecutive_losses,
                    trending_win_rate, ranging_win_rate, volatile_win_rate,
                    best_day, worst_day, avg_daily_return, volatility,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric_id,
                metrics_data.get('timestamp', datetime.now().isoformat()),
                metrics_data.get('strategy_name'),
                metrics_data.get('account_id'),
                metrics_data.get('time_period', 'all_time'),
                metrics_data.get('total_trades', 0),
                metrics_data.get('winning_trades', 0),
                metrics_data.get('losing_trades', 0),
                metrics_data.get('break_even_trades', 0),
                metrics_data.get('win_rate', 0.0),
                metrics_data.get('gross_profit', 0.0),
                metrics_data.get('gross_loss', 0.0),
                metrics_data.get('net_profit', 0.0),
                metrics_data.get('profit_factor', 0.0),
                metrics_data.get('avg_trade_pl', 0.0),
                metrics_data.get('avg_win', 0.0),
                metrics_data.get('avg_loss', 0.0),
                metrics_data.get('largest_win', 0.0),
                metrics_data.get('largest_loss', 0.0),
                metrics_data.get('max_drawdown', 0.0),
                metrics_data.get('avg_drawdown', 0.0),
                metrics_data.get('recovery_factor', 0.0),
                metrics_data.get('sharpe_ratio', 0.0),
                metrics_data.get('sortino_ratio', 0.0),
                metrics_data.get('calmar_ratio', 0.0),
                metrics_data.get('avg_trade_duration', 0.0),
                metrics_data.get('avg_bars_held', 0.0),
                metrics_data.get('trades_per_day', 0.0),
                metrics_data.get('avg_r_multiple', 0.0),
                metrics_data.get('consecutive_wins', 0),
                metrics_data.get('consecutive_losses', 0),
                metrics_data.get('max_consecutive_wins', 0),
                metrics_data.get('max_consecutive_losses', 0),
                metrics_data.get('trending_win_rate', 0.0),
                metrics_data.get('ranging_win_rate', 0.0),
                metrics_data.get('volatile_win_rate', 0.0),
                metrics_data.get('best_day', 0.0),
                metrics_data.get('worst_day', 0.0),
                metrics_data.get('avg_daily_return', 0.0),
                metrics_data.get('volatility', 0.0),
                json.dumps(metrics_data.get('metadata', {}))
            ))
            
            self.conn.commit()
            logger.info(f"✅ Stored strategy metrics: {metric_id}")
            return metric_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store strategy metrics: {e}")
            self.conn.rollback()
            raise
    
    def get_strategy_metrics(self, 
                            strategy_name: str,
                            time_period: str = 'all_time',
                            account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the latest metrics for a strategy"""
        try:
            query = """
                SELECT * FROM strategy_metrics
                WHERE strategy_name = ? AND time_period = ?
            """
            params = [strategy_name, time_period]
            
            if account_id:
                query += " AND account_id = ?"
                params.append(account_id)
            
            query += " ORDER BY timestamp DESC LIMIT 1"
            
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get strategy metrics: {e}")
            return None
    
    # ========================================================================
    # ANALYTICS QUERIES
    # ========================================================================
    
    def get_equity_curve(self, account_id: str, days: int = 30) -> List[Tuple[datetime, float]]:
        """Get equity curve for an account"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT timestamp, equity
                FROM account_snapshots
                WHERE account_id = ?
                AND datetime(timestamp) >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp ASC
            """, (account_id, days))
            
            return [(row['timestamp'], row['equity']) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"❌ Failed to get equity curve: {e}")
            return []
    
    def get_daily_returns(self, 
                         strategy_name: Optional[str] = None,
                         account_id: Optional[str] = None,
                         days: int = 30) -> List[float]:
        """Get daily returns for analysis"""
        try:
            query = """
                SELECT SUM(net_pl) as daily_pl
                FROM trades
                WHERE status = 'closed'
                AND date(entry_time) >= date('now', '-' || ? || ' days')
            """
            params = [days]
            
            if strategy_name:
                query += " AND strategy_name = ?"
                params.append(strategy_name)
            
            if account_id:
                query += " AND account_id = ?"
                params.append(account_id)
            
            query += " GROUP BY date(entry_time) ORDER BY date(entry_time)"
            
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            
            return [row['daily_pl'] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"❌ Failed to get daily returns: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            cursor = self.conn.cursor()
            
            stats = {}
            
            # Count trades
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            stats['total_trades'] = cursor.fetchone()['count']
            
            # Count snapshots
            cursor.execute("SELECT COUNT(*) as count FROM account_snapshots")
            stats['total_snapshots'] = cursor.fetchone()['count']
            
            # Count changes
            cursor.execute("SELECT COUNT(*) as count FROM strategy_changes")
            stats['total_changes'] = cursor.fetchone()['count']
            
            # Count metrics
            cursor.execute("SELECT COUNT(*) as count FROM strategy_metrics")
            stats['total_metrics'] = cursor.fetchone()['count']
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {}


