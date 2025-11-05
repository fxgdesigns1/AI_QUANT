#!/usr/bin/env python3
import logging
from ai_trading_system import AITradingSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    system = AITradingSystem()
    system.trading_enabled = True
    system.run_trading_cycle()
    print("One trading cycle finished.")
