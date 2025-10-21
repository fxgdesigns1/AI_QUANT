#!/usr/bin/env python3
"""
Adaptive System Integration
Integrates the adaptive system with existing OANDA accounts and strategies
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List
import logging

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from .oanda_client import OandaClient
from .telegram_notifier import TelegramNotifier
from .adaptive_system import AdaptiveTradingSystem, MarketCondition, AdaptationLevel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdaptiveAccountManager:
    """Manages adaptive system for all OANDA accounts"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.path.join(BASE_DIR, 'oanda_config.env')
        self.load_dotenv(self.config_file)
        
        # Initialize OANDA clients
        self.oanda_clients = self._initialize_oanda_clients()
        
        # Initialize Telegram notifier
        self.telegram_notifier = self._initialize_telegram_notifier()
        
        # Initialize adaptive system
        self.adaptive_system = AdaptiveTradingSystem(
            self.oanda_clients, 
            self.telegram_notifier
        )
        
        logger.info("🔗 Adaptive Account Manager initialized")
    
    def load_dotenv(self, file_path: str):
        """Load environment variables from file"""
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        except Exception as e:
            logger.error(f"❌ Failed to load environment file: {e}")
            raise
    
    def _initialize_oanda_clients(self) -> Dict[str, OandaClient]:
        """Initialize OANDA clients for all accounts"""
        clients = {}
        
        # Account configurations
        accounts = {
            'PRIMARY': os.getenv('PRIMARY_ACCOUNT'),
            'GOLD': os.getenv('GOLD_SCALP_ACCOUNT'),
            'ALPHA': os.getenv('STRATEGY_ALPHA_ACCOUNT')
        }
        
        api_key = os.getenv('OANDA_API_KEY')
        environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
        
        if not api_key:
            raise ValueError("OANDA_API_KEY not found in environment")
        
        for account_name, account_id in accounts.items():
            if not account_id:
                logger.warning(f"⚠️ No account ID found for {account_name}")
                continue
            
            try:
                client = OandaClient(
                    api_key=api_key,
                    account_id=account_id,
                    environment=environment
                )
                
                # Test connection
                if client.is_connected():
                    clients[account_name] = client
                    logger.info(f"✅ {account_name} client initialized: {account_id}")
                else:
                    logger.error(f"❌ Failed to connect to {account_name}: {account_id}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to initialize {account_name}: {e}")
        
        if not clients:
            raise ValueError("No OANDA clients could be initialized")
        
        return clients
    
    def _initialize_telegram_notifier(self) -> TelegramNotifier:
        """Initialize Telegram notifier"""
        try:
            token = os.getenv('TELEGRAM_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if token and chat_id:
                notifier = TelegramNotifier(token, chat_id)
                logger.info("✅ Telegram notifier initialized")
                return notifier
            else:
                logger.warning("⚠️ Telegram credentials not found")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram notifier: {e}")
            return None
    
    def start_adaptive_monitoring(self):
        """Start adaptive monitoring for all accounts"""
        try:
            self.adaptive_system.start_monitoring()
            
            # Send startup notification
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    "🤖 ADAPTIVE TRADING SYSTEM STARTED\n\n"
                    f"📊 Monitoring {len(self.oanda_clients)} accounts:\n"
                    f"• PRIMARY (Ultra Strict Forex)\n"
                    f"• GOLD (Gold Scalping)\n"
                    f"• ALPHA (Momentum Trading)\n\n"
                    f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"🔍 Market conditions: Real-time monitoring\n"
                    f"🛡️ Risk management: Automatic adaptations"
                )
            
            logger.info("🚀 Adaptive monitoring started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start adaptive monitoring: {e}")
            raise
    
    def stop_adaptive_monitoring(self):
        """Stop adaptive monitoring"""
        try:
            self.adaptive_system.stop_monitoring()
            
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    "🛑 ADAPTIVE TRADING SYSTEM STOPPED\n\n"
                    f"⏰ Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"📊 System status: Monitoring disabled"
                )
            
            logger.info("🛑 Adaptive monitoring stopped")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop adaptive monitoring: {e}")
    
    def get_account_status(self) -> Dict[str, Dict]:
        """Get status of all accounts"""
        status = {}
        
        for account_name, client in self.oanda_clients.items():
            try:
                account_info = client.get_account_info()
                positions = client.get_positions()
                
                # Calculate P&L
                total_pl = account_info.unrealized_pl + account_info.realized_pl
                pl_percentage = (total_pl / account_info.balance * 100) if account_info.balance > 0 else 0
                
                # Count open positions
                open_positions = sum(1 for pos in positions.values() 
                                   if pos.long_units != 0 or pos.short_units != 0)
                
                status[account_name] = {
                    'account_id': account_info.account_id,
                    'balance': account_info.balance,
                    'currency': account_info.currency,
                    'unrealized_pl': account_info.unrealized_pl,
                    'realized_pl': account_info.realized_pl,
                    'total_pl': total_pl,
                    'pl_percentage': pl_percentage,
                    'margin_used': account_info.margin_used,
                    'margin_available': account_info.margin_available,
                    'open_positions': open_positions,
                    'open_trades': account_info.open_trade_count,
                    'pending_orders': account_info.pending_order_count,
                    'margin_usage_pct': (account_info.margin_used / account_info.balance * 100) if account_info.balance > 0 else 0
                }
                
            except Exception as e:
                logger.error(f"❌ Failed to get status for {account_name}: {e}")
                status[account_name] = {'error': str(e)}
        
        return status
    
    def get_adaptive_system_status(self) -> Dict:
        """Get adaptive system status"""
        return self.adaptive_system.get_system_status()
    
    def force_adaptation_check(self):
        """Force an immediate adaptation check"""
        try:
            self.adaptive_system._check_market_conditions()
            self.adaptive_system._apply_adaptations()
            
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    "🔍 FORCED ADAPTATION CHECK\n\n"
                    f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n"
                    f"📊 Market condition: {self.adaptive_system.market_detector.get_current_market_condition().value}\n"
                    f"🎯 Adaptations applied if needed"
                )
            
            logger.info("🔍 Forced adaptation check completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to force adaptation check: {e}")
    
    def send_daily_report(self):
        """Send daily status report"""
        try:
            account_status = self.get_account_status()
            system_status = self.get_adaptive_system_status()
            
            # Calculate portfolio totals
            total_balance = sum(status.get('balance', 0) for status in account_status.values() if 'balance' in status)
            total_pl = sum(status.get('total_pl', 0) for status in account_status.values() if 'total_pl' in status)
            total_pl_pct = (total_pl / total_balance * 100) if total_balance > 0 else 0
            
            message = "📊 DAILY ADAPTIVE SYSTEM REPORT\n\n"
            message += f"💰 Portfolio Balance: ${total_balance:,.2f}\n"
            message += f"📈 Total P&L: ${total_pl:,.2f} ({total_pl_pct:+.2f}%)\n\n"
            
            message += "🏦 ACCOUNT BREAKDOWN:\n"
            for account_name, status in account_status.items():
                if 'error' in status:
                    message += f"• {account_name}: ❌ {status['error']}\n"
                else:
                    pl_emoji = "📈" if status['total_pl'] >= 0 else "📉"
                    message += f"• {account_name}: {pl_emoji} ${status['total_pl']:,.2f} ({status['pl_percentage']:+.2f}%)\n"
                    message += f"  Balance: ${status['balance']:,.2f} | Positions: {status['open_positions']}\n"
            
            message += f"\n🤖 ADAPTIVE SYSTEM:\n"
            message += f"• Status: {'🟢 Active' if system_status['is_running'] else '🔴 Inactive'}\n"
            message += f"• Market Condition: {system_status['current_condition'].replace('_', ' ').title()}\n"
            message += f"• Active Signals: {system_status['active_signals']}\n"
            message += f"• Monitored Instruments: {len(system_status['monitored_instruments'])}\n"
            
            message += f"\n⏰ Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if self.telegram_notifier:
                self.telegram_notifier.send_message(message)
            
            logger.info("📊 Daily report sent")
            
        except Exception as e:
            logger.error(f"❌ Failed to send daily report: {e}")
    
    def save_learning_data(self, filename: str = None):
        """Save learning data for analysis"""
        try:
            filename = self.adaptive_system.save_learning_data(filename)
            logger.info(f"💾 Learning data saved: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Failed to save learning data: {e}")
            return None

def main():
    """Main function for running the adaptive system"""
    try:
        # Initialize adaptive account manager
        manager = AdaptiveAccountManager()
        
        print("🤖 ADAPTIVE TRADING SYSTEM")
        print("=" * 50)
        
        # Show initial status
        account_status = manager.get_account_status()
        print("\n📊 ACCOUNT STATUS:")
        for account_name, status in account_status.items():
            if 'error' not in status:
                pl_emoji = "📈" if status['total_pl'] >= 0 else "📉"
                print(f"  {account_name}: {pl_emoji} ${status['total_pl']:,.2f} ({status['pl_percentage']:+.2f}%)")
            else:
                print(f"  {account_name}: ❌ {status['error']}")
        
        # Start adaptive monitoring
        print("\n🚀 Starting adaptive monitoring...")
        manager.start_adaptive_monitoring()
        
        # Keep running
        try:
            while True:
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping adaptive system...")
            manager.stop_adaptive_monitoring()
            
    except Exception as e:
        logger.error(f"❌ Failed to run adaptive system: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    import time
    exit(main())

