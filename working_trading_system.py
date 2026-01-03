#!/usr/bin/env python3
"""
WORKING TRADING SYSTEM - ACTUALLY EXECUTES TRADES
This system will generate signals and EXECUTE them immediately
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Set up environment
os.environ['OANDA_ENVIRONMENT'] = os.environ.get('OANDA_ENVIRONMENT', 'practice')

# Path setup is handled by src.runner.main
# All imports from google-cloud-trading-system/src/
from src.core.dynamic_account_manager import get_account_manager
from src.core.trading_scanner import TradingScanner
from src.core.order_manager import OrderManager
from src.core.execution_gate import ExecutionGate
from src.strategies.momentum_trading import MomentumTradingStrategy
# Note: Using gold_scalping_optimized as gold_scalping doesn't exist
try:
    from src.strategies.gold_scalping_optimized import GoldScalpingOptimizedStrategy as GoldScalpingStrategy
except ImportError:
    # Fallback: use momentum if gold scalping not available
    GoldScalpingStrategy = MomentumTradingStrategy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _can_execute() -> tuple[bool, str]:
    """Determine if execution is enabled based on trading mode and flags.
    
    Returns:
        (can_execute: bool, reason: str)
    """
    gate = ExecutionGate()
    decision = gate.decision()
    
    # Live mode: requires dual-confirm
    if decision.mode == 'live':
        if decision.allowed:
            return (True, "live_dual_enabled")
        else:
            return (False, f"live_blocked_{decision.reason}")
    
    # Paper mode: requires PAPER_EXECUTION_ENABLED=true
    paper_execution = os.getenv('PAPER_EXECUTION_ENABLED', 'false').lower() == 'true'
    if paper_execution:
        return (True, "paper_execution_enabled")
    else:
        return (False, "paper_signals_only")


def _is_placeholder_account_id(account_id: str) -> bool:
    """Check if account_id is clearly a placeholder/invalid value."""
    if not account_id or not account_id.strip():
        return True
    
    account_id_lower = account_id.lower().strip()
    
    # Common placeholder prefixes
    placeholder_prefixes = ['test-', 'demo-', 'placeholder-', 'replace_', 'example-', 'sample-']
    if any(account_id_lower.startswith(prefix) for prefix in placeholder_prefixes):
        return True
    
    # Too short to be a real OANDA account ID
    if len(account_id.strip()) <= 3:
        return True
    
    # Contains placeholder keywords
    placeholder_keywords = ['placeholder', 'demo', 'test', 'example', 'sample', 'replace']
    if any(keyword in account_id_lower for keyword in placeholder_keywords):
        return True
    
    return False


def _has_valid_broker(account_id: str, account_manager) -> bool:
    """Check if account has a valid (non-placeholder) broker client for execution."""
    # Placeholder account_ids cannot have valid brokers
    if _is_placeholder_account_id(account_id):
        return False
    
    # Check if broker client exists and is not PaperBroker (for execution purposes)
    client = account_manager.get_account_client(account_id)
    if not client:
        return False
    
    # PaperBroker is not a valid execution broker
    from src.core.paper_broker import PaperBroker
    if isinstance(client, PaperBroker):
        return False
    
    return True


class WorkingTradingSystem:
    def __init__(self):
        # Defer OANDA_API_KEY check to runtime (allows paper-mode testing)
        if 'OANDA_API_KEY' not in os.environ:
            logger.warning("⚠️ OANDA_API_KEY not set - paper mode only")
        
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        
        # Get account configs from YAML (even if broker not initialized)
        # This allows scanning to run with paper accounts
        self.account_configs = self.account_manager.account_configs
        self.account_ids_for_scanning = list(self.account_configs.keys()) if self.account_configs else []
        
        self.strategies = {
            'momentum': MomentumTradingStrategy(),
            'gold': GoldScalpingStrategy()
        }
        self.order_managers = {}
        
        # Determine execution eligibility
        can_execute, exec_reason = _can_execute()
        self.execution_enabled = can_execute
        
        # Count accounts with valid execution brokers (non-placeholder, non-PaperBroker)
        execution_ready_accounts = []
        if can_execute:
            for account_id in self.active_accounts:
                if _has_valid_broker(account_id, self.account_manager):
                    execution_ready_accounts.append(account_id)
                    try:
                        self.order_managers[account_id] = OrderManager(account_id=account_id)
                    except Exception as e:
                        logger.warning(f"⚠️ Could not initialize OrderManager for {account_id}: {e}")
        
        if not can_execute:
            logger.info(f"📄 Execution disabled ({exec_reason}) - signals-only mode")
        elif not execution_ready_accounts:
            logger.info(f"📄 Execution enabled but no valid brokers available - signals-only mode")
        else:
            logger.info(f"✅ Execution enabled ({exec_reason}) - {len(execution_ready_accounts)} account(s) ready")
        
        if not self.account_ids_for_scanning:
            logger.info("ℹ️ No accounts configured in YAML - scanning will run with default instruments")
        else:
            logger.info(f"✅ Working Trading System initialized")
            logger.info(f"   Accounts for scanning: {len(self.account_ids_for_scanning)}")
            logger.info(f"   Accounts with execution capability: {len(execution_ready_accounts)}")
    
    def scan_and_execute(self):
        """Scan for opportunities and EXECUTE trades immediately
        
        Always runs scanning even if no broker accounts are available.
        Uses account configs from YAML to determine which accounts/strategies to test.
        """
        logger.info("🔍 SCANNING FOR OPPORTUNITIES...")
        
        all_signals = []
        
        # Use account_ids from configs (paper accounts work even without broker)
        accounts_to_scan = self.account_ids_for_scanning if self.account_ids_for_scanning else ['default']
        
        # Get market data for all accounts (or use paper broker if no real broker)
        for account_id in accounts_to_scan:
            try:
                # Get broker client (may be PaperBroker or OandaClient)
                client = self.account_manager.get_account_client(account_id)
                
                # If no client available, create a temporary paper broker for scanning
                if not client:
                    from src.core.paper_broker import PaperBroker
                    config = self.account_configs.get(account_id)
                    currency = config.instruments[0].split('_')[1] if config and config.instruments else "USD"
                    client = PaperBroker(account_id=account_id, currency=currency)
                    logger.debug(f"📄 Using temporary paper broker for scanning: {account_id[-3:]}")
                
                # Get instruments from account config, or use defaults
                if account_id in self.account_configs:
                    config = self.account_configs[account_id]
                    instruments = config.instruments if config.instruments else ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']
                else:
                    instruments = ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD']
                
                market_data = client.get_current_prices(instruments)
                
                # Get strategy for this account (from config or default)
                if account_id in self.account_configs:
                    config = self.account_configs[account_id]
                    strategy_name = config.strategy_name
                    # Map strategy name to strategy instance
                    if strategy_name == 'momentum':
                        strategy = self.strategies['momentum']
                    elif strategy_name in ('gold_scalping', 'gold_scalping_optimized'):
                        strategy = self.strategies['gold']
                    else:
                        strategy = self.strategies['momentum']  # Default
                else:
                    # Test all strategies if no specific account config
                    strategy = None
                    strategies_to_test = self.strategies
                
                # Test strategy(ies)
                if strategy:
                    # Single strategy for this account
                    try:
                        signals = strategy.analyze_market(market_data)
                        if signals:
                            logger.info(f"📊 {strategy_name} generated {len(signals)} signals for account {account_id[-3:]}")
                            for signal in signals:
                                signal.account_id = account_id
                                all_signals.append(signal)
                    except Exception as e:
                        logger.warning(f"⚠️ {strategy_name} failed for account {account_id[-3:]}: {e}")
                else:
                    # Test all strategies (fallback)
                    for strategy_name, strategy in strategies_to_test.items():
                        try:
                            signals = strategy.analyze_market(market_data)
                            if signals:
                                logger.info(f"📊 {strategy_name} generated {len(signals)} signals")
                                for signal in signals:
                                    signal.account_id = account_id
                                    all_signals.append(signal)
                        except Exception as e:
                            logger.warning(f"⚠️ {strategy_name} failed: {e}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to get market data for account {account_id[-3:]}: {e}")
        
        logger.info(f"📊 Total signals generated: {len(all_signals)}")
        
        # EXECUTE TRADES (only if execution is enabled and order managers are available)
        executed_trades = 0
        if not self.execution_enabled:
            logger.info(f"📄 Execution disabled (signals-only) — signals generated: {len(all_signals)}, executed: 0")
            return len(all_signals)  # Return signal count, not executed count
        
        if not self.order_managers:
            logger.info(f"📄 Execution enabled but no order managers available — signals generated: {len(all_signals)}, executed: 0")
            return len(all_signals)  # Return signal count, not executed count
        
        for signal in all_signals:
            try:
                account_id = signal.account_id
                order_manager = self.order_managers[account_id]
                
                logger.info(f"🚀 EXECUTING TRADE: {signal.instrument} {signal.side.value} on account {account_id[-3:]}")
                
                # Calculate position size (1% risk)
                account_info = order_manager.oanda_client.get_account_info()
                risk_amount = account_info.balance * 0.01
                
                # Calculate stop distance
                if signal.side.value == 'BUY':
                    stop_distance = signal.entry_price - signal.stop_loss
                else:
                    stop_distance = signal.stop_loss - signal.entry_price
                
                position_size = risk_amount / stop_distance if stop_distance > 0 else 10000
                
                # Place the order
                gate = ExecutionGate()
                result = gate.place_market_order(
                    instrument=signal.instrument,
                    units=int(position_size),
                    account_id=account_id,
                    exec_fn=lambda: order_manager.oanda_client.place_market_order(
                        instrument=signal.instrument,
                        side=signal.side.value,
                        units=int(position_size),
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit
                    ),
                    meta={"source": "working_trading_system", "path": "place_market_order"}
                )
                
                if result:
                    executed_trades += 1
                    logger.info(f"✅ TRADE EXECUTED: {signal.instrument} {signal.side.value} - Units: {int(position_size)}")
                else:
                    logger.error(f"❌ TRADE FAILED: {signal.instrument} {signal.side.value}")
                    
            except Exception as e:
                logger.error(f"❌ Trade execution failed: {e}")
        
        if executed_trades > 0:
            logger.info(f"🎯 EXECUTED {executed_trades} TRADES")
        else:
            logger.info(f"📄 Execution enabled but no trades executed — signals generated: {len(all_signals)}, executed: 0")
        return executed_trades

def run_forever(max_iterations: int = 0) -> None:
    """Run continuous scanning"""
    logger.info("🚀 STARTING WORKING TRADING SYSTEM")
    
    system = WorkingTradingSystem()
    
    # Run continuous scanning
    i = 0
    while True:
        try:
            executed = system.scan_and_execute()
            logger.info(f"⏰ Next scan in 30 seconds... (Executed {executed} trades)")
            
            i += 1
            if max_iterations > 0 and i >= max_iterations:
                logger.info(f"🛑 Reached max iterations ({max_iterations}), stopping.")
                break
            
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("🛑 Trading system stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            time.sleep(10)

def main():
    """Main trading loop"""
    run_forever()

if __name__ == "__main__":
    # BLOCKED: Direct execution bypasses canonical entrypoint and safety gates
    # Use canonical entrypoint: python -m runner_src.runner.main
    import sys
    print("❌ BLOCKED: Direct execution of working_trading_system.py is not allowed.")
    print("   Use the canonical entrypoint: python -m runner_src.runner.main")
    print("   This ensures proper safety gates, execution controls, and environment setup.")
    sys.exit(1)


