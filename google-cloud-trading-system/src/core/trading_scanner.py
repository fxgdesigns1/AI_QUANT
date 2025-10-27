#!/usr/bin/env python3
"""
Trading Scanner - Main strategy execution engine
Runs every 5 minutes to scan for trading opportunities
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import yaml

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.yaml_manager import get_yaml_manager
from src.core.oanda_client import OandaClient
from src.core.order_manager import OrderManager
from src.core.telegram_notifier import get_telegram_notifier
from src.core.strategy_factory import get_strategy_factory

logger = logging.getLogger(__name__)

class TradingScanner:
    """
    Main trading scanner that runs all strategies and executes trades
    """
    
    def __init__(self):
        self.yaml_mgr = get_yaml_manager()
        self.accounts = self.yaml_mgr.get_all_accounts()
        self.active_accounts = [a for a in self.accounts if a.get('active', False)]
        
        # Initialize strategy factory
        self.strategy_factory = get_strategy_factory()
        
        # Load strategies dynamically based on active accounts
        self.strategies = {}
        loaded_strategies = set()
        
        logger.info(f"📊 Found {len(self.active_accounts)} active accounts")
        
        for account in self.active_accounts:
            strategy_name = account.get('strategy')
            if strategy_name and strategy_name not in loaded_strategies:
                try:
                    strategy = self.strategy_factory.get_strategy(
                        strategy_name, 
                        account_config=account
                    )
                    self.strategies[strategy_name] = strategy
                    loaded_strategies.add(strategy_name)
                    logger.info(f"✅ Loaded strategy: {strategy_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load {strategy_name}: {e}")
        
        logger.info(f"📊 Successfully loaded {len(self.strategies)} strategies")
        
        # Initialize order manager
        self.order_manager = OrderManager()
        
        # Initialize Telegram notifier
        self.telegram = get_telegram_notifier()
        
        logger.info(f"✅ Trading Scanner initialized with {len(self.active_accounts)} active accounts")
        logger.info(f"📊 Strategies loaded: {list(self.strategies.keys())}")
    
    def get_market_data(self, instruments: List[str]) -> Dict[str, Any]:
        """Get current market data for all instruments"""
        try:
            # Use primary account for market data
            client = OandaClient(account_id='101-004-30719775-008')
            prices = client.get_current_prices(instruments, force_refresh=True)
            
            logger.info(f"📊 Retrieved prices for {len(prices)} instruments")
            return prices
            
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return {}
    
    def run_scan(self) -> Dict[str, Any]:
        """
        Run a complete trading scan across all strategies
        Returns scan results and executed trades
        """
        scan_start = datetime.now()
        logger.info(f"🔍 Starting trading scan at {scan_start.strftime('%H:%M:%S')}")
        
        results = {
            'scan_time': scan_start.isoformat(),
            'total_signals': 0,
            'executed_trades': 0,
            'rejected_trades': 0,
            'errors': 0,
            'strategy_results': {}
        }
        
        # Get all unique instruments from active accounts
        all_instruments = set()
        for account in self.active_accounts:
            instruments = account.get('instruments', [])
            all_instruments.update(instruments)
        
        # If no instruments from accounts, use default set
        if not all_instruments:
            all_instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'XAU_USD']
        
        all_instruments = list(all_instruments)
        logger.info(f"📊 Scanning instruments: {all_instruments}")
        
        # Get market data
        market_data = self.get_market_data(all_instruments)
        if not market_data:
            logger.error("❌ No market data available - aborting scan")
            return results
        
        # Run each strategy
        for strategy_name, strategy in self.strategies.items():
            try:
                logger.info(f"🎯 Running {strategy_name} strategy")
                
                # Check if strategy is active
                if not strategy.is_strategy_active():
                    logger.info(f"⏸️  {strategy_name} is inactive - skipping")
                    continue
                
                # Check trading hours
                if not strategy.is_trading_hours():
                    logger.info(f"⏰ {strategy_name} outside trading hours - skipping")
                    continue
                
                # Analyze market and generate signals
                signals = strategy.analyze_market(market_data)
                logger.info(f"📊 {strategy_name} generated {len(signals)} signals")
                
                results['total_signals'] += len(signals)
                results['strategy_results'][strategy_name] = {
                    'signals_generated': len(signals),
                    'signals': []
                }
                
                # Execute each signal
                for signal in signals:
                    try:
                        # Add strategy name to signal
                        signal.strategy_name = strategy_name
                        
                        # Execute trade
                        execution = self.order_manager.execute_trade(signal)
                        
                        if execution.success:
                            results['executed_trades'] += 1
                            logger.info(f"✅ TRADE EXECUTED: {signal.instrument} {signal.side.value} {signal.units} units")
                            
                            # Send Telegram alert
                            try:
                                message = f"""✅ **TRADE EXECUTED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 **Strategy:** {strategy_name}
