#!/usr/bin/env python3
"""
Multi-Strategy Testing Framework - Data Collector
Comprehensive data collection system for market data, trade execution, and performance metrics
"""

import os
import json
import logging
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import queue
import csv

from .multi_account_data_feed import get_multi_account_data_feed
from .dynamic_account_manager import get_account_manager
from .strategy_manager import get_strategy_manager
from .strategy_executor import get_multi_strategy_executor
from .telegram_notifier import TelegramNotifier

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataType(Enum):
    """Types of data being collected"""
    MARKET_DATA = "market_data"
    TRADE_DATA = "trade_data"
    SIGNAL_DATA = "signal_data"
    PERFORMANCE_DATA = "performance_data"
    NEWS_DATA = "news_data"
    RISK_DATA = "risk_data"

@dataclass
class MarketDataPoint:
    """Market data point for collection"""
    timestamp: datetime
    instrument: str
    bid: float
    ask: float
    spread: float
    volume: Optional[float]
    session: str
    volatility: float
    account_id: str

@dataclass
class TradeDataPoint:
    """Trade execution data point"""
    timestamp: datetime
    strategy_id: str
    account_id: str
    instrument: str
    side: str
    units: int
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    execution_time: float
    order_id: str
    status: str

@dataclass
class SignalDataPoint:
    """Signal generation data point"""
    timestamp: datetime
    strategy_id: str
    instrument: str
    signal_type: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    executed: bool
    execution_delay: float

@dataclass
class PerformanceDataPoint:
    """Performance metrics data point"""
    timestamp: datetime
    strategy_id: str
    account_id: str
    balance: float
    unrealized_pl: float
    realized_pl: float
    total_pnl: float
    margin_used: float
    margin_available: float
    open_positions: int
    daily_return: float
    monthly_return: float

