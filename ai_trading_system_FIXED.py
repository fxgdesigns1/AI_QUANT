import sys
import os
import logging
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from typing import List, Any, Dict

# --- Reliable Path Resolution ---
# Get the directory where the script is located, then construct absolute paths from there.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
# --------------------------------

# --- Core Imports ---
from src.core.strategy_executor import get_multi_strategy_executor
from src.core.account_manager import get_account_manager
from src.core.strategy_manager import get_strategy_manager
from src.core.streaming_data_feed import get_optimized_data_feed
from src.analytics.topdown_scheduler import integrate_with_trading_system

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AI_Trading_System_Main")

def main():
    logger.info("🤖 AI Trading System Starting (YAML Architecture)...")

    try:
        # Construct the absolute path to the config file
        config_path = os.path.join(SCRIPT_DIR, "strategy_config.yaml")

        # 1. Get singleton instances of core managers
        account_manager = get_account_manager()
        strategy_manager = get_strategy_manager(config_file=config_path)
        multi_strategy_executor = get_multi_strategy_executor()
        oanda_client = get_oanda_client() # Shared OANDA client for data feed

        # 2. Initialize managers (they self-initialize on get, but ensure config is loaded)
        # AccountManager initializes itself from env vars
        multi_strategy_executor.initialize_executors()
        if not multi_strategy_executor.executors:
            logger.critical("❌ No strategy executors were initialized. System cannot trade. Check configurations and logs.")
            return

        # 3. Start Data Feed
        data_feed = get_optimized_data_feed()
        data_feed.start()
        logger.info("✅ Data Feed Started.")

        # 4. Integrate Top-Down Analysis
        topdown_scheduler = integrate_with_trading_system(multi_strategy_executor)
        scheduler_thread = threading.Thread(
            target=topdown_scheduler.run_scheduler,
            daemon=True
        )
        scheduler_thread.start()
        logger.info("✅ Top-Down Scheduler Integrated and Running.")

        # 5. Start All Strategy Executors
        multi_strategy_executor.start_all_executors()
        logger.info("🚀 System is live. All executors are running.")

        # 6. Keep Main Thread Alive
        while True:
            time.sleep(60)

    except Exception as e:
        logger.critical(f"❌ A critical error occurred during system startup: {e}")
        logger.exception("Traceback:")
    except KeyboardInterrupt:
        logger.info("🛑 System shutting down by user request...")
        if 'multi_strategy_executor' in locals():
            multi_strategy_executor.stop_all_executors()
        logger.info("✅ All executors stopped.")

if __name__ == "__main__":
    main()
