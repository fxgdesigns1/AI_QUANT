#!/usr/bin/env python3
"""
Daily Gold Monitor - Sends daily alerts about Trump Gold Strategy
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, time, timedelta
import pytz
from typing import Dict, Any, Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.oanda_client import get_oanda_client
from src.core.telegram_notifier import get_telegram_notifier

# Telegram config
BOT_TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
CHAT_ID = "6100678501"

logger = logging.getLogger(__name__)

class DailyGoldMonitor:
    """Daily monitoring and alerting for Trump Gold Strategy"""
    
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.chat_id = CHAT_ID
        self.data_file = "adaptive_trump_gold_data.json"
        self.strategy_data = self._load_strategy_data()
        
    def _load_strategy_data(self) -> Dict[str, Any]:
        """Load strategy data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading strategy data: {e}")
            return {}
    
    def _get_current_gold_price(self) -> Optional[float]:
        """Get current gold price from OANDA"""
        try:
            client = get_oanda_client()
            prices = client.get_current_prices(['XAU_USD'])
            if 'XAU_USD' in prices:
                return (prices['XAU_USD'].bid + prices['XAU_USD'].ask) / 2
        except Exception as e:
            logger.error(f"Error getting gold price: {e}")
        return None
    
    def _get_account_balance(self) -> float:
        """Get current account balance"""
        try:
            client = get_oanda_client()
            account_info = client.get_account_summary()
            return float(account_info.get('balance', 0))
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 0.0
    
    def _get_open_positions(self) -> int:
        """Get number of open gold positions"""
        try:
            client = get_oanda_client()
            positions = client.get_positions()
            gold_positions = 0
            for pos in positions:
                if 'XAU_USD' in pos.get('instrument', ''):
                    gold_positions += 1
            return gold_positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return 0
    
    def _send_telegram_alert(self, message: str):
        """Send Telegram alert"""
        try:
            url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Daily alert sent to Telegram")
            else:
                logger.error(f"❌ Telegram error: {response.text}")
        except Exception as e:
            logger.error(f"❌ Error sending Telegram alert: {e}")
    
    def generate_daily_report(self) -> str:
        """Generate comprehensive daily report"""
        london_time = datetime.now(pytz.timezone('Europe/London'))
        
        # Get current market data
        current_price = self._get_current_gold_price()
        account_balance = self._get_account_balance()
        open_positions = self._get_open_positions()
        
        # Get strategy levels
        current_levels = self.strategy_data.get('current_levels', {})
        entry_zones = current_levels.get('entry_zones', [])
        profit_targets = current_levels.get('profit_targets', [])
        stop_loss_levels = current_levels.get('stop_loss_levels', [])
        
        # Calculate distance to entry zones
        entry_analysis = []
        if current_price and entry_zones:
            for i, zone in enumerate(entry_zones):
                distance = abs(current_price - zone)
                direction = "ABOVE" if current_price > zone else "BELOW"
                entry_analysis.append(f"• **Zone {i+1}:** ${zone:,.0f} ({direction} by ${distance:.0f})")
        
        # Calculate profit potential
        profit_analysis = []
        if current_price and profit_targets:
            for i, target in enumerate(profit_targets):
                profit = target - current_price
                profit_analysis.append(f"• **Target {i+1}:** ${target:,.0f} (+${profit:,.0f} profit)")
        
        # Market status
        market_status = "🟢 BULLISH" if current_price and current_price > 4000 else "🔴 BEARISH" if current_price and current_price < 4000 else "⚪ NEUTRAL"
        
        # Strategy readiness
        readiness = "🟢 READY" if open_positions < 2 else "🟡 ACTIVE" if open_positions >= 1 else "🔴 WAITING"
        
        # Generate report
        report = f"""🥇 **DAILY TRUMP GOLD STRATEGY REPORT**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 **Time:** {london_time.strftime('%I:%M %p %Z')}
📅 **Date:** {london_time.strftime('%A, %B %d, %Y')}

**📊 MARKET STATUS:**
• **Gold Price:** ${current_price:,.2f} ({market_status})
• **Account Balance:** ${account_balance:,.2f}
• **Open Positions:** {open_positions}/2
• **Strategy Status:** {readiness}

**🎯 ENTRY ZONES:**
{chr(10).join(entry_analysis) if entry_analysis else "• No entry zones configured"}

**💰 MASSIVE PROFIT TARGETS:**
{chr(10).join(profit_analysis) if profit_analysis else "• No profit targets configured"}

**🛡️ STOP LOSS LEVELS:**
{chr(10).join([f"• **Stop {i+1}:** ${stop:,.0f}" for i, stop in enumerate(stop_loss_levels)]) if stop_loss_levels else "• No stop losses configured"}

**📈 STRATEGY PERFORMANCE:**
• **Risk per Trade:** 1.5%
• **Max Positions:** 2
• **Min Confidence:** 70%
• **Self-Regulation:** ACTIVE
• **Weekly Assessment:** Scheduled

**🚀 TODAY'S OPPORTUNITIES:**
• **London Session:** 8:00 AM - 5:00 PM
• **NY Session:** 1:00 PM - 5:00 PM (Prime Time)
• **Entry Triggers:** Price within $5 of entry zones
• **Confidence Threshold:** 70%+

**📋 ECONOMIC EVENTS:**
• Monitor for high-impact USD/EUR events
• Watch for Fed speeches and policy changes
• Track geopolitical developments
• Gold-specific news and central bank actions

**🎯 ACTION PLAN:**
• **If price hits entry zone:** AUTOMATIC ENTRY
• **If price breaks resistance:** BREAKOUT ENTRY
• **If price pulls back:** PULLBACK ENTRY
• **Risk Management:** Stop losses active
• **Profit Taking:** Multiple targets available

**📞 ALERTS:**
• Entry signals will be sent immediately
• Position updates every 4 hours
• Weekly assessment on Sunday 6 PM
• Emergency alerts for major moves

**READY FOR MASSIVE PROFITS!** 🥇💰"""

        return report
    
    def send_daily_alert(self):
        """Send daily alert with comprehensive report"""
        try:
            report = self.generate_daily_report()
            self._send_telegram_alert(report)
            logger.info("📊 Daily gold strategy report sent")
        except Exception as e:
            logger.error(f"❌ Error sending daily alert: {e}")
    
    def check_entry_opportunities(self):
        """Check for immediate entry opportunities"""
        try:
            current_price = self._get_current_gold_price()
            if not current_price:
                return
            
            current_levels = self.strategy_data.get('current_levels', {})
            entry_zones = current_levels.get('entry_zones', [])
            
            if not entry_zones:
                return
            
            # Check if price is near any entry zone
            for i, zone in enumerate(entry_zones):
                distance = abs(current_price - zone)
                if distance <= 5.0:  # Within $5 of entry zone
                    message = f"""🚨 **IMMEDIATE ENTRY OPPORTUNITY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🥇 **Gold Price:** ${current_price:,.2f}
🎯 **Entry Zone {i+1}:** ${zone:,.0f}
📏 **Distance:** ${distance:.1f} (WITHIN TRIGGER RANGE)

**🚀 STRATEGY READY TO ENTER:**
• **Confidence:** HIGH (within $5 of zone)
• **Risk:** 1.5% per trade
• **Max Positions:** 2
• **Profit Targets:** $400-$2,000

**⚡ AUTOMATIC ENTRY ACTIVE**
The system will attempt to enter when conditions are met!"""
                    
                    self._send_telegram_alert(message)
                    logger.info(f"🚨 Entry opportunity detected: Zone {i+1} at ${zone:,.0f}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Error checking entry opportunities: {e}")

def main():
    """Main function for daily monitoring"""
    logging.basicConfig(level=logging.INFO)
    
    monitor = DailyGoldMonitor()
    
    print("🥇 Daily Gold Monitor Started")
    print("=" * 50)
    
    # Send daily report
    monitor.send_daily_alert()
    
    # Check for immediate opportunities
    monitor.check_entry_opportunities()
    
    print("✅ Daily monitoring complete")

if __name__ == "__main__":
    main()
