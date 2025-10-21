#!/usr/bin/env python3
"""
Read-Only OANDA Data Collector
Fetches data from OANDA API without any trading actions
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.oanda_client import OandaClient
from analytics.database.models import PerformanceDatabase

logger = logging.getLogger(__name__)


class ReadOnlyOandaCollector:
    """
    Read-only data collector from OANDA API
    Collects trade history and account data without interfering with trading
    """
    
    def __init__(self, db: PerformanceDatabase):
        """Initialize read-only collector"""
        self.db = db
        
        # Get account IDs from environment
        self.accounts = {
            'PRIMARY': os.getenv('PRIMARY_ACCOUNT'),
            'GOLD_SCALP': os.getenv('GOLD_SCALP_ACCOUNT'),
            'STRATEGY_ALPHA': os.getenv('STRATEGY_ALPHA_ACCOUNT')
        }
        
        # Get strategy mappings
        self.strategy_mapping = {
            'PRIMARY': os.getenv('PRIMARY_STRATEGY', 'gold_scalping'),
            'GOLD_SCALP': os.getenv('GOLD_SCALP_STRATEGY', 'ultra_strict_forex'),
            'STRATEGY_ALPHA': os.getenv('STRATEGY_ALPHA_STRATEGY', 'momentum_trading')
        }
        
        # Initialize OANDA clients (read-only)
        self.clients = {}
        for name, account_id in self.accounts.items():
            if account_id:
                try:
                    self.clients[name] = OandaClient(
                        api_key=os.getenv('OANDA_API_KEY'),
                        account_id=account_id,
                        environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
                    )
                    logger.info(f"✅ Read-only client initialized for {name} ({account_id})")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize client for {name}: {e}")
        
        # Track last collection times
        self.last_trade_collection = {}
        self.last_snapshot_collection = {}
        
        logger.info(f"✅ ReadOnlyOandaCollector initialized for {len(self.clients)} accounts")
    
    def collect_all_data(self):
        """Collect all data types from all accounts"""
        try:
            logger.info("🔄 Starting data collection cycle...")
            
            for account_name in self.clients:
                try:
                    # Collect closed trades
                    self.collect_closed_trades(account_name)
                    
                    # Collect account snapshot
                    self.collect_account_snapshot(account_name)
                    
                    # Small delay between accounts
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to collect data for {account_name}: {e}")
            
            logger.info("✅ Data collection cycle completed")
            
        except Exception as e:
            logger.error(f"❌ Data collection cycle failed: {e}")
    
    def collect_closed_trades(self, account_name: str) -> int:
        """Collect closed trades from OANDA for an account"""
        try:
            if account_name not in self.clients:
                return 0
            
            client = self.clients[account_name]
            account_id = self.accounts[account_name]
            strategy_name = self.strategy_mapping[account_name]
            
            # Get trades since last collection (or last 7 days if first run)
            since = self.last_trade_collection.get(account_name)
            if not since:
                since = datetime.now() - timedelta(days=7)
            
            logger.info(f"📊 Collecting trades for {account_name} since {since}")
            
            # Fetch closed trades from OANDA
            try:
                response = client.api.transaction.list(
                    accountID=account_id,
                    from_time=since.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                )
                
                trades_collected = 0
                
                # Filter for ORDER_FILL transactions (completed trades)
                if hasattr(response, 'transactions'):
                    for txn in response.transactions:
                        if txn.type == 'ORDER_FILL':
                            # Convert to our trade format
                            trade_data = self._parse_oanda_trade(
                                txn, 
                                account_id, 
                                account_name, 
                                strategy_name
                            )
                            
                            if trade_data:
                                self.db.store_trade(trade_data)
                                trades_collected += 1
                
                # Update last collection time
                self.last_trade_collection[account_name] = datetime.now()
                
                logger.info(f"✅ Collected {trades_collected} trades for {account_name}")
                return trades_collected
                
            except Exception as e:
                logger.error(f"❌ OANDA API error for {account_name}: {e}")
                return 0
                
        except Exception as e:
            logger.error(f"❌ Failed to collect trades for {account_name}: {e}")
            return 0
    
    def collect_account_snapshot(self, account_name: str) -> bool:
        """Collect current account state snapshot"""
        try:
            if account_name not in self.clients:
                return False
            
            client = self.clients[account_name]
            account_id = self.accounts[account_name]
            
            # Get account summary from OANDA using client's method
            try:
                account_data = client.get_account_info()
                if not account_data:
                    return False
                
                account_info = {
                    'balance': account_data.balance,
                    'equity': account_data.balance + account_data.unrealized_pl,
                    'margin_used': account_data.margin_used,
                    'margin_available': account_data.margin_available,
                    'unrealized_pl': account_data.unrealized_pl
                }
            except Exception as e:
                logger.error(f"❌ Failed to get account info: {e}")
                return False
            
            if not account_info:
                return False
            
            # Get current positions and trades using client methods
            try:
                open_positions = client.get_open_positions() or []
            except Exception as e:
                logger.warning(f"Could not get open positions: {e}")
                open_positions = []
            
            try:
                open_trades = client.get_open_trades() or []
            except Exception as e:
                logger.warning(f"Could not get open trades: {e}")
                open_trades = []
            
            # Calculate metrics from recent trade history
            recent_trades = self.db.get_trades(
                account_id=account_id,
                status='closed',
                limit=100
            )
            
            # Calculate performance metrics
            metrics = self._calculate_snapshot_metrics(recent_trades)
            
            # Create snapshot data
            snapshot_data = {
                'snapshot_id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'account_id': account_id,
                'account_name': account_name,
                'balance': account_info.get('balance', 0.0),
                'equity': account_info.get('equity', 0.0),
                'margin_used': account_info.get('margin_used', 0.0),
                'margin_available': account_info.get('margin_available', 0.0),
                'unrealized_pl': account_info.get('unrealized_pl', 0.0),
                'open_positions': len(open_positions),
                'open_trades': len(open_trades),
                'pending_orders': 0,  # Would need separate API call
                **metrics
            }
            
            # Store snapshot
            self.db.store_snapshot(snapshot_data)
            
            # Update last collection time
            self.last_snapshot_collection[account_name] = datetime.now()
            
            logger.info(f"✅ Collected snapshot for {account_name} - Balance: ${account_info.get('balance', 0):,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to collect snapshot for {account_name}: {e}")
            return False
    
    def _parse_oanda_trade(self, 
                          transaction: Any, 
                          account_id: str, 
                          account_name: str,
                          strategy_name: str) -> Optional[Dict[str, Any]]:
        """Parse OANDA transaction into our trade format"""
        try:
            # Extract trade details
            trade_id = str(transaction.id)
            
            # Determine if this is entry or exit
            # Entry: positive units, Exit: negative units (or vice versa)
            units = int(transaction.units)
            side = 'BUY' if units > 0 else 'SELL'
            
            trade_data = {
                'trade_id': trade_id,
                'account_id': account_id,
                'account_name': account_name,
                'instrument': transaction.instrument,
                'strategy_name': strategy_name,
                'entry_time': transaction.time,
                'entry_price': float(transaction.price),
                'units': abs(units),
                'side': side,
                'entry_reason': transaction.reason if hasattr(transaction, 'reason') else 'OANDA_FILL',
                'status': 'closed',  # ORDER_FILL means completed
                # Additional fields would be populated by matching entry/exit
                'realized_pl': float(transaction.pl) if hasattr(transaction, 'pl') else 0.0,
                'commission': float(transaction.commission) if hasattr(transaction, 'commission') else 0.0,
            }
            
            # Calculate net P&L
            trade_data['net_pl'] = trade_data['realized_pl'] - trade_data['commission']
            
            return trade_data
            
        except Exception as e:
            logger.error(f"❌ Failed to parse transaction: {e}")
            return None
    
    def _calculate_snapshot_metrics(self, recent_trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate performance metrics from recent trades"""
        if not recent_trades:
            return {
                'daily_pl': 0.0,
                'daily_trades': 0,
                'daily_wins': 0,
                'daily_losses': 0,
                'total_trades': 0,
                'total_wins': 0,
                'total_losses': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'current_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'daily_return': 0.0,
                'weekly_return': 0.0,
                'monthly_return': 0.0,
                'ytd_return': 0.0
            }
        
        # Filter today's trades
        today = datetime.now().date()
        daily_trades = [t for t in recent_trades if datetime.fromisoformat(t['entry_time']).date() == today]
        
        # Calculate metrics
        total_trades = len(recent_trades)
        winning_trades = [t for t in recent_trades if t.get('net_pl', 0) > 0]
        losing_trades = [t for t in recent_trades if t.get('net_pl', 0) < 0]
        
        daily_wins = len([t for t in daily_trades if t.get('net_pl', 0) > 0])
        daily_losses = len([t for t in daily_trades if t.get('net_pl', 0) < 0])
        
        total_pl = sum(t.get('net_pl', 0) for t in recent_trades)
        daily_pl = sum(t.get('net_pl', 0) for t in daily_trades)
        
        gross_profit = sum(t.get('net_pl', 0) for t in winning_trades)
        gross_loss = abs(sum(t.get('net_pl', 0) for t in losing_trades))
        
        metrics = {
            'daily_pl': daily_pl,
            'daily_trades': len(daily_trades),
            'daily_wins': daily_wins,
            'daily_losses': daily_losses,
            'total_trades': total_trades,
            'total_wins': len(winning_trades),
            'total_losses': len(losing_trades),
            'win_rate': (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0,
            'avg_win': (gross_profit / len(winning_trades)) if winning_trades else 0.0,
            'avg_loss': (gross_loss / len(losing_trades)) if losing_trades else 0.0,
            'profit_factor': (gross_profit / gross_loss) if gross_loss > 0 else 0.0,
            'max_drawdown': 0.0,  # Would need equity curve
            'max_drawdown_pct': 0.0,
            'current_drawdown': 0.0,
            'sharpe_ratio': 0.0,  # Would need returns series
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'daily_return': 0.0,
            'weekly_return': 0.0,
            'monthly_return': 0.0,
            'ytd_return': 0.0
        }
        
        return metrics
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get status of data collection"""
        return {
            'accounts': list(self.clients.keys()),
            'last_trade_collection': {
                name: time.isoformat() if (time := self.last_trade_collection.get(name)) else None
                for name in self.clients
            },
            'last_snapshot_collection': {
                name: time.isoformat() if (time := self.last_snapshot_collection.get(name)) else None
                for name in self.clients
            },
            'database_stats': self.db.get_database_stats()
        }


def main():
    """Test the collector"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('oanda_config.env')
    
    # Initialize database
    db = PerformanceDatabase()
    
    # Initialize collector
    collector = ReadOnlyOandaCollector(db)
    
    # Collect data
    collector.collect_all_data()
    
    # Show status
    status = collector.get_collection_status()
    print("\n" + "="*60)
    print("COLLECTION STATUS")
    print("="*60)
    print(f"Accounts: {', '.join(status['accounts'])}")
    print(f"\nDatabase Stats:")
    for key, value in status['database_stats'].items():
        print(f"  {key}: {value}")
    print("="*60)


if __name__ == '__main__':
    main()

