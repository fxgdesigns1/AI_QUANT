#!/usr/bin/env python3
"""
DASHBOARD SYNC MANAGER
=====================

Ensures all account data syncs with the main dashboard:
1. Real-time account updates
2. Semi-automatic trading integration
3. Trade assistant data sync
4. Performance metrics sync
5. Alert system integration
"""

import os
import sys
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import threading

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.yaml_manager import get_yaml_manager
from src.core.oanda_client import OandaClient
from src.analytics.trade_database import TradeDatabase
from src.analytics.metrics_calculator import MetricsCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DashboardSyncManager:
    """Manages synchronization between trading system and dashboard"""
    
    def __init__(self):
        self.sync_interval = 30  # 30 seconds
        self.is_running = False
        
        # Initialize components
        self.trade_db = TradeDatabase()
        self.metrics_calculator = MetricsCalculator()
        
        # Load accounts
        self.load_accounts()
        
        # Sync state
        self.last_sync_time = {}
        self.sync_errors = {}
        
    def load_accounts(self):
        """Load all trading accounts"""
        try:
            yaml_mgr = get_yaml_manager()
            self.accounts_config = yaml_mgr.get_all_accounts()
            logger.info(f"✅ Loaded {len(self.accounts_config)} accounts for dashboard sync")
        except Exception as e:
            logger.error(f"❌ Error loading accounts: {e}")
            self.accounts_config = []
    
    def sync_account_data(self, account_id: str) -> bool:
        """Sync data for a specific account"""
        try:
            # Get account info
            client = OandaClient(account_id=account_id)
            account_info = client.get_account_info()
            open_trades = client.get_open_trades()
            
            # Find account config
            account_config = None
            for acc in self.accounts_config:
                if acc['id'] == account_id:
                    account_config = acc
                    break
            
            if not account_config:
                logger.warning(f"⚠️ Account config not found for {account_id}")
                return False
            
            # Prepare sync data
            sync_data = {
                'account_id': account_id,
                'name': account_config.get('name', 'Unknown'),
                'strategy': account_config.get('strategy', 'unknown'),
                'balance': getattr(account_info, 'balance', 0),
                'currency': getattr(account_info, 'currency', 'USD'),
                'open_trades': len(open_trades),
                'trades': open_trades,
                'last_update': datetime.now().isoformat(),
                'status': 'ACTIVE' if account_config.get('active', False) else 'INACTIVE'
            }
            
            # Calculate P&L
            total_pnl = 0
            for trade in open_trades:
                total_pnl += float(trade.get('unrealizedPL', 0))
            sync_data['pnl'] = total_pnl
            
            # Save to database
            self.trade_db.save_account_snapshot(sync_data)
            
            # Update metrics
            self.metrics_calculator.update_account_metrics(account_id, sync_data)
            
            logger.info(f"✅ Synced {account_config.get('name', account_id)}: {total_pnl:.2f} P&L")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error syncing account {account_id}: {e}")
            self.sync_errors[account_id] = str(e)
            return False
    
    def sync_semi_automatic_system(self) -> bool:
        """Sync semi-automatic trading system data"""
        try:
            semi_auto_account_id = "101-004-30719775-001"  # Strategy Zeta
            
            # Get semi-auto account data
            client = OandaClient(account_id=semi_auto_account_id)
            account_info = client.get_account_info()
            open_trades = client.get_open_trades()
            
            # Prepare semi-auto specific data
            semi_auto_data = {
                'account_id': semi_auto_account_id,
                'name': 'Semi-Automatic Trading System',
                'strategy': 'semi_automatic',
                'balance': getattr(account_info, 'balance', 0),
                'currency': getattr(account_info, 'currency', 'USD'),
                'open_trades': len(open_trades),
                'trades': open_trades,
                'last_update': datetime.now().isoformat(),
                'status': 'ACTIVE',
                'system_type': 'semi_automatic',
                'ready_for_commands': True,
                'supported_instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY']
            }
            
            # Calculate P&L
            total_pnl = 0
            for trade in open_trades:
                total_pnl += float(trade.get('unrealizedPL', 0))
            semi_auto_data['pnl'] = total_pnl
            
            # Save to database
            self.trade_db.save_account_snapshot(semi_auto_data)
            
            # Update metrics
            self.metrics_calculator.update_account_metrics(semi_auto_account_id, semi_auto_data)
            
            logger.info(f"✅ Synced Semi-Automatic System: {total_pnl:.2f} P&L")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error syncing semi-automatic system: {e}")
            return False
    
    def sync_trade_assistant_data(self) -> bool:
        """Sync trade assistant data"""
        try:
            # Get all account data for trade assistant
            all_accounts_data = []
            
            for account in self.accounts_config:
                try:
                    client = OandaClient(account_id=account['id'])
                    account_info = client.get_account_info()
                    open_trades = client.get_open_trades()
                    
                    account_data = {
                        'account_id': account['id'],
                        'name': account.get('name', 'Unknown'),
                        'strategy': account.get('strategy', 'unknown'),
                        'balance': getattr(account_info, 'balance', 0),
                        'currency': getattr(account_info, 'currency', 'USD'),
                        'open_trades': len(open_trades),
                        'trades': open_trades,
                        'active': account.get('active', False)
                    }
                    
                    all_accounts_data.append(account_data)
                    
                except Exception as e:
                    logger.error(f"❌ Error getting data for {account['id']}: {e}")
                    continue
            
            # Prepare trade assistant data
            trade_assistant_data = {
                'timestamp': datetime.now().isoformat(),
                'total_accounts': len(all_accounts_data),
                'active_accounts': len([acc for acc in all_accounts_data if acc.get('active', False)]),
                'accounts': all_accounts_data,
                'system_status': 'OPERATIONAL',
                'last_update': datetime.now().isoformat()
            }
            
            # Save to database
            self.trade_db.save_trade_assistant_data(trade_assistant_data)
            
            logger.info(f"✅ Synced Trade Assistant: {len(all_accounts_data)} accounts")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error syncing trade assistant data: {e}")
            return False
    
    def sync_performance_metrics(self) -> bool:
        """Sync performance metrics for all accounts"""
        try:
            performance_data = {}
            
            for account in self.accounts_config:
                account_id = account['id']
                try:
                    # Get account performance
                    client = OandaClient(account_id=account_id)
                    account_info = client.get_account_info()
                    open_trades = client.get_open_trades()
                    
                    # Calculate metrics
                    total_pnl = sum(float(trade.get('unrealizedPL', 0)) for trade in open_trades)
                    win_rate = self.calculate_win_rate(open_trades)
                    sharpe_ratio = self.calculate_sharpe_ratio(account_id)
                    
                    performance_data[account_id] = {
                        'account_id': account_id,
                        'name': account.get('name', 'Unknown'),
                        'strategy': account.get('strategy', 'unknown'),
                        'balance': getattr(account_info, 'balance', 0),
                        'currency': getattr(account_info, 'currency', 'USD'),
                        'total_pnl': total_pnl,
                        'win_rate': win_rate,
                        'sharpe_ratio': sharpe_ratio,
                        'open_trades': len(open_trades),
                        'last_update': datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    logger.error(f"❌ Error calculating metrics for {account_id}: {e}")
                    continue
            
            # Save performance data
            self.trade_db.save_performance_metrics(performance_data)
            
            logger.info(f"✅ Synced performance metrics for {len(performance_data)} accounts")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error syncing performance metrics: {e}")
            return False
    
    def calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate from trades"""
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if float(trade.get('unrealizedPL', 0)) > 0)
        return winning_trades / len(trades) if trades else 0.0
    
    def calculate_sharpe_ratio(self, account_id: str) -> float:
        """Calculate Sharpe ratio for account"""
        try:
            # This would typically use historical data
            # For now, return a placeholder
            return 1.5  # Placeholder
        except Exception as e:
            logger.error(f"❌ Error calculating Sharpe ratio for {account_id}: {e}")
            return 0.0
    
    def run_sync_cycle(self):
        """Run one synchronization cycle"""
        logger.info("🔄 Running dashboard sync cycle...")
        
        sync_success = 0
        sync_total = 0
        
        # Sync all accounts
        for account in self.accounts_config:
            account_id = account['id']
            sync_total += 1
            
            if self.sync_account_data(account_id):
                sync_success += 1
                self.last_sync_time[account_id] = datetime.now()
        
        # Sync semi-automatic system
        if self.sync_semi_automatic_system():
            sync_success += 1
        
        # Sync trade assistant data
        if self.sync_trade_assistant_data():
            sync_success += 1
        
        # Sync performance metrics
        if self.sync_performance_metrics():
            sync_success += 1
        
        logger.info(f"✅ Sync complete: {sync_success}/{sync_total + 3} successful")
    
    def start_sync_manager(self):
        """Start the dashboard sync manager"""
        logger.info("🚀 Starting Dashboard Sync Manager...")
        self.is_running = True
        
        # Run sync loop
        while self.is_running:
            try:
                self.run_sync_cycle()
                time.sleep(self.sync_interval)
            except KeyboardInterrupt:
                logger.info("🛑 Stopping sync manager...")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"❌ Error in sync cycle: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def stop_sync_manager(self):
        """Stop the sync manager"""
        self.is_running = False
        logger.info("🛑 Sync manager stopped")

def main():
    """Main function"""
    logger.info("🤖 Starting Dashboard Sync Manager...")
    
    # Set up environment
    os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
    os.environ['OANDA_ENVIRONMENT'] = "practice"
    
    # Start sync manager
    sync_manager = DashboardSyncManager()
    sync_manager.start_sync_manager()

if __name__ == "__main__":
    main()

