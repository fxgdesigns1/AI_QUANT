#!/usr/bin/env python3
"""
Performance Tracker - Historical Strategy Performance Storage
Tracks strategy performance over time with SQLite database
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Track and store strategy performance history"""
    
    def __init__(self, db_path: str = "/tmp/performance_history.db"):
        """Initialize performance tracker with SQLite database"""
        self.db_path = db_path
        self._init_database()
        logger.info(f"✅ Performance tracker initialized: {db_path}")
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Strategy snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                account_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                display_name TEXT,
                balance REAL,
                nav REAL,
                pl REAL,
                unrealized_pl REAL,
                trade_count INTEGER DEFAULT 0,
                open_positions INTEGER DEFAULT 0,
                win_rate REAL,
                pairs TEXT,
                timeframe TEXT,
                daily_limit INTEGER,
                status TEXT
            )
        """)
        
        # Trade history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                account_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                instrument TEXT,
                direction TEXT,
                units REAL,
                entry_price REAL,
                exit_price REAL,
                pl REAL,
                pips REAL
            )
        """)
        
        # Daily summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                account_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                start_balance REAL,
                end_balance REAL,
                daily_pl REAL,
                trades_count INTEGER,
                wins INTEGER,
                losses INTEGER,
                win_rate REAL,
                UNIQUE(date, account_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_account ON strategy_snapshots(account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON strategy_snapshots(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_account ON trade_history(account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_account ON daily_summary(account_id, date)")
        
        conn.commit()
        conn.close()
    
    def capture_snapshot(self, account_data: Dict[str, Any]):
        """Capture current performance snapshot"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO strategy_snapshots (
                    account_id, strategy_name, display_name, balance, nav, pl, 
                    unrealized_pl, trade_count, open_positions, win_rate, 
                    pairs, timeframe, daily_limit, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_data.get('account_id'),
                account_data.get('strategy_name'),
                account_data.get('display_name'),
                account_data.get('balance', 0),
                account_data.get('nav', 0),
                account_data.get('pl', 0),
                account_data.get('unrealized_pl', 0),
                account_data.get('trade_count', 0),
                account_data.get('open_positions', 0),
                account_data.get('win_rate', 0),
                account_data.get('pairs', ''),
                account_data.get('timeframe', ''),
                account_data.get('daily_limit', 0),
                account_data.get('status', 'unknown')
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"📸 Snapshot captured: {account_data.get('display_name')}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to capture snapshot: {e}")
            return False
    
    def get_strategy_history(self, account_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical performance data for a strategy"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT timestamp, balance, nav, pl, unrealized_pl, trade_count, 
                       open_positions, win_rate, status
                FROM strategy_snapshots
                WHERE account_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (account_id, cutoff_date))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                history.append({
                    'timestamp': row[0],
                    'balance': row[1],
                    'nav': row[2],
                    'pl': row[3],
                    'unrealized_pl': row[4],
                    'trade_count': row[5],
                    'open_positions': row[6],
                    'win_rate': row[7],
                    'status': row[8]
                })
            
            return history
        except Exception as e:
            logger.error(f"❌ Failed to get history for {account_id}: {e}")
            return []
    
    def get_latest_snapshots(self) -> List[Dict[str, Any]]:
        """Get latest snapshot for each strategy"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s1.*
                FROM strategy_snapshots s1
                INNER JOIN (
                    SELECT account_id, MAX(timestamp) as max_timestamp
                    FROM strategy_snapshots
                    GROUP BY account_id
                ) s2 ON s1.account_id = s2.account_id AND s1.timestamp = s2.max_timestamp
                ORDER BY s1.pl DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            snapshots = []
            for row in rows:
                snapshots.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'account_id': row[2],
                    'strategy_name': row[3],
                    'display_name': row[4],
                    'balance': row[5],
                    'nav': row[6],
                    'pl': row[7],
                    'unrealized_pl': row[8],
                    'trade_count': row[9],
                    'open_positions': row[10],
                    'win_rate': row[11],
                    'pairs': row[12],
                    'timeframe': row[13],
                    'daily_limit': row[14],
                    'status': row[15]
                })
            
            return snapshots
        except Exception as e:
            logger.error(f"❌ Failed to get latest snapshots: {e}")
            return []
    
    def get_comparison_data(self, account_ids: List[str], days: int = 7) -> Dict[str, Any]:
        """Get comparison data for multiple strategies"""
        comparison = {}
        
        for account_id in account_ids:
            history = self.get_strategy_history(account_id, days)
            if history:
                comparison[account_id] = {
                    'start_pl': history[0]['pl'] if history else 0,
                    'end_pl': history[-1]['pl'] if history else 0,
                    'change': (history[-1]['pl'] - history[0]['pl']) if len(history) > 1 else 0,
                    'history': history
                }
        
        return comparison
    
    def record_trade(self, trade_data: Dict[str, Any]):
        """Record a completed trade"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trade_history (
                    account_id, strategy_name, instrument, direction, 
                    units, entry_price, exit_price, pl, pips
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get('account_id'),
                trade_data.get('strategy_name'),
                trade_data.get('instrument'),
                trade_data.get('direction'),
                trade_data.get('units', 0),
                trade_data.get('entry_price', 0),
                trade_data.get('exit_price', 0),
                trade_data.get('pl', 0),
                trade_data.get('pips', 0)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to record trade: {e}")
            return False
    
    def update_daily_summary(self, account_id: str, strategy_name: str, 
                            start_balance: float, end_balance: float,
                            trades_count: int, wins: int, losses: int):
        """Update daily summary for a strategy"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date = datetime.now().date()
            daily_pl = end_balance - start_balance
            win_rate = (wins / trades_count * 100) if trades_count > 0 else 0
            
            cursor.execute("""
                INSERT OR REPLACE INTO daily_summary (
                    date, account_id, strategy_name, start_balance, end_balance,
                    daily_pl, trades_count, wins, losses, win_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date, account_id, strategy_name, start_balance, end_balance,
                  daily_pl, trades_count, wins, losses, win_rate))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update daily summary: {e}")
            return False
    
    def get_daily_summary(self, account_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily summary history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now().date() - timedelta(days=days)
            
            cursor.execute("""
                SELECT date, start_balance, end_balance, daily_pl, trades_count,
                       wins, losses, win_rate
                FROM daily_summary
                WHERE account_id = ? AND date >= ?
                ORDER BY date ASC
            """, (account_id, cutoff_date))
            
            rows = cursor.fetchall()
            conn.close()
            
            summary = []
            for row in rows:
                summary.append({
                    'date': row[0],
                    'start_balance': row[1],
                    'end_balance': row[2],
                    'daily_pl': row[3],
                    'trades_count': row[4],
                    'wins': row[5],
                    'losses': row[6],
                    'win_rate': row[7]
                })
            
            return summary
        except Exception as e:
            logger.error(f"❌ Failed to get daily summary: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up data older than specified days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("DELETE FROM strategy_snapshots WHERE timestamp < ?", (cutoff_date,))
            cursor.execute("DELETE FROM trade_history WHERE timestamp < ?", (cutoff_date,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"🗑️ Cleaned up {deleted} old records")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old data: {e}")
            return False


# Singleton instance
_performance_tracker = None

def get_performance_tracker() -> PerformanceTracker:
    """Get singleton performance tracker instance"""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker

