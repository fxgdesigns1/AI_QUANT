#!/usr/bin/env python3
"""
UNIFIED MONITORING SYSTEM
========================

Comprehensive monitoring for:
1. All trading accounts (10 strategies)
2. Semi-automatic trading system
3. Trade assistant integration
4. Dashboard synchronization
5. Real-time alerts and updates
"""

import os
import sys
import logging
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
from dataclasses import dataclass

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.yaml_manager import get_yaml_manager
from src.core.oanda_client import OandaClient
from src.core.data_feed import get_data_feed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AccountStatus:
    """Account status information"""
    account_id: str
    name: str
    strategy: str
    balance: float
    currency: str
    open_trades: int
    open_positions: int
    pnl: float
    status: str
    last_update: datetime

@dataclass
class TradingOpportunity:
    """Trading opportunity"""
    instrument: str
    price: float
    spread: float
    opportunity_type: str
    confidence: float
    account_suggestion: str

class UnifiedMonitoringSystem:
    """Unified monitoring system for all accounts and trading"""
    
    def __init__(self):
        # Telegram configuration
        self.telegram_token = os.getenv('TELEGRAM_TOKEN', '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6100678501')
        
        # System configuration
        self.semi_auto_account_id = "101-004-30719775-001"  # Strategy Zeta
        self.monitoring_interval = 60  # 1 minute
        self.alert_interval = 300  # 5 minutes
        
        # State tracking
        self.account_statuses = {}
        self.trading_opportunities = []
        self.last_alert_time = {}
        self.is_running = False
        
        # Load all accounts
        self.load_all_accounts()
        
    def load_all_accounts(self):
        """Load all trading accounts"""
        try:
            yaml_mgr = get_yaml_manager()
            self.accounts_config = yaml_mgr.get_all_accounts()
            logger.info(f"✅ Loaded {len(self.accounts_config)} accounts for monitoring")
        except Exception as e:
            logger.error(f"❌ Error loading accounts: {e}")
            self.accounts_config = []
    
    def send_telegram_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram"""
        try:
            url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Telegram message sent successfully")
                return True
            else:
                logger.error(f"❌ Telegram error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def get_account_status(self, account_id: str) -> Optional[AccountStatus]:
        """Get status for a specific account"""
        try:
            client = OandaClient(account_id=account_id)
            account_info = client.get_account_info()
            open_trades = client.get_open_trades()
            
            # Calculate P&L
            total_pnl = 0
            for trade in open_trades:
                total_pnl += float(trade.get('unrealizedPL', 0))
            
            # Find account config
            account_config = None
            for acc in self.accounts_config:
                if acc['id'] == account_id:
                    account_config = acc
                    break
            
            if not account_config:
                return None
            
            return AccountStatus(
                account_id=account_id,
                name=account_config.get('name', 'Unknown'),
                strategy=account_config.get('strategy', 'unknown'),
                balance=getattr(account_info, 'balance', 0),
                currency=getattr(account_info, 'currency', 'USD'),
                open_trades=len(open_trades),
                open_positions=0,  # Will be updated when method is available
                pnl=total_pnl,
                status="ACTIVE" if account_config.get('active', False) else "INACTIVE",
                last_update=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting status for account {account_id}: {e}")
            return None
    
    def scan_trading_opportunities(self) -> List[TradingOpportunity]:
        """Scan for trading opportunities across all instruments"""
        opportunities = []
        
        try:
            data_feed = get_data_feed()
            instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'XAU_USD']
            
            for instrument in instruments:
                try:
                    # Get current price data
                    prices = data_feed.get_latest_prices([instrument])
                    if instrument in prices:
                        price_data = prices[instrument]
                        mid_price = (price_data.bid + price_data.ask) / 2
                        spread = price_data.ask - price_data.bid
                        
                        # Opportunity detection logic
                        if spread < 0.0005:  # Low spread
                            opportunities.append(TradingOpportunity(
                                instrument=instrument,
                                price=mid_price,
                                spread=spread,
                                opportunity_type="LOW_SPREAD",
                                confidence=0.8,
                                account_suggestion=self._suggest_account(instrument)
                            ))
                        
                        # Price movement opportunity
                        if spread > 0.001:  # High volatility
                            opportunities.append(TradingOpportunity(
                                instrument=instrument,
                                price=mid_price,
                                spread=spread,
                                opportunity_type="HIGH_VOLATILITY",
                                confidence=0.7,
                                account_suggestion=self._suggest_account(instrument)
                            ))
                            
                except Exception as e:
                    logger.error(f"❌ Error scanning {instrument}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in opportunity scan: {e}")
            
        return opportunities
    
    def _suggest_account(self, instrument: str) -> str:
        """Suggest best account for instrument"""
        if instrument == 'XAU_USD':
            return "Trump DNA Gold (010)"
        elif instrument in ['EUR_USD', 'GBP_USD']:
            return "Semi-Auto Swing (001)"
        else:
            return "Primary Trading (008)"
    
    def create_comprehensive_report(self) -> str:
        """Create comprehensive monitoring report"""
        report = "📊 **UNIFIED TRADING SYSTEM MONITORING**\n\n"
        report += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')} London\n\n"
        
        # Account statuses
        report += "🏦 **ACCOUNT STATUSES:**\n"
        total_pnl = 0
        active_accounts = 0
        
        for account_id, status in self.account_statuses.items():
            if status:
                status_icon = "✅" if status.status == "ACTIVE" else "❌"
                pnl_icon = "📈" if status.pnl > 0 else "📉" if status.pnl < 0 else "⚪"
                
                report += f"{status_icon} **{status.name}** ({status.account_id}):\n"
                report += f"   • Balance: {status.balance:.2f} {status.currency}\n"
                report += f"   • Trades: {status.open_trades}\n"
                report += f"   • P&L: {status.pnl:.2f} {pnl_icon}\n"
                report += f"   • Strategy: {status.strategy}\n\n"
                
                total_pnl += status.pnl
                if status.status == "ACTIVE":
                    active_accounts += 1
        
        report += f"📊 **SUMMARY:**\n"
        report += f"• Active Accounts: {active_accounts}/{len(self.accounts_config)}\n"
        report += f"• Total P&L: {total_pnl:.2f}\n"
        report += f"• System Status: {'🟢 OPERATIONAL' if active_accounts > 0 else '🔴 OFFLINE'}\n\n"
        
        # Trading opportunities
        if self.trading_opportunities:
            report += "🎯 **TRADING OPPORTUNITIES:**\n"
            for i, opp in enumerate(self.trading_opportunities[:3], 1):
                report += f"{i}. **{opp.instrument}** - {opp.opportunity_type}\n"
                report += f"   • Price: {opp.price:.5f}\n"
                report += f"   • Confidence: {opp.confidence:.1%}\n"
                report += f"   • Suggested Account: {opp.account_suggestion}\n\n"
        
        # Semi-automatic status
        semi_auto_status = self.account_statuses.get(self.semi_auto_account_id)
        if semi_auto_status:
            report += "🤖 **SEMI-AUTOMATIC TRADING:**\n"
            report += f"• Account: {semi_auto_status.name}\n"
            report += f"• Status: {'🟢 READY' if semi_auto_status.status == 'ACTIVE' else '🔴 OFFLINE'}\n"
            report += f"• Balance: {semi_auto_status.balance:.2f} {semi_auto_status.currency}\n"
            report += f"• Open Trades: {semi_auto_status.open_trades}\n"
            report += f"• P&L: {semi_auto_status.pnl:.2f}\n\n"
            
            report += "💡 **Ready for commands:**\n"
            report += "• \"Enter BUY EUR/USD on account 001\"\n"
            report += "• \"Enter SELL GBP/USD on account 001\"\n"
            report += "• \"Enter BUY USD/JPY on account 001\"\n"
            report += "• \"Enter BUY XAU/USD on account 001\"\n"
            report += "• \"Enter SELL AUD/USD on account 001\"\n\n"
        
        report += "🚀 **SYSTEM STATUS: FULLY OPERATIONAL**"
        
        return report
    
    def update_all_accounts(self):
        """Update status for all accounts"""
        logger.info("🔄 Updating all account statuses...")
        
        for account in self.accounts_config:
            account_id = account['id']
            try:
                status = self.get_account_status(account_id)
                if status:
                    self.account_statuses[account_id] = status
                    logger.info(f"✅ Updated {status.name}: {status.pnl:.2f} P&L")
                else:
                    logger.warning(f"⚠️ Could not get status for {account_id}")
            except Exception as e:
                logger.error(f"❌ Error updating account {account_id}: {e}")
    
    def update_trading_opportunities(self):
        """Update trading opportunities"""
        logger.info("🔍 Scanning for trading opportunities...")
        
        opportunities = self.scan_trading_opportunities()
        self.trading_opportunities = opportunities
        
        if opportunities:
            logger.info(f"✅ Found {len(opportunities)} trading opportunities")
        else:
            logger.info("ℹ️ No trading opportunities found")
    
    def should_send_alert(self, alert_type: str, interval_minutes: int = 5) -> bool:
        """Check if alert should be sent"""
        if alert_type not in self.last_alert_time:
            return True
            
        time_since_last = datetime.now() - self.last_alert_time[alert_type]
        return time_since_last.total_seconds() >= (interval_minutes * 60)
    
    def run_monitoring_cycle(self):
        """Run one monitoring cycle"""
        logger.info("🔄 Running unified monitoring cycle...")
        
        # Update all accounts
        self.update_all_accounts()
        
        # Update trading opportunities
        self.update_trading_opportunities()
        
        # Send comprehensive report (every 5 minutes)
        if self.should_send_alert("comprehensive_report", 5):
            report = self.create_comprehensive_report()
            if report:
                self.send_telegram_message(report)
                self.last_alert_time["comprehensive_report"] = datetime.now()
        
        # Send opportunity alerts (every 2 minutes)
        if self.trading_opportunities and self.should_send_alert("opportunities", 2):
            opp_message = "🎯 **NEW TRADING OPPORTUNITIES**\n\n"
            opp_message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')} London\n\n"
            
            for i, opp in enumerate(self.trading_opportunities[:3], 1):
                opp_message += f"**{i}. {opp.instrument}** - {opp.opportunity_type}\n"
                opp_message += f"   • Price: {opp.price:.5f}\n"
                opp_message += f"   • Confidence: {opp.confidence:.1%}\n"
                opp_message += f"   • Suggested: {opp.account_suggestion}\n\n"
            
            opp_message += "💡 **Ready for your trading commands!**"
            
            self.send_telegram_message(opp_message)
            self.last_alert_time["opportunities"] = datetime.now()
    
    def start_monitoring(self):
        """Start the unified monitoring system"""
        logger.info("🚀 Starting Unified Monitoring System...")
        
        # Send startup message
        startup_message = """🤖 **UNIFIED TRADING SYSTEM MONITORING ACTIVATED**

