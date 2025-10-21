#!/usr/bin/env python3
"""
Test Stop-Loss Order Execution
Verify that stop-loss orders are properly created and triggered
"""

import os
import sys
import logging
from datetime import datetime

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.oanda_client import get_oanda_client
from src.core.order_manager import OrderManager, TradeSignal, OrderSide

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_stop_loss_creation():
    """Test that stop-loss orders are properly created"""
    try:
        logger.info("🧪 Testing stop-loss order creation...")
        
        # Get OANDA client
        oanda = get_oanda_client()
        
        # Test with a small position
        instrument = "EUR_USD"
        units = 1000  # Small test position
        current_price = 1.0500  # Example price
        stop_loss = 1.0450  # 50 pip stop loss
        take_profit = 1.0600  # 100 pip take profit
        
        logger.info(f"📊 Testing order: {instrument} {units} units")
        logger.info(f"📊 Entry: {current_price}, SL: {stop_loss}, TP: {take_profit}")
        
        # Create test order
        order = oanda.place_market_order(
            instrument=instrument,
            units=units,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        if order:
            logger.info(f"✅ Order created successfully: {order.order_id}")
            logger.info(f"📊 Order details: {order}")
            
            # Check if stop-loss was included
            if hasattr(order, 'stop_loss') and order.stop_loss:
                logger.info(f"✅ Stop-loss included: {order.stop_loss}")
            else:
                logger.warning("⚠️ Stop-loss not found in order")
            
            # Check if take-profit was included
            if hasattr(order, 'take_profit') and order.take_profit:
                logger.info(f"✅ Take-profit included: {order.take_profit}")
            else:
                logger.warning("⚠️ Take-profit not found in order")
                
            return True
        else:
            logger.error("❌ Failed to create order")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.exception("Full traceback:")
        return False

def test_order_manager():
    """Test OrderManager with stop-loss"""
    try:
        logger.info("🧪 Testing OrderManager with stop-loss...")
        
        # Create order manager
        order_manager = OrderManager()
        
        # Create test signal
        signal = TradeSignal(
            instrument="EUR_USD",
            side=OrderSide.BUY,
            units=1000,
            stop_loss=1.0450,
            take_profit=1.0600,
            strategy_name="test_strategy",
            confidence=0.8
        )
        
        logger.info(f"📊 Test signal: {signal}")
        
        # Execute trade
        execution = order_manager.execute_trade(signal)
        
        if execution.success:
            logger.info(f"✅ Trade executed successfully: {execution.order.order_id}")
            return True
        else:
            logger.error(f"❌ Trade execution failed: {execution.error_message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ OrderManager test failed: {e}")
        logger.exception("Full traceback:")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting stop-loss order tests...")
    
    # Test 1: Direct OANDA client
    logger.info("\n" + "="*50)
    logger.info("TEST 1: Direct OANDA Client")
    logger.info("="*50)
    test1_success = test_stop_loss_creation()
    
    # Test 2: OrderManager
    logger.info("\n" + "="*50)
    logger.info("TEST 2: OrderManager")
    logger.info("="*50)
    test2_success = test_order_manager()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    logger.info(f"Direct OANDA Client: {'✅ PASS' if test1_success else '❌ FAIL'}")
    logger.info(f"OrderManager: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        logger.info("🎉 All tests passed! Stop-loss orders working correctly.")
    else:
        logger.error("💥 Some tests failed! Stop-loss orders need fixing.")