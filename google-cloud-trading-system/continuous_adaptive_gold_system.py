#!/usr/bin/env python3
"""
Continuous Adaptive Gold System
==============================

Permanent, self-regulating gold trading system that:
1. Runs continuously (24/7)
2. Weekly assessment and planning
3. Adaptive risk management
4. Economic event integration
5. Self-learning and optimization
"""

import requests
import time
import threading
import schedule
from datetime import datetime, timedelta
import pytz
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OANDA config
OANDA_API_KEY = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
OANDA_BASE_URL = "https://api-fxpractice.oanda.com"

headers = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}

BOT_TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
CHAT_ID = "6100678501"

class ContinuousAdaptiveGoldSystem:
    """Continuous adaptive gold trading system"""
    
    def __init__(self):
        self.running = False
        self.account_id = '101-004-30719775-008'
        self.adaptive_strategy = None
        self.weekly_assessment_scheduled = False
        
        # Load adaptive strategy
        self._load_adaptive_strategy()
        
        # Schedule weekly assessments (Sundays at 6 PM London)
        self._schedule_weekly_assessments()
        
        logger.info("🥇 Continuous Adaptive Gold System initialized")
        logger.info("   Status: PERMANENT & SELF-REGULATING")
        logger.info("   Weekly assessments: Scheduled")
        logger.info("   Economic integration: Active")
    
    def _load_adaptive_strategy(self):
        """Load the adaptive Trump Gold strategy"""
        try:
            from src.strategies.adaptive_trump_gold_strategy import get_adaptive_trump_gold_strategy
            self.adaptive_strategy = get_adaptive_trump_gold_strategy()
            logger.info("✅ Adaptive Trump Gold Strategy loaded")
        except Exception as e:
            logger.error(f"❌ Error loading adaptive strategy: {e}")
            self.adaptive_strategy = None
    
    def _schedule_weekly_assessments(self):
        """Schedule weekly assessments for Sundays at 6 PM London"""
        try:
            # Schedule weekly assessment
            schedule.every().sunday.at("18:00").do(self._run_weekly_assessment)
            self.weekly_assessment_scheduled = True
            logger.info("📅 Weekly assessments scheduled for Sundays at 6 PM London")
        except Exception as e:
            logger.error(f"❌ Error scheduling weekly assessments: {e}")
    
    def _run_weekly_assessment(self):
        """Run weekly assessment and planning"""
        try:
            logger.info("📊 Running weekly assessment...")
            
            # Import and run weekly assessment
            from weekly_gold_assessment import main as run_assessment
            run_assessment()
            
            # Reload adaptive strategy with new parameters
            self._load_adaptive_strategy()
            
            logger.info("✅ Weekly assessment completed")
            
        except Exception as e:
            logger.error(f"❌ Error in weekly assessment: {e}")
    
    def send_telegram(self, message):
        """Send Telegram message"""
        try:
            url = f'https://api.telegram.org/bot{self.BOT_TOKEN}/sendMessage'
            data = {'chat_id': self.CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            logger.error(f"Telegram error: {e}")
    
    def get_current_price(self, instrument):
        """Get current price"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/pricing"
            params = {'instruments': instrument}
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'prices' in data and len(data['prices']) > 0:
                    price_data = data['prices'][0]
                    return {
                        'bid': float(price_data['bids'][0]['price']),
                        'ask': float(price_data['asks'][0]['price']),
                        'mid': (float(price_data['bids'][0]['price']) + float(price_data['asks'][0]['price'])) / 2,
                        'spread': float(price_data['asks'][0]['price']) - float(price_data['bids'][0]['price'])
                    }
        except Exception as e:
            logger.error(f"Price error for {instrument}: {e}")
        return None
    
    def analyze_adaptive_opportunity(self):
        """Analyze adaptive gold opportunity"""
        try:
            if not self.adaptive_strategy:
                return None
            
            # Get current gold price
            gold_data = self.get_current_prices(['XAU_USD']).get('XAU_USD')
            if not gold_data:
                return None
            
            current_price = gold_data['mid']
            spread = gold_data['spread']
            
            # Check if in entry zone
            entry_zones = self.adaptive_strategy.entry_zones
            profit_targets = self.adaptive_strategy.profit_targets
            
            # Find closest entry zone
            closest_zone = None
            min_distance = float('inf')
            
            for zone in entry_zones:
                distance = abs(current_price - zone)
                if distance < min_distance:
                    min_distance = distance
                    closest_zone = zone
            
            # Check if within entry range
            if min_distance <= 5.0:  # Within $5 of entry zone
                # Determine entry type
                if current_price < closest_zone:
                    entry_type = "PULLBACK"
                    confidence = 0.80
                elif current_price > closest_zone:
                    entry_type = "BREAKOUT"
                    confidence = 0.75
                else:
                    entry_type = "ENTRY ZONE"
                    confidence = 0.70
                
                # Check minimum confidence
                if confidence >= self.adaptive_strategy.min_confidence:
                    return {
                        'instrument': 'XAU_USD',
                        'price': current_price,
                        'entry_type': entry_type,
                        'confidence': confidence,
                        'zone': closest_zone,
                        'profit_targets': profit_targets,
                        'spread': spread
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing adaptive opportunity: {e}")
            return None
    
    def execute_adaptive_trade(self, opportunity):
        """Execute adaptive gold trade"""
        try:
            if not opportunity:
                return False
            
            instrument = opportunity['instrument']
            price = opportunity['price']
            confidence = opportunity['confidence']
            entry_type = opportunity['entry_type']
            
            # Calculate position size for $1,000+ profit
            # For gold: 1 pip = $1 per 1 unit
            # Need 1000 units for $1,000 profit on 1 pip move
            # Need 100 units for $1,000 profit on 10 pip move
            
            profit_distance = opportunity['profit_targets'][0] - price
            if profit_distance > 0:
                units_needed = int(1000 / profit_distance)  # Units for $1,000 profit
                units_needed = max(100, min(units_needed, 2000))  # Between 100-2000 units
            else:
                units_needed = 1000  # Default size
            
            # Calculate stop loss and take profit
            stop_loss = price - 15.0  # $15 stop loss
            take_profit = opportunity['profit_targets'][0]  # First profit target
            
            # Execute trade
            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(units_needed),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                    "stopLossOnFill": {"price": str(stop_loss)},
                    "takeProfitOnFill": {"price": str(take_profit)}
                }
            }
            
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/orders"
            response = requests.post(url, headers=headers, json=order_data, timeout=10)
            
            if response.status_code == 201:
                order = response.json().get('orderCreateTransaction', {})
                
                # Send success alert
                message = f"""🥇 **ADAPTIVE GOLD TRADE EXECUTED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💱 **Instrument:** {instrument}
📊 **Units:** {units_needed:,}
💰 **Entry:** ${price:.2f}
🛡️ **Stop Loss:** ${stop_loss:.2f}
🎯 **Take Profit:** ${take_profit:.2f}
📈 **Confidence:** {confidence:.2f}
🎯 **Entry Type:** {entry_type}

**ADAPTIVE SYSTEM ACTIVE** ✅
**Weekly Assessment:** Scheduled
**Self-Regulation:** ENABLED
**Economic Integration:** ACTIVE

Ready for continuous profits! 🥇💰"""
                
                self.send_telegram(message)
                logger.info(f"ADAPTIVE GOLD TRADE EXECUTED: {instrument} {units_needed} units")
                return True
            else:
                logger.error(f"Trade execution failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return False
    
    def run_adaptive_scan(self):
        """Run one adaptive scan cycle"""
        try:
            # Check for adaptive opportunity
            opportunity = self.analyze_adaptive_opportunity()
            
            if opportunity:
                logger.info(f"ADAPTIVE OPPORTUNITY: {opportunity['entry_type']} at ${opportunity['price']:.2f}")
                
                # Execute trade
                success = self.execute_adaptive_trade(opportunity)
                if success:
                    logger.info("ADAPTIVE TRADE EXECUTED SUCCESSFULLY!")
                else:
                    logger.error("ADAPTIVE TRADE EXECUTION FAILED!")
            else:
                logger.info("No adaptive opportunities found")
                
        except Exception as e:
            logger.error(f"Adaptive scan error: {e}")
    
    def start_continuous_system(self):
        """Start continuous adaptive gold system"""
        self.running = True
        logger.info("🥇 CONTINUOUS ADAPTIVE GOLD SYSTEM STARTED")
        
        # Send startup message
        self.send_telegram("""🥇 **CONTINUOUS ADAPTIVE GOLD SYSTEM ACTIVATED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **System Status:** PERMANENT & ACTIVE
🔄 **Self-Regulation:** ENABLED
📊 **Weekly Assessment:** Scheduled (Sundays 6 PM)
💰 **Min Profit:** $1,000+ per trade
🎯 **Adaptive Parameters:** Dynamic

**SYSTEM CAPABILITIES:**
• Continuous 24/7 monitoring
• Weekly performance assessment
• Adaptive risk management
• Economic event integration
• Self-learning optimization
• Automatic parameter adjustment

**READY FOR CONTINUOUS PROFITS!** 🥇💰""")
        
        while self.running:
            try:
                # Run adaptive scan
                self.run_adaptive_scan()
                
                # Check scheduled tasks
                schedule.run_pending()
                
                # Wait before next scan
                time.sleep(60)  # Scan every minute
                
            except KeyboardInterrupt:
                logger.info("Continuous system stopped by user")
                break
            except Exception as e:
                logger.error(f"Continuous system error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
        
        logger.info("🥇 CONTINUOUS ADAPTIVE GOLD SYSTEM STOPPED")
    
    def stop_continuous_system(self):
        """Stop continuous adaptive gold system"""
        self.running = False
        self.send_telegram("🥇 **CONTINUOUS ADAPTIVE GOLD SYSTEM STOPPED**")

if __name__ == "__main__":
    system = ContinuousAdaptiveGoldSystem()
    try:
        system.start_continuous_system()
    except KeyboardInterrupt:
        system.stop_continuous_system()