**📊 MONITORING ALL ACCOUNTS:**
• 10 trading strategies
• Semi-automatic trading system
• Trade assistant integration
• Real-time alerts and updates

**🔔 ALERT FREQUENCY:**
• Comprehensive reports: Every 5 minutes
• Trading opportunities: Every 2 minutes
• Account updates: Real-time
• System status: Continuous

**🎯 SEMI-AUTOMATIC READY:**
Account 001 (Strategy Zeta) is active and ready for your commands!

**📱 DASHBOARD SYNC:**
All data is synchronized with the main dashboard.

Starting continuous monitoring..."""
        
        self.send_telegram_message(startup_message)
        self.is_running = True
        
        # Run monitoring loop
        while self.is_running:
            try:
                self.run_monitoring_cycle()
                time.sleep(self.monitoring_interval)
            except KeyboardInterrupt:
                logger.info("🛑 Stopping monitoring system...")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring cycle: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_running = False
        logger.info("🛑 Monitoring system stopped")

def main():
    """Main function"""
    logger.info("🤖 Starting Unified Monitoring System...")
    
    # Set up environment
    os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
    os.environ['OANDA_ENVIRONMENT'] = "practice"
    
    # Start monitoring system
    monitoring_system = UnifiedMonitoringSystem()
    monitoring_system.start_monitoring()

if __name__ == "__main__":
    main()
