#!/usr/bin/env python3
"""
Trump DNA Scanner - Integrates weekly roadmaps + economic calendar into scanning
Each strategy knows the week's plan and trades at sniper zones
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from .trump_dna_framework import get_trump_dna_planner
from .economic_calendar import get_economic_calendar
from .oanda_client import get_oanda_client
from .telegram_notifier import get_telegram_notifier

logger = logging.getLogger(__name__)

class TrumpDNAScanner:
    """Scanner that uses Trump DNA - weekly planning + sniper execution"""
    
    def __init__(self):
        self.planner = get_trump_dna_planner()
        self.calendar = get_economic_calendar()
        self.oanda = get_oanda_client()
        self.notifier = get_telegram_notifier()
        
        # Track signals
        self.signals_today = 0
        self.trades_entered = []
        
        logger.info("✅ Trump DNA Scanner initialized")
        logger.info(f"   Weekly target: ${sum([p.weekly_target_dollars for p in self.planner.weekly_plans.values()])}")
    
    def scan_for_sniper_entries(self) -> List[Dict]:
        """Scan for sniper entry opportunities based on roadmaps"""
        signals = []
        
        logger.info("🎯 Scanning for sniper entries...")
        
        # Get current prices
        instruments = ['XAU_USD', 'GBP_USD', 'EUR_USD', 'USD_JPY']
        try:
            prices = self.oanda.get_current_prices(instruments)
        except:
            logger.error("❌ Failed to get prices")
            return []
        
        # Check each plan
        for plan_key, plan in self.planner.weekly_plans.items():
            pair = plan.pair
            
            # Check if pair in our price data
            if pair not in prices:
                continue
            
            current_price = prices[pair].ask  # Use ask for buying
            
            # Check economic calendar - should we pause?
            should_pause, reason = self.calendar.should_pause_trading(pair)
            if should_pause:
                logger.warning(f"⏸️  {pair} paused: {reason}")
                continue
            
            # Check weekly roadmap - can we trade?
            can_trade, trade_reason = self.planner.should_trade_now(pair, plan.strategy_name)
            if not can_trade:
                logger.info(f"⏸️  {pair} not trading: {trade_reason}")
                continue
            
            # Check sniper entry zones
            signal = self.planner.get_entry_signal(pair, current_price, plan.strategy_name)
            
            if signal:
                logger.info(f"🎯 SNIPER SIGNAL: {pair} @ {current_price}")
                logger.info(f"   Zone: {signal['zone_type']} at {signal['entry_zone']}")
                logger.info(f"   Action: {signal['action']}")
                logger.info(f"   SL: {signal['stop_loss']} | TP: {signal['take_profit']}")
                
                signals.append({
                    **signal,
                    'strategy': plan.strategy_name,
                    'weekly_target': plan.weekly_target_dollars,
                    'weekly_progress': plan.current_week_profit,
                    'max_hold_hours': plan.max_hold_hours
                })
        
        logger.info(f"📊 Found {len(signals)} sniper entry signals")
        return signals
    
    def execute_signal(self, signal: Dict, account_id: str) -> bool:
        """Execute a sniper signal"""
        try:
            pair = signal['pair']
            action = signal['action']
            entry = signal['entry_price']
            sl = signal['stop_loss']
            tp = signal['take_profit']
            
            # Determine units (small test: 100 for forex, 10 for gold)
            units = 10 if 'XAU' in pair else 100
            if action == 'SELL':
                units = -units
            
            logger.info(f"📤 Executing: {action} {pair} @ {entry}")
            logger.info(f"   SL: {sl} | TP: {tp} | Units: {units}")
            
            # Place order via OANDA
            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": pair,
                    "units": str(units),
                    "timeInForce": "FOK",
                    "stopLossOnFill": {"price": f"{sl:.5f}" if 'XAU' not in pair else f"{sl:.2f}"},
                    "takeProfitOnFill": {"price": f"{tp:.5f}" if 'XAU' not in pair else f"{tp:.2f}"}
                }
            }
            
            # Execute via OANDA client
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.oanda.api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f'{self.oanda.base_url}/accounts/{account_id}/orders'
            response = requests.post(url, headers=headers, json=order_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                if 'orderFillTransaction' in result:
                    fill = result['orderFillTransaction']
                    trade_id = fill['id']
                    
                    logger.info(f"✅ Trade executed! ID: {trade_id}")
                    
                    # Send Telegram alert
                    self.notifier.send_message(
                        f"🎯 SNIPER ENTRY EXECUTED!\\n\\n"
                        f"{signal['strategy']}\\n"
                        f"{action} {pair} @ {entry}\\n"
                        f"SL: {sl} | TP: {tp}\\n"
                        f"Trade ID: {trade_id}\\n"
                        f"Reason: {signal['reason']}",
                        'trade_signal'
                    )
                    
                    self.trades_entered.append(trade_id)
                    return True
            
            logger.error(f"❌ Order failed: {response.text[:200]}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return False


# Global instance
_trump_scanner = None

def get_trump_dna_scanner():
    """Get Trump DNA scanner instance"""
    global _trump_scanner
    if _trump_scanner is None:
        _trump_scanner = TrumpDNAScanner()
    return _trump_scanner