💱 **Instrument:** {signal.instrument}
➡️ **Direction:** {signal.side.value}
📊 **Units:** {signal.units:,}
💰 **Entry Price:** {signal.entry_price:.5f}
🛑 **Stop Loss:** {signal.stop_loss:.5f}
🎯 **Take Profit:** {signal.take_profit:.5f}
🆔 **Trade ID:** {execution.order.order_id if execution.order else 'N/A'}
                                
**Account:** {signal.account_id if hasattr(signal, 'account_id') else 'Primary'}
**System Protection Active** ✅"""
                                
                                self.telegram.send_alert(message, priority='HIGH')
                                
                            except Exception as e:
                                logger.error(f"❌ Failed to send Telegram alert: {e}")
                            
                        else:
                            results['rejected_trades'] += 1
                            logger.warning(f"❌ TRADE REJECTED: {execution.error_message}")
                        
                        # Store signal result
                        results['strategy_results'][strategy_name]['signals'].append({
                            'instrument': signal.instrument,
                            'side': signal.side.value,
                            'units': signal.units,
                            'success': execution.success,
                            'error': execution.error_message if not execution.success else None
                        })
                        
                    except Exception as e:
                        results['errors'] += 1
                        logger.error(f"❌ Error executing signal: {e}")
                
            except Exception as e:
                results['errors'] += 1
                logger.error(f"❌ Error running {strategy_name}: {e}")
        
        # Send scan summary
        scan_duration = datetime.now() - scan_start
        logger.info(f"✅ Scan completed in {scan_duration.total_seconds():.1f}s")
        logger.info(f"📊 Results: {results['executed_trades']} executed, {results['rejected_trades']} rejected, {results['errors']} errors")
        
        # Send summary to Telegram
        try:
            summary_message = f"""📊 **TRADING SCAN COMPLETE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 **Time:** {scan_start.strftime('%H:%M:%S')}
⏱️ **Duration:** {scan_duration.total_seconds():.1f}s

**📈 RESULTS:**
• **Signals Generated:** {results['total_signals']}
• **Trades Executed:** {results['executed_trades']}
• **Trades Rejected:** {results['rejected_trades']}
• **Errors:** {results['errors']}

**🎯 STRATEGY BREAKDOWN:**
"""
            
            for strategy_name, strategy_result in results['strategy_results'].items():
                summary_message += f"• **{strategy_name}:** {strategy_result['signals_generated']} signals\n"
            
            if results['executed_trades'] > 0:
                summary_message += "\n**🚀 TRADES ARE LIVE!**"
            else:
                summary_message += "\n**⏳ Waiting for opportunities...**"
            
            self.telegram.send_alert(summary_message, priority='NORMAL')
            
        except Exception as e:
            logger.error(f"❌ Failed to send scan summary: {e}")
        
        return results
    
    def run_continuous(self, scan_interval: int = 300):
        """
        Run continuous scanning every scan_interval seconds
        """
        logger.info(f"🔄 Starting continuous scanning every {scan_interval}s")
        
        while True:
            try:
                self.run_scan()
                time.sleep(scan_interval)
            except KeyboardInterrupt:
                logger.info("🛑 Scanner stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Scanner error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

def main():
    """Main function for running the scanner"""
    logging.basicConfig(level=logging.INFO)
    
    scanner = TradingScanner()
    
    print("🚀 Trading Scanner Started")
    print("=" * 50)
    
    # Run single scan
    results = scanner.run_scan()
    
    print(f"✅ Scan completed: {results['executed_trades']} trades executed")
    
    # Optionally run continuously
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        scanner.run_continuous()

if __name__ == "__main__":
    main()
