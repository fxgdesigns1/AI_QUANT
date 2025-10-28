#!/usr/bin/env python3
"""
Cloud Auto-Trading Scanner - Runs 24/7 on Cloud Run
Monitors 3 GBP/USD strategy accounts continuously
"""

import sys
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Setup paths
sys.path.insert(0, 'src')
load_dotenv('oanda_config.env')

from src.core.oanda_client import OandaClient
from src.strategies.gbp_usd_optimized import get_strategy_rank_1, get_strategy_rank_2, get_strategy_rank_3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CloudAutoTradingScanner:
    """24/7 Auto-trading scanner for Cloud Run"""
    
    def __init__(self):
        """Initialize scanner"""
        self.accounts = [
            {
                "id": "101-004-30719775-008",
                "name": "🏆 Strategy #1 (Sharpe 35.90)",
                "strategy": get_strategy_rank_1(),
                "max_positions": 5,
                "position_size": 2000
            },
            {
                "id": "101-004-30719775-007",
                "name": "🥈 Strategy #2 (Sharpe 35.55)",
                "strategy": get_strategy_rank_2(),
                "max_positions": 5,
                "position_size": 2000
            },
            {
                "id": "101-004-30719775-006",
                "name": "🥉 Strategy #3 (Sharpe 35.18)",
                "strategy": get_strategy_rank_3(),
                "max_positions": 5,
                "position_size": 2000
            }
        ]
        
        self.clients = {}
        for acc in self.accounts:
            self.clients[acc['id']] = OandaClient(account_id=acc['id'])
        
        logger.info("✅ Cloud Auto-Trading Scanner initialized")
        logger.info(f"📊 Monitoring {len(self.accounts)} accounts")
    
    def scan_and_trade(self):
        """Scan market and place trades when signals detected"""
        
        logger.info("\n" + "="*70)
        logger.info(f"🔍 MARKET SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("="*70)
        
        for account in self.accounts:
            account_id = account['id']
            name = account['name']
            strategy = account['strategy']
            
            try:
                client = self.clients[account_id]
                
                # Get account status
                account_info = client.get_account_info()
                current_trades = account_info.open_trade_count
                
                logger.info(f"\n{name} (...{account_id[-3:]}):")
                logger.info(f"   Open Trades: {current_trades}/{account['max_positions']}")
                logger.info(f"   Balance: ${account_info.balance:,.2f}")
                logger.info(f"   P/L: ${account_info.unrealized_pl:.2f}")
                
                # Check if we can add more positions
                if current_trades >= account['max_positions']:
                    logger.info(f"   ⚠️ Max positions reached - skipping")
                    continue
                
                # Get market data
                prices = client.get_current_prices(["GBP_USD"])
                gbp_price = prices["GBP_USD"]
                
                # Get candles for signal generation
                candles_data = client.get_candles("GBP_USD", "M5", 50)
                
                if not candles_data or 'candles' not in candles_data:
                    logger.warning(f"   ⚠️ No candle data available")
                    continue
                
                # Let strategy analyze
                signal = strategy.scan_for_signal(candles_data, gbp_price)
                
                if signal and hasattr(signal, 'signal') and signal.signal in ['BUY', 'SELL']:
                    logger.info(f"   🎯 SIGNAL DETECTED: {signal.signal} (Confidence: {signal.confidence:.1%})")
                    
                    # Place trade
                    units = account['position_size'] if signal.signal == 'BUY' else -account['position_size']
                    
                    # Calculate SL/TP
                    if signal.signal == 'BUY':
                        sl = gbp_price.ask - 0.0050  # 50 pips
                        tp = gbp_price.ask + 0.0100  # 100 pips
                    else:
                        sl = gbp_price.bid + 0.0050
                        tp = gbp_price.bid - 0.0100
                    
                    order = client.place_market_order(
                        instrument="GBP_USD",
                        units=units,
                        stop_loss=sl,
                        take_profit=tp
                    )
                    
                    logger.info(f"   ✅ AUTO-TRADE PLACED!")
                    logger.info(f"      Order ID: {order.order_id}")
                    logger.info(f"      Direction: {signal.signal}")
                    logger.info(f"      Units: {abs(units)}")
                else:
                    logger.info(f"   ⏸️ No signal - waiting")
                    
            except Exception as e:
                logger.error(f"   ❌ Error on {name}: {str(e)[:60]}")
    
    def run_forever(self):
        """Run scanner continuously 24/7"""
        
        logger.info("\n" + "="*70)
        logger.info("🚀 CLOUD AUTO-TRADING SCANNER STARTING (24/7 MODE)")
        logger.info("="*70)
        logger.info(f"Scan Interval: Every 5 minutes")
        logger.info(f"Mode: Continuous (runs until stopped)")
        logger.info(f"Platform: Google Cloud Run")
        logger.info("="*70)
        
        scan_count = 0
        
        while True:
            try:
                scan_count += 1
                logger.info(f"\n🔄 Scan #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                self.scan_and_trade()
                
                # Wait 5 minutes between scans
                logger.info(f"\n⏸️ Waiting 5 minutes until next scan...")
                time.sleep(300)  # 5 minutes
                
            except KeyboardInterrupt:
                logger.info("\n⏹️ Scanner stopped by user")
                break
            except Exception as e:
                logger.error(f"\n❌ Scanner error: {e}")
                logger.info("🔄 Restarting in 60 seconds...")
                time.sleep(60)
                continue

if __name__ == "__main__":
    scanner = CloudAutoTradingScanner()
    scanner.run_forever()