class DataCollector:
    """Comprehensive data collection system"""
    
    def __init__(self, db_path: str = "trading_data.db"):
        """Initialize data collector"""
        self.db_path = db_path
        self.multi_data_feed = get_multi_account_data_feed()
        self.account_manager = get_account_manager()
        self.strategy_manager = get_strategy_manager()
        self.multi_executor = get_multi_strategy_executor()
        self.telegram_notifier = TelegramNotifier()
        
        # Collection state
        self.is_collecting = False
        self.collection_threads: Dict[str, threading.Thread] = {}
        self.data_queues: Dict[str, queue.Queue] = {}
        
        # Database
        self.db_connection = None
        self._initialize_database()
        
        # Data storage
        self.market_data_buffer: List[MarketDataPoint] = []
        self.trade_data_buffer: List[TradeDataPoint] = []
        self.signal_data_buffer: List[SignalDataPoint] = []
        self.performance_data_buffer: List[PerformanceDataPoint] = []
        
        # Collection intervals
        self.collection_intervals = {
            DataType.MARKET_DATA: 5,      # 5 seconds
            DataType.TRADE_DATA: 1,       # 1 second
            DataType.SIGNAL_DATA: 1,      # 1 second
            DataType.PERFORMANCE_DATA: 30, # 30 seconds
            DataType.RISK_DATA: 60        # 1 minute
        }
        
        logger.info("📊 Data Collector initialized")
    
    def _initialize_database(self):
        """Initialize SQLite database for data storage"""
        try:
            self.db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.db_connection.cursor()
            
            # Create tables for different data types
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    spread REAL NOT NULL,
                    volume REAL,
                    session TEXT,
                    volatility REAL,
                    account_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    side TEXT NOT NULL,
                    units INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    confidence REAL NOT NULL,
                    execution_time REAL,
                    order_id TEXT,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    executed BOOLEAN NOT NULL,
                    execution_delay REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    balance REAL NOT NULL,
                    unrealized_pl REAL NOT NULL,
                    realized_pl REAL NOT NULL,
                    total_pnl REAL NOT NULL,
                    margin_used REAL NOT NULL,
                    margin_available REAL NOT NULL,
                    open_positions INTEGER NOT NULL,
                    daily_return REAL NOT NULL,
                    monthly_return REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    impact TEXT,
                    currency_pairs TEXT,
                    source TEXT,
                    url TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_data_timestamp ON trade_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signal_data_timestamp ON signal_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_data_timestamp ON performance_data(timestamp)')
            
            self.db_connection.commit()
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
    
    def start_collection(self):
        """Start comprehensive data collection"""
        if self.is_collecting:
            logger.warning("Data collection already running")
            return
        
        self.is_collecting = True
        
        # Start collection threads for each data type
        for data_type in DataType:
            queue_name = data_type.value
            self.data_queues[queue_name] = queue.Queue()
            
            thread = threading.Thread(
                target=self._collection_loop,
                args=(data_type,),
                daemon=True
            )
            thread.start()
            self.collection_threads[queue_name] = thread
        
        logger.info("🚀 Data collection started")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_message(
                "📊 Data Collection Started\n"
                f"🗄️ Database: {self.db_path}\n"
                f"📈 Data Types: {len(DataType)}\n"
                "🔄 Real-time collection active"
            )
    
    def stop_collection(self):
        """Stop data collection"""
        self.is_collecting = False
        
        # Wait for threads to finish
        for thread in self.collection_threads.values():
            thread.join(timeout=5)
        
        # Close database connection
        if self.db_connection:
            self.db_connection.close()
        
        logger.info("🛑 Data collection stopped")
    
    def _collection_loop(self, data_type: DataType):
        """Main collection loop for specific data type"""
        while self.is_collecting:
            try:
                if data_type == DataType.MARKET_DATA:
                    self._collect_market_data()
                elif data_type == DataType.TRADE_DATA:
                    self._collect_trade_data()
                elif data_type == DataType.SIGNAL_DATA:
                    self._collect_signal_data()
                elif data_type == DataType.PERFORMANCE_DATA:
                    self._collect_performance_data()
                elif data_type == DataType.NEWS_DATA:
                    self._collect_news_data()
                elif data_type == DataType.RISK_DATA:
                    self._collect_risk_data()
                
                # Sleep for collection interval
                time.sleep(self.collection_intervals[data_type])
                
            except Exception as e:
                logger.error(f"❌ Error collecting {data_type.value}: {e}")
                time.sleep(60)
    
    def _collect_market_data(self):
        """Collect market data from all accounts"""
        try:
            # Get all market data
            all_market_data = self.multi_data_feed.get_all_market_data()
            
            for account_id, market_data in all_market_data.items():
                for instrument, data in market_data.items():
                    # Determine trading session
                    session = self._get_current_session()
                    
                    # Calculate volatility (simplified)
                    volatility = self._calculate_volatility(data.bid, data.ask)
                    
                    data_point = MarketDataPoint(
                        timestamp=datetime.now(),
                        instrument=instrument,
                        bid=data.bid,
                        ask=data.ask,
                        spread=data.spread,
                        volume=None,  # Not available in current data feed
                        session=session,
                        volatility=volatility,
                        account_id=account_id
                    )
                    
                    self.market_data_buffer.append(data_point)
                    
                    # Store in database
                    self._store_market_data(data_point)
            
            # Keep buffer size manageable
            if len(self.market_data_buffer) > 1000:
                self.market_data_buffer = self.market_data_buffer[-500:]
                
        except Exception as e:
            logger.error(f"❌ Failed to collect market data: {e}")
    
    def _collect_trade_data(self):
        """Collect trade execution data"""
        try:
            # Get execution data from all executors
            execution_status = self.multi_executor.get_all_execution_status()
            
            for strategy_id, executor_data in execution_status.get('executors', {}).items():
                # Get recent trades from executor
                trade_log = executor_data.get('metrics', {}).get('trade_log', [])
                
                for trade in trade_log[-10:]:  # Last 10 trades
                    if trade.get('processed', False):
                        continue
                    
                    signal_data = trade.get('signal', {})
                    order_result = trade.get('order_result', {})
                    
                    data_point = TradeDataPoint(
                        timestamp=datetime.fromisoformat(trade['timestamp']),
                        strategy_id=strategy_id,
                        account_id=executor_data.get('account_id', ''),
                        instrument=signal_data.get('instrument', ''),
                        side=signal_data.get('side', ''),
                        units=signal_data.get('units', 0),
                        entry_price=signal_data.get('entry_price', 0.0),
                        stop_loss=signal_data.get('stop_loss', 0.0),
                        take_profit=signal_data.get('take_profit', 0.0),
                        confidence=signal_data.get('confidence', 0.0),
                        execution_time=trade.get('execution_time', 0.0),
                        order_id=order_result.get('order_id', ''),
                        status='executed'
                    )
                    
                    self.trade_data_buffer.append(data_point)
                    
                    # Store in database
                    self._store_trade_data(data_point)
                    
                    # Mark as processed
                    trade['processed'] = True
            
        except Exception as e:
            logger.error(f"❌ Failed to collect trade data: {e}")
    
    def _collect_signal_data(self):
        """Collect signal generation data"""
        try:
            # Get signal data from all executors
            execution_status = self.multi_executor.get_all_execution_status()
            
            for strategy_id, executor_data in execution_status.get('executors', {}).items():
                # Get recent signals from executor
                signal_log = executor_data.get('metrics', {}).get('signal_log', [])
                
                for signal in signal_log[-10:]:  # Last 10 signals
                    if signal.get('processed', False):
                        continue
                    
                    signal_data = signal.get('signal', {})
                    
                    data_point = SignalDataPoint(
                        timestamp=datetime.fromisoformat(signal['timestamp']),
                        strategy_id=strategy_id,
                        instrument=signal_data.get('instrument', ''),
                        signal_type=signal_data.get('side', ''),
                        confidence=signal_data.get('confidence', 0.0),
                        entry_price=signal_data.get('entry_price', 0.0),
                        stop_loss=signal_data.get('stop_loss', 0.0),
                        take_profit=signal_data.get('take_profit', 0.0),
                        executed=signal_data.get('executed', False),
                        execution_delay=0.0  # Calculate if needed
                    )
                    
                    self.signal_data_buffer.append(data_point)
                    
                    # Store in database
                    self._store_signal_data(data_point)
                    
                    # Mark as processed
                    signal['processed'] = True
            
        except Exception as e:
            logger.error(f"❌ Failed to collect signal data: {e}")
    
    def _collect_performance_data(self):
        """Collect performance metrics data"""
        try:
            # Get account performance data
            active_accounts = self.account_manager.get_active_accounts()
            
            for account_id in active_accounts:
                account_info = self.account_manager.get_account_info(account_id)
                if not account_info:
                    continue
                
                # Get strategy for this account
                strategy_id = None
                for sid, config in self.strategy_manager.strategies.items():
                    if config.account_id == account_id:
                        strategy_id = sid
                        break
                
                if not strategy_id:
                    continue
                
                # Calculate returns (simplified)
                daily_return = 0.0  # Calculate based on previous day
                monthly_return = (account_info.unrealized_pl + account_info.realized_pl) / account_info.balance * 100 if account_info.balance > 0 else 0.0
                
                data_point = PerformanceDataPoint(
                    timestamp=datetime.now(),
                    strategy_id=strategy_id,
                    account_id=account_id,
                    balance=account_info.balance,
                    unrealized_pl=account_info.unrealized_pl,
                    realized_pl=account_info.realized_pl,
                    total_pnl=account_info.unrealized_pl + account_info.realized_pl,
                    margin_used=account_info.margin_used,
                    margin_available=account_info.margin_available,
                    open_positions=account_info.open_position_count,
                    daily_return=daily_return,
                    monthly_return=monthly_return
                )
                
                self.performance_data_buffer.append(data_point)
                
                # Store in database
                self._store_performance_data(data_point)
            
        except Exception as e:
            logger.error(f"❌ Failed to collect performance data: {e}")
    
    def _collect_news_data(self):
        """Collect news and market sentiment data"""
        try:
            # Mock news data - in real implementation, integrate with news API
            news_items = [
                {
                    'title': 'Fed Signals Potential Rate Cut',
                    'summary': 'USD weakness expected, Gold bullish',
                    'impact': 'high',
                    'currency_pairs': 'USD, XAU',
                    'source': 'Reuters',
                    'url': 'https://example.com/news1'
                },
                {
                    'title': 'ECB Maintains Current Policy',
                    'summary': 'EUR stability, range-bound trading',
                    'impact': 'medium',
                    'currency_pairs': 'EUR',
                    'source': 'Bloomberg',
                    'url': 'https://example.com/news2'
                }
            ]
            
            for news in news_items:
                self._store_news_data(news)
                
        except Exception as e:
            logger.error(f"❌ Failed to collect news data: {e}")
    
    def _collect_risk_data(self):
        """Collect risk management data"""
        try:
            # Collect risk metrics from all strategies
            execution_status = self.multi_executor.get_all_execution_status()
            
            for strategy_id, executor_data in execution_status.get('executors', {}).items():
                # Log risk violations
                risk_violations = executor_data.get('metrics', {}).get('risk_violations', 0)
                if risk_violations > 0:
                    logger.warning(f"⚠️ Risk violations detected for {strategy_id}: {risk_violations}")
            
        except Exception as e:
            logger.error(f"❌ Failed to collect risk data: {e}")
    
    def _get_current_session(self) -> str:
        """Get current trading session"""
        current_hour = datetime.now().hour
        
        if 0 <= current_hour < 9:
            return "Tokyo"
        elif 8 <= current_hour < 17:
            return "London"
        elif 13 <= current_hour < 22:
            return "New York"
        else:
            return "Overlap"
    
    def _calculate_volatility(self, bid: float, ask: float) -> float:
        """Calculate simplified volatility"""
        try:
            # Use spread as a proxy for volatility
            spread = ask - bid
            mid_price = (bid + ask) / 2
            return (spread / mid_price) * 10000  # Convert to pips
            
        except Exception:
            return 0.0
    
    def _store_market_data(self, data_point: MarketDataPoint):
        """Store market data in database"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO market_data 
                (timestamp, instrument, bid, ask, spread, volume, session, volatility, account_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data_point.timestamp.isoformat(),
                data_point.instrument,
                data_point.bid,
                data_point.ask,
                data_point.spread,
                data_point.volume,
                data_point.session,
                data_point.volatility,
                data_point.account_id
            ))
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to store market data: {e}")
    
    def _store_trade_data(self, data_point: TradeDataPoint):
        """Store trade data in database"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO trade_data 
                (timestamp, strategy_id, account_id, instrument, side, units, entry_price, 
                 stop_loss, take_profit, confidence, execution_time, order_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data_point.timestamp.isoformat(),
                data_point.strategy_id,
                data_point.account_id,
                data_point.instrument,
                data_point.side,
                data_point.units,
                data_point.entry_price,
                data_point.stop_loss,
                data_point.take_profit,
                data_point.confidence,
                data_point.execution_time,
                data_point.order_id,
                data_point.status
            ))
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to store trade data: {e}")
    
    def _store_signal_data(self, data_point: SignalDataPoint):
        """Store signal data in database"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO signal_data 
                (timestamp, strategy_id, instrument, signal_type, confidence, entry_price, 
                 stop_loss, take_profit, executed, execution_delay)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data_point.timestamp.isoformat(),
                data_point.strategy_id,
                data_point.instrument,
                data_point.signal_type,
                data_point.confidence,
                data_point.entry_price,
                data_point.stop_loss,
                data_point.take_profit,
                data_point.executed,
                data_point.execution_delay
            ))
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to store signal data: {e}")
    
    def _store_performance_data(self, data_point: PerformanceDataPoint):
        """Store performance data in database"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO performance_data 
                (timestamp, strategy_id, account_id, balance, unrealized_pl, realized_pl, 
                 total_pnl, margin_used, margin_available, open_positions, daily_return, monthly_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data_point.timestamp.isoformat(),
                data_point.strategy_id,
                data_point.account_id,
                data_point.balance,
                data_point.unrealized_pl,
                data_point.realized_pl,
                data_point.total_pnl,
                data_point.margin_used,
                data_point.margin_available,
                data_point.open_positions,
                data_point.daily_return,
                data_point.monthly_return
            ))
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to store performance data: {e}")
    
    def _store_news_data(self, news_data: Dict[str, Any]):
        """Store news data in database"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO news_data 
                (timestamp, title, summary, impact, currency_pairs, source, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                news_data['title'],
                news_data.get('summary', ''),
                news_data.get('impact', 'low'),
                news_data.get('currency_pairs', ''),
                news_data.get('source', ''),
                news_data.get('url', '')
            ))
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to store news data: {e}")
    
    def export_data_for_backtesting(self, start_date: datetime, end_date: datetime, 
                                   output_format: str = "json") -> str:
        """Export collected data for backtesting integration"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if output_format.lower() == "json":
                filename = f"backtesting_data_export_{timestamp}.json"
                self._export_json_data(start_date, end_date, filename)
            elif output_format.lower() == "csv":
                filename = f"backtesting_data_export_{timestamp}.csv"
                self._export_csv_data(start_date, end_date, filename)
            else:
                raise ValueError(f"Unsupported format: {output_format}")
            
            logger.info(f"📊 Data exported for backtesting: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to export data: {e}")
            return ""
    
    def _export_json_data(self, start_date: datetime, end_date: datetime, filename: str):
        """Export data in JSON format"""
        try:
            cursor = self.db_connection.cursor()
            
            export_data = {
                'export_info': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'export_timestamp': datetime.now().isoformat(),
                    'total_records': 0
                },
                'market_data': [],
                'trade_data': [],
                'signal_data': [],
                'performance_data': []
            }
            
            # Export market data
            cursor.execute('''
                SELECT * FROM market_data 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            market_records = cursor.fetchall()
            for record in market_records:
                export_data['market_data'].append({
                    'timestamp': record[1],
                    'instrument': record[2],
                    'bid': record[3],
                    'ask': record[4],
                    'spread': record[5],
                    'session': record[7],
                    'volatility': record[8],
                    'account_id': record[9]
                })
            
            # Export trade data
            cursor.execute('''
                SELECT * FROM trade_data 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            trade_records = cursor.fetchall()
            for record in trade_records:
                export_data['trade_data'].append({
                    'timestamp': record[1],
                    'strategy_id': record[2],
                    'account_id': record[3],
                    'instrument': record[4],
                    'side': record[5],
                    'units': record[6],
                    'entry_price': record[7],
                    'stop_loss': record[8],
                    'take_profit': record[9],
                    'confidence': record[10],
                    'execution_time': record[11],
                    'order_id': record[12]
                })
            
            # Export signal data
            cursor.execute('''
                SELECT * FROM signal_data 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            signal_records = cursor.fetchall()
            for record in signal_records:
                export_data['signal_data'].append({
                    'timestamp': record[1],
                    'strategy_id': record[2],
                    'instrument': record[3],
                    'signal_type': record[4],
                    'confidence': record[5],
                    'entry_price': record[6],
                    'stop_loss': record[7],
                    'take_profit': record[8],
                    'executed': record[9],
                    'execution_delay': record[10]
                })
            
            # Export performance data
            cursor.execute('''
                SELECT * FROM performance_data 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            performance_records = cursor.fetchall()
            for record in performance_records:
                export_data['performance_data'].append({
                    'timestamp': record[1],
                    'strategy_id': record[2],
                    'account_id': record[3],
                    'balance': record[4],
                    'unrealized_pl': record[5],
                    'realized_pl': record[6],
                    'total_pnl': record[7],
                    'margin_used': record[8],
                    'margin_available': record[9],
                    'open_positions': record[10],
                    'daily_return': record[11],
                    'monthly_return': record[12]
                })
            
            export_data['export_info']['total_records'] = (
                len(market_records) + len(trade_records) + 
                len(signal_records) + len(performance_records)
            )
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"❌ Failed to export JSON data: {e}")
    
    def _export_csv_data(self, start_date: datetime, end_date: datetime, filename: str):
        """Export data in CSV format"""
        try:
            cursor = self.db_connection.cursor()
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write market data
                writer.writerow(['Data Type', 'Market Data'])
                writer.writerow(['timestamp', 'instrument', 'bid', 'ask', 'spread', 'session', 'volatility', 'account_id'])
                
                cursor.execute('''
                    SELECT timestamp, instrument, bid, ask, spread, session, volatility, account_id
                    FROM market_data 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                for record in cursor.fetchall():
                    writer.writerow(['market_data'] + list(record))
                
                # Write trade data
                writer.writerow([])
                writer.writerow(['Data Type', 'Trade Data'])
                writer.writerow(['timestamp', 'strategy_id', 'account_id', 'instrument', 'side', 'units', 'entry_price', 'stop_loss', 'take_profit', 'confidence'])
                
                cursor.execute('''
                    SELECT timestamp, strategy_id, account_id, instrument, side, units, entry_price, stop_loss, take_profit, confidence
                    FROM trade_data 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                for record in cursor.fetchall():
                    writer.writerow(['trade_data'] + list(record))
                
        except Exception as e:
            logger.error(f"❌ Failed to export CSV data: {e}")
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get data collection status"""
        try:
            # Get database statistics
            cursor = self.db_connection.cursor()
            
            table_counts = {}
            for table in ['market_data', 'trade_data', 'signal_data', 'performance_data', 'news_data']:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                table_counts[table] = cursor.fetchone()[0]
            
            return {
                'is_collecting': self.is_collecting,
                'collection_threads': len(self.collection_threads),
                'data_queues': len(self.data_queues),
                'database_path': self.db_path,
                'table_counts': table_counts,
                'buffer_sizes': {
                    'market_data': len(self.market_data_buffer),
                    'trade_data': len(self.trade_data_buffer),
                    'signal_data': len(self.signal_data_buffer),
                    'performance_data': len(self.performance_data_buffer)
                },
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get collection status: {e}")
            return {}

# Global data collector instance
data_collector = DataCollector()

def get_data_collector() -> DataCollector:
    """Get the global data collector instance"""
    return data_collector

