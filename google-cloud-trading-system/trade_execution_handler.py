#!/usr/bin/env python3
"""
TRADE EXECUTION HANDLER
======================

Handles direct trade execution commands like "enter usdjpy long on account 001"
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import re

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.yaml_manager import get_yaml_manager
from src.core.oanda_client import OandaClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradeExecutionHandler:
    """Handles direct trade execution commands"""
    
    def __init__(self):
        self.semi_auto_account_id = "101-004-30719775-001"
        self.load_accounts()
        
    def load_accounts(self):
        """Load trading accounts"""
        try:
            yaml_mgr = get_yaml_manager()
            self.accounts_config = yaml_mgr.get_all_accounts()
            logger.info(f"✅ Loaded {len(self.accounts_config)} accounts")
        except Exception as e:
            logger.error(f"❌ Error loading accounts: {e}")
            self.accounts_config = []
    
    def parse_trade_command(self, command: str) -> Optional[Dict]:
        """Parse trade execution command"""
        command = command.lower().strip()
        
        # Pattern: "enter [instrument] [direction] on account [account]"
        patterns = [
            r'enter\s+(\w+)\s+(long|short|buy|sell)\s+on\s+account\s+(\d+)',
            r'enter\s+(\w+)\s+(long|short|buy|sell)\s+on\s+account\s+(\w+)',
            r'(\w+)\s+(long|short|buy|sell)\s+on\s+account\s+(\d+)',
            r'(\w+)\s+(long|short|buy|sell)\s+on\s+account\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                instrument = match.group(1).upper()
                direction = match.group(2).lower()
                account_ref = match.group(3)
                
                # Normalize instrument
                if '_' not in instrument:
                    if instrument == 'EURUSD':
                        instrument = 'EUR_USD'
                    elif instrument == 'GBPUSD':
                        instrument = 'GBP_USD'
                    elif instrument == 'USDJPY':
                        instrument = 'USD_JPY'
                    elif instrument == 'AUDUSD':
                        instrument = 'AUD_USD'
                    elif instrument == 'XAUUSD':
                        instrument = 'XAU_USD'
                
                # Normalize direction
                if direction in ['long', 'buy']:
                    direction = 'BUY'
                elif direction in ['short', 'sell']:
                    direction = 'SELL'
                
                # Map account reference
                account_id = self._map_account_reference(account_ref)
                
                return {
                    'instrument': instrument,
                    'direction': direction,
                    'account_id': account_id,
                    'original_command': command
                }
        
        return None
    
    def _map_account_reference(self, account_ref: str) -> str:
        """Map account reference to actual account ID"""
        account_ref = account_ref.lower()
        
        if account_ref in ['001', '1', 'semi', 'semi-auto']:
            return self.semi_auto_account_id
        elif account_ref in ['002', '2']:
            return "101-004-30719775-002"
        elif account_ref in ['003', '3']:
            return "101-004-30719775-003"
        else:
            # Try to find by account ID
            for account in self.accounts_config:
                if account_ref in account.get('id', '').lower():
                    return account['id']
            
            # Default to semi-auto account
            return self.semi_auto_account_id
    
    def execute_trade(self, parsed_command: Dict) -> Dict:
        """Execute the trade"""
        try:
            instrument = parsed_command['instrument']
            direction = parsed_command['direction']
            account_id = parsed_command['account_id']
            
            logger.info(f"🔄 Executing trade: {instrument} {direction} on {account_id}")
            
            # Create OANDA client
            client = OandaClient(account_id=account_id)
            
            # Get current price
            prices = client.get_current_prices([instrument], force_refresh=True)
            
            if instrument not in prices:
                return {
                    'success': False,
                    'error': f'No price data available for {instrument}',
                    'instrument': instrument,
                    'direction': direction,
                    'account_id': account_id
                }
            
            current_price = prices[instrument]
            mid_price = (current_price.bid + current_price.ask) / 2
            spread = current_price.ask - current_price.bid
            
            # Calculate position size
            units = self._calculate_position_size(instrument, account_id)
            
            # Calculate stop loss and take profit
            if 'XAU' in instrument:  # Gold
                tp_distance = 10.0  # $10 take profit
                sl_distance = 5.0   # $5 stop loss
            elif 'JPY' in instrument:  # JPY pairs
                tp_distance = 0.50  # 50 pip TP
                sl_distance = 0.25  # 25 pip SL
            else:  # Regular forex
                tp_distance = 0.0050  # 50 pip TP
                sl_distance = 0.0025  # 25 pip SL
            
            # Determine units direction
            if direction == 'SELL':
                units = -units
            
            logger.info(f"📊 {instrument}: {current_price.bid:.5f}/{current_price.ask:.5f}")
            logger.info(f"💰 Units: {units}, TP: {tp_distance}, SL: {sl_distance}")
            
            # Calculate stop loss and take profit prices
            if direction == 'BUY':
                stop_loss_price = mid_price - sl_distance
                take_profit_price = mid_price + tp_distance
            else:  # SELL
                stop_loss_price = mid_price + sl_distance
                take_profit_price = mid_price - tp_distance
            
            # Place market order
            result = client.place_market_order(
                instrument=instrument,
                units=units,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
            
            if result:
                # Extract order information from OandaOrder object
                trade_id = getattr(result, 'order_id', 'N/A')
                order_id = getattr(result, 'order_id', 'N/A')
                instrument_result = getattr(result, 'instrument', instrument)
                units_result = getattr(result, 'units', abs(units))
                
                logger.info(f"✅ TRADE EXECUTED: {instrument} {direction}")
                logger.info(f"📋 Order ID: {order_id}")
                
                return {
                    'success': True,
                    'instrument': instrument,
                    'direction': direction,
                    'account_id': account_id,
                    'trade_id': trade_id,
                    'order_id': order_id,
                    'units': abs(units),
                    'price': mid_price,
                    'spread': spread,
                    'take_profit': tp_distance,
                    'stop_loss': sl_distance,
                    'executed_at': datetime.now().isoformat(),
                    'message': f'✅ TRADE EXECUTED: {instrument} {direction} on {account_id}'
                }
            else:
                error = 'No result returned'
                logger.error(f"❌ TRADE FAILED: {error}")
                
                return {
                    'success': False,
                    'error': error,
                    'instrument': instrument,
                    'direction': direction,
                    'account_id': account_id,
                    'message': f'❌ TRADE FAILED: {error}'
                }
                
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            return {
                'success': False,
                'error': str(e),
                'instrument': parsed_command.get('instrument', 'N/A'),
                'direction': parsed_command.get('direction', 'N/A'),
                'account_id': parsed_command.get('account_id', 'N/A'),
                'message': f'❌ EXECUTION ERROR: {str(e)}'
            }
    
    def _calculate_position_size(self, instrument: str, account_id: str) -> int:
        """Calculate position size based on risk management"""
        try:
            # Get account balance
            client = OandaClient(account_id=account_id)
            account_info = client.get_account_info()
            balance = getattr(account_info, 'balance', 100000)
            
            # Calculate position size (1% risk)
            risk_amount = balance * 0.01  # 1% of balance
            
            if 'XAU' in instrument:  # Gold
                return int(risk_amount / 10)  # Smaller units for gold
            elif 'JPY' in instrument:  # JPY pairs
                return int(risk_amount / 100)  # Standard forex units
            else:  # Regular forex
                return int(risk_amount / 100)  # Standard forex units
                
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return 1000  # Default fallback
    
    def process_trade_command(self, command: str) -> Dict:
        """Process a trade execution command"""
        logger.info(f"🎯 Processing trade command: {command}")
        
        # Parse the command
        parsed = self.parse_trade_command(command)
        
        if not parsed:
            return {
                'success': False,
                'error': 'Could not parse trade command',
                'message': '❌ Invalid command format. Use: "enter USDJPY long on account 001"',
                'examples': [
                    'enter USDJPY long on account 001',
                    'enter EUR_USD buy on account 001',
                    'enter XAU_USD short on account 001'
                ]
            }
        
        # Execute the trade
        result = self.execute_trade(parsed)
        
        return result

def test_trade_execution():
    """Test trade execution functionality"""
    handler = TradeExecutionHandler()
    
    # Test commands
    test_commands = [
        "enter usdjpy long on account 001",
        "enter EUR_USD buy on account 001",
        "enter XAU_USD short on account 001",
        "GBP_USD sell on account 001"
    ]
    
    print("🧪 TESTING TRADE EXECUTION HANDLER")
    print("=" * 60)
    
    for command in test_commands:
        print(f"\n🎯 Testing: {command}")
        result = handler.process_trade_command(command)
        
        if result['success']:
            print(f"✅ SUCCESS: {result['message']}")
            print(f"   Trade ID: {result.get('trade_id', 'N/A')}")
            print(f"   Units: {result.get('units', 'N/A')}")
        else:
            print(f"❌ FAILED: {result['message']}")
            if 'examples' in result:
                print("   Examples:")
                for example in result['examples']:
                    print(f"     • {example}")

if __name__ == "__main__":
    test_trade_execution()
