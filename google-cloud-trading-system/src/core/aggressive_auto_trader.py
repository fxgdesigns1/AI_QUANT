#!/usr/bin/env python3
"""
AGGRESSIVE AUTO-TRADER - Catches ALL moves automatically
No hesitation, no waiting - executes immediately on ANY signal
"""

import os
import logging
from datetime import datetime
from typing import List, Dict
import time

logger = logging.getLogger(__name__)

class AggressiveAutoTrader:
    """Automatically catches and executes ALL trading opportunities"""
    
    def __init__(self):
        self.name = "AggressiveAutoTrader"
        self.min_momentum = 0.01  # VERY LOW - catch almost everything
        self.enabled = True
        
        logger.info("="*80)
        logger.info("🚀 AGGRESSIVE AUTO-TRADER INITIALIZED")
        logger.info("="*80)
        logger.info("Mode: FULL AUTO-EXECUTION")
        logger.info("Momentum threshold: 0.01% (VERY AGGRESSIVE)")
        logger.info("Will execute on ANY clear signal")
        logger.info("="*80)
    
    def scan_and_execute(self):
        """Scan market and execute ALL opportunities immediately"""
        try:
            from src.core.oanda_client import OandaClient
            from src.core.yaml_manager import get_yaml_manager
            import requests
            
            yaml_mgr = get_yaml_manager()
            accounts = yaml_mgr.get_all_accounts()
            
            if not accounts:
                logger.error("❌ No accounts found")
                return
            
            # Use first active account
            account = accounts[0]
            account_id = account['id']
            
            client = OandaClient(account_id=account_id)
            account_info = client.get_account_info()
            balance = float(account_info.balance)
            
            logger.info(f"💰 Balance: ${balance:,.2f}")
            
            # Instruments to scan
            instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
            
            trades_executed = 0
            
            for instrument in instruments:
                try:
                    # Get current price
                    prices = client.get_current_prices([instrument], force_refresh=True)
                    if instrument not in prices:
                        continue
                    
                    price = prices[instrument]
                    
                    # Get candles for momentum
                    headers = {
                        'Authorization': f'Bearer {os.environ["OANDA_API_KEY"]}',
                        'Content-Type': 'application/json'
                    }
                    
                    url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles"
                    params = {'count': 20, 'granularity': 'M5', 'price': 'M'}
                    
                    response = requests.get(url, headers=headers, params=params)
                    data = response.json()
                    
                    if 'candles' not in data or len(data['candles']) < 10:
                        continue
                    
                    candles = data['candles']
                    closes = [float(c['mid']['c']) for c in candles[-10:]]
                    
                    # Calculate momentum
                    momentum = (closes[-1] - closes[-5]) / closes[-5] * 100
                    
                    # Moving averages
                    ma_3 = sum(closes[-3:]) / 3
                    ma_5 = sum(closes[-5:]) / 5
                    
                    current = closes[-1]
                    
                    # VERY AGGRESSIVE - execute on minimal signal
                    signal = None
                    
                    if ma_3 > ma_5 and momentum > self.min_momentum:
                        signal = 'BUY'
                    elif ma_3 < ma_5 and momentum < -self.min_momentum:
                        signal = 'SELL'
                    
                    if signal:
                        logger.info(f"🎯 {instrument} {signal} signal detected (momentum: {momentum:.3f}%)")
                        
                        # Calculate sizing
                        if 'XAU' in instrument:
                            units = int((balance * 0.01) / 2.5)
                            if signal == 'SELL':
                                units = -units
                            entry = price.bid if signal == 'SELL' else price.ask
                            tp = entry + 15.0 if signal == 'BUY' else entry - 15.0
                            sl = entry - 2.5 if signal == 'BUY' else entry + 2.5
                        else:
                            units = int(((balance * 0.01) / 10) * 10000)
                            units = (units // 1000) * 1000
                            if signal == 'SELL':
                                units = -units
                            entry = price.bid if signal == 'SELL' else price.ask
                            
                            if 'JPY' in instrument:
                                tp = entry + 0.20 if signal == 'BUY' else entry - 0.20
                                sl = entry - 0.10 if signal == 'BUY' else entry + 0.10
                            else:
                                tp = entry + 0.0020 if signal == 'BUY' else entry - 0.0020
                                sl = entry - 0.0010 if signal == 'BUY' else entry + 0.0010
                        
                        # EXECUTE IMMEDIATELY
                        logger.info(f"⚡ EXECUTING: {instrument} {signal} {units} units")
                        
                        result = client.place_market_order(
                            instrument=instrument,
                            units=units,
                            stop_loss=sl,
                            take_profit=tp
                        )
                        
                        if result:
                            trades_executed += 1
                            logger.info(f"✅ FILLED: {instrument} {signal} @ {entry:.5f}")
                            
                            # Send Telegram alert
                            try:
                                message = f"✅ AUTO-TRADE\n\n{instrument} {signal}\nEntry: {entry:.5f if 'XAU' not in instrument else entry:.2f}\nUnits: {abs(units):,}\nMomentum: {momentum:+.2f}%"
                                
                                tg_url = "https://api.telegram.org/bot7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU/sendMessage"
                                requests.post(tg_url, json={"chat_id": "6100678501", "text": message}, timeout=3)
                            except:
                                pass
                        else:
                            logger.warning(f"⚠️ Failed to execute {instrument} {signal}")
                    
                    # Small delay between instruments
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ Error scanning {instrument}: {e}")
                    continue
            
            logger.info(f"📊 Scan complete: {trades_executed} trades executed")
            return trades_executed
            
        except Exception as e:
            logger.error(f"❌ Auto-trader error: {e}")
            import traceback
            traceback.print_exc()
            return 0


def get_aggressive_auto_trader():
    """Get aggressive auto-trader instance"""
    global _auto_trader
    if '_auto_trader' not in globals():
        _auto_trader = AggressiveAutoTrader()
    return _auto_trader
