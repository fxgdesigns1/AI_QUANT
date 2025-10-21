#!/usr/bin/env python3
"""
Auto-Trading Scanner for 3 New GBP/USD Strategies
Continuous market monitoring and automatic trade execution
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

class AutoTradingScanner:
    """Automatic trading scanner for 3 GBP strategies"""
    
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
        
        logger.info("✅ Auto-Trading Scanner initialized")
        logger.info(f"📊 Monitoring {len(self.accounts)} accounts")
    
    def scan_and_trade(self):
        """Scan market and place trades when signals detected"""
        
        logger.info("\n" + "="*70)
        logger.info(f"🔍 MARKET SCAN - {datetime.now().strftime('%H:%M:%S')}")
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
                signal = strategy.analyze_market(candles_data, gbp_price)
                
                if signal and signal.signal in ['BUY', 'SELL']:
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
    
    def run(self, duration_minutes: int = 60):
        """Run scanner for specified duration"""
        
        logger.info("\n" + "="*70)
        logger.info("🚀 AUTO-TRADING SCANNER STARTING")
        logger.info("="*70)
        logger.info(f"Duration: {duration_minutes} minutes")
        logger.info(f"Scan Interval: Every 5 minutes (5M timeframe)")
        logger.info("="*70)
        
        start_time = datetime.now()
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                elapsed = (datetime.now() - start_time).total_seconds() / 60
                
                if elapsed >= duration_minutes:
                    logger.info(f"\n⏰ Scanner duration reached ({duration_minutes} min)")
                    break
                
                self.scan_and_trade()
                
                # Wait 5 minutes between scans (matching 5M timeframe)
                logger.info(f"\n⏸️ Waiting 5 minutes until next scan... (Scan #{scan_count+1})")
                time.sleep(300)  # 5 minutes
                
        except KeyboardInterrupt:
            logger.info("\n⏹️ Scanner stopped by user")
        
        logger.info("\n" + "="*70)
        logger.info("✅ AUTO-TRADING SCANNER COMPLETED")
        logger.info(f"Total Scans: {scan_count}")
        logger.info("="*70)

if __name__ == "__main__":
    scanner = AutoTradingScanner()
    
    # Run for 1 hour (12 scans at 5-minute intervals)
    scanner.run(duration_minutes=60)


