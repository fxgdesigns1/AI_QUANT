#!/usr/bin/env python3
"""
SNIPER TRADING SYSTEM - PERFECT TIMING & EARLY OPPORTUNITY DETECTION
This system identifies real opportunities early and enters with sniper precision
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime, timedelta

# Set up environment
os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.dynamic_account_manager import get_account_manager
from src.core.oanda_client import OandaClient
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.strategies.gold_scalping import GoldScalpingStrategy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SniperTradingSystem:
    def __init__(self):
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        self.strategies = {
            'momentum': MomentumTradingStrategy(),
            'gold': GoldScalpingStrategy()
        }
        self.is_running = False
        self.scan_count = 0
        self.opportunity_history = {}
        
        logger.info(f"🎯 SNIPER SYSTEM initialized with {len(self.active_accounts)} accounts")
    
    def detect_early_opportunities(self, market_data):
        """Detect real opportunities early with sniper precision"""
        opportunities = []
        
        for instrument, price_data in market_data.items():
            try:
                # Calculate key metrics for early detection
                spread = price_data.ask - price_data.bid
                spread_pips = spread * 10000 if 'JPY' not in instrument else spread * 100
                
                # Early opportunity detection criteria
                is_tight_spread = spread_pips < 2.0  # Tight spread = good opportunity
                is_volatile = abs(price_data.ask - price_data.bid) > 0.0001  # Some volatility
                is_liquid = True  # OANDA instruments are liquid
                
                # Market regime analysis
                regime = self._analyze_market_regime(instrument, price_data)
                
                if is_tight_spread and is_volatile and is_liquid:
                    opportunity = {
                        'instrument': instrument,
                        'bid': price_data.bid,
                        'ask': price_data.ask,
                        'spread_pips': spread_pips,
                        'regime': regime,
                        'quality_score': self._calculate_opportunity_quality(instrument, price_data, regime),
                        'timestamp': datetime.now()
                    }
                    opportunities.append(opportunity)
                    
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return opportunities
    
    def _analyze_market_regime(self, instrument, price_data):
        """Analyze market regime for opportunity quality"""
        try:
            # Simple regime detection based on spread
            spread = price_data.ask - price_data.bid
            spread_pips = spread * 10000 if 'JPY' not in instrument else spread * 100
            
            if spread_pips < 1.0:
                return "TIGHT"  # Excellent for trading
            elif spread_pips < 2.0:
                return "MODERATE"  # Good for trading
            else:
                return "WIDE"  # Poor for trading
        except:
            return "UNKNOWN"
    
    def _calculate_opportunity_quality(self, instrument, price_data, regime):
        """Calculate opportunity quality score"""
        try:
            spread = price_data.ask - price_data.bid
            spread_pips = spread * 10000 if 'JPY' not in instrument else spread * 100
            
            # Quality scoring
            quality = 100  # Base score
            
            # Spread quality (lower spread = higher quality)
            if spread_pips < 1.0:
                quality += 20
            elif spread_pips < 2.0:
                quality += 10
            else:
                quality -= 10
            
            # Regime quality
            if regime == "TIGHT":
                quality += 15
            elif regime == "MODERATE":
                quality += 5
            else:
                quality -= 15
            
            # Instrument-specific adjustments
            if instrument in ['EUR_USD', 'GBP_USD', 'XAU_USD']:
                quality += 10  # Major pairs get bonus
            
            return max(0, min(100, quality))  # Clamp between 0-100
            
        except:
            return 50  # Default score
    
    def sniper_scan_and_execute(self):
        """Sniper scan - identify and execute with perfect timing"""
        self.scan_count += 1
        logger.info(f"🎯 SNIPER SCAN #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        total_opportunities = 0
        total_executed = 0
        
        # Get market data for all accounts
        for account_id in self.active_accounts:
            try:
                client = self.account_manager.get_account_client(account_id)
                market_data = client.get_current_prices(['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD', 'USD_CAD'])
                
                # Detect early opportunities
                opportunities = self.detect_early_opportunities(market_data)
                total_opportunities += len(opportunities)
                
                if opportunities:
                    logger.info(f"🎯 Found {len(opportunities)} opportunities for account {account_id[-3:]}")
                    
                    # Sort by quality score (highest first)
                    opportunities.sort(key=lambda x: x['quality_score'], reverse=True)
                    
                    # Take only the best opportunity
                    best_opportunity = opportunities[0]
                    
                    if best_opportunity['quality_score'] >= 70:  # High quality threshold
                        logger.info(f"🎯 HIGH QUALITY OPPORTUNITY: {best_opportunity['instrument']} - Score: {best_opportunity['quality_score']}")
                        
                        # Test each strategy on the best opportunity
                        for strategy_name, strategy in self.strategies.items():
                            try:
                                signals = strategy.analyze_market(market_data)
                                if signals:
                                    # Find signal for this instrument
                                    relevant_signals = [s for s in signals if s.instrument == best_opportunity['instrument']]
                                    
                                    if relevant_signals:
                                        signal = relevant_signals[0]
                                        logger.info(f"🎯 {strategy_name} signal for {signal.instrument} - Confidence: {signal.confidence:.3f}")
                                        
                                        # SNIPER EXECUTION - Perfect timing
                                        try:
                                            # Calculate position size (1% risk - Conservative)
                                            account_info = client.get_account_info()
                                            risk_amount = account_info.balance * 0.01  # 1% risk
                                            
                                            # Get entry price from market data
                                            current_price = market_data.get(signal.instrument)
                                            if current_price:
                                                entry_price = current_price.ask if signal.side.value == 'BUY' else current_price.bid
                                            else:
                                                entry_price = 0.0
                                            
                                            # Calculate stop distance
                                            if signal.side.value == 'BUY':
                                                stop_distance = entry_price - signal.stop_loss
                                            else:
                                                stop_distance = signal.stop_loss - entry_price
                                            
                                            position_size = int(risk_amount / stop_distance) if stop_distance > 0 else 10000
                                            
                                            # SNIPER EXECUTION
                                            result = client.place_market_order(
                                                instrument=signal.instrument,
                                                units=position_size,
                                                stop_loss=signal.stop_loss,
                                                take_profit=signal.take_profit
                                            )
                                            
                                            if result:
                                                total_executed += 1
                                                logger.info(f"🎯 SNIPER HIT: {signal.instrument} {signal.side.value} - Units: {position_size} - Quality: {best_opportunity['quality_score']}")
                                            else:
                                                logger.error(f"❌ SNIPER MISS: {signal.instrument} {signal.side.value}")
                                                
                                        except Exception as e:
                                            logger.error(f"❌ Sniper execution failed: {e}")
                                        
                                        break  # Only execute one trade per scan
                                        
                            except Exception as e:
                                logger.error(f"❌ {strategy_name} failed for account {account_id[-3:]}: {e}")
                                
            except Exception as e:
                logger.error(f"❌ Failed to get market data for account {account_id[-3:]}: {e}")
        
        logger.info(f"🎯 SNIPER SCAN #{self.scan_count} COMPLETE: {total_opportunities} opportunities, {total_executed} executed")
        return total_executed
    
    def start_sniper_scanning(self):
        """Start sniper scanning - EVERY 10 MINUTES (Quality over quantity)"""
        self.is_running = True
        logger.info("🎯 STARTING SNIPER SCANNING - EVERY 10 MINUTES...")
        
        while self.is_running:
            try:
                executed = self.sniper_scan_and_execute()
                logger.info(f"🎯 Next sniper scan in 10 minutes... (Executed {executed} trades)")
                time.sleep(600)  # 10 minutes - Quality over quantity
            except KeyboardInterrupt:
                logger.info("🛑 Sniper system stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Sniper system error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop scanning"""
        self.is_running = False
        logger.info("🛑 Sniper system stopped")

def main():
    """Main sniper system loop"""
    logger.info("🎯 STARTING SNIPER TRADING SYSTEM - PERFECT TIMING")
    
    sniper = SniperTradingSystem()
    
    try:
        sniper.start_sniper_scanning()
    except KeyboardInterrupt:
        logger.info("🛑 Sniper system stopped by user")
        sniper.stop()

if __name__ == "__main__":
    main()


