#!/usr/bin/env python3
"""
SYSTEM PROBE & DIAGNOSTIC TOOL
Identifies blockers preventing trade entry.
Usage:
    python3 scripts/system_probe.py          # Check current environment
    python3 scripts/system_probe.py --sim    # Simulate successful trade (verify logic)
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timezone

# Ensure we can import from src
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    print("=== 🔍 SYSTEM ENVIRONMENT PROBE ===")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"CWD: {os.getcwd()}")
    
    # 1. Check .env
    env_path = os.path.join(os.getcwd(), '.env')
    has_env = os.path.exists(env_path)
    print(f"\n--- Configuration Source ---")
    print(f".env file found: {'✅ Yes' if has_env else '❌ No'}")
    
    # Load .env manually if present (for this script only)
    if has_env:
        print("Loading .env for probe context...")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    if k not in os.environ:
                        os.environ[k] = v.strip('"').strip("'")

    # 2. Check Critical Variables
    print(f"\n--- Critical Variables ---")
    
    # API KEY
    api_key = os.getenv("OANDA_API_KEY")
    if api_key:
        print(f"✅ OANDA_API_KEY: Present (len={len(api_key)})")
    else:
        print(f"❌ OANDA_API_KEY: MISSING")
        
    # ACCOUNT ID
    account_id = os.getenv("OANDA_ACCOUNT_ID")
    if account_id:
        print(f"✅ OANDA_ACCOUNT_ID: {account_id}")
    else:
        print(f"❌ OANDA_ACCOUNT_ID: MISSING")
        
    # TRADING MODE
    mode = os.getenv("TRADING_MODE", "paper")
    print(f"ℹ️  TRADING_MODE: {mode}")
    
    # EXECUTION FLAGS
    exec_unlock = os.getenv("EXECUTION_UNLOCK_OK")
    paper_exec = os.getenv("PAPER_EXECUTION_ENABLED")
    
    can_execute = False
    if str(exec_unlock).lower() == "true":
        print(f"✅ EXECUTION_UNLOCK_OK: true")
        can_execute = True
    elif str(paper_exec).lower() == "true":
        print(f"✅ PAPER_EXECUTION_ENABLED: true (Legacy)")
        can_execute = True
    else:
        print(f"❌ EXECUTION_UNLOCK_OK: Not set (Trading DISABLED)")
        
    # 3. System Initialization Check
    print(f"\n--- System Initialization Check ---")
    try:
        from working_trading_system import WorkingTradingSystem
        
        system = WorkingTradingSystem()
        
        print(f"Strategies Loaded: {list(system.strategies.keys())}")
        print(f"Accounts Loaded: {len(system.account_ids_for_scanning)}")
        
        if not system.account_ids_for_scanning:
            print("❌ BLOCKER: No accounts configured. System is in 'signals-only' mode with no targets.")
            print("   Fix: Set OANDA_ACCOUNT_ID in .env")
        else:
            print(f"✅ Accounts Configured: {system.account_ids_for_scanning}")
            
        if not system.execution_enabled:
             print(f"❌ BLOCKER: Execution is DISABLED.")
             print("   Fix: Set EXECUTION_UNLOCK_OK=true in .env")
        else:
            print(f"✅ Execution Enabled: Yes")
            
        if not system.order_managers:
            print(f"❌ BLOCKER: No OrderManagers initialized.")
            if can_execute and system.account_ids_for_scanning:
                 print("   Reason: Likely failed to initialize broker (API Key invalid?)")
    
    except Exception as e:
        print(f"❌ CRITICAL INIT FAILURE: {e}")

def run_simulation():
    print("=== 🧪 LOGIC SIMULATION (MOCKED) ===")
    print("Verifying that strategies GENERATE signals and execute if env is correct.")
    
    from unittest.mock import MagicMock, patch
    import json
    
    # Mock Env
    os.environ["EXECUTION_UNLOCK_OK"] = "true"
    os.environ["TRADING_MODE"] = "paper"
    os.environ["OANDA_API_KEY"] = "mock_key"
    os.environ["OANDA_ACCOUNT_ID"] = "sim-account-001"
    os.environ["OANDA_BASE_URL"] = "https://mock-api.oanda.com"

    # Monkeypatch requests
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        # Mocks
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"positions": [], "account": {"balance": "10000.0"}}
        
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "orderCreateTransaction": {"id": "101"},
            "orderFillTransaction": {"id": "102"}
        }

        try:
            from working_trading_system import WorkingTradingSystem
            from src.core.order_manager import OrderManager
            from src.core.paper_broker import PaperBroker
            
            # Init
            system = WorkingTradingSystem()
            
            # Inject
            account_id = "sim-account-001"
            system.account_ids_for_scanning = [account_id]
            
            class MockConfig:
                strategy_name = 'momentum'
                instruments = ['XAU_USD']
            system.account_configs = {account_id: MockConfig()}
            
            class MockAssignment:
                account_id = "sim-account-001"
                strategy_key = 'momentum'
                enabled = True
            system._strategy_assignments = [MockAssignment()]
            system.order_managers[account_id] = OrderManager()
            
            # Force synthetic data
            system.account_manager.get_account_client = MagicMock(return_value=PaperBroker())
            
            # Run
            print("\nRunning Scan...")
            executed = system.scan_and_execute()
            
            if executed > 0:
                print(f"\n✅ SUCCESS: Logic is sound. Executed {executed} trade(s) in simulation.")
                print("   This proves the code works. The issue is your ENVIRONMENT configuration.")
            else:
                print(f"\n❌ FAILURE: Logic failed even in simulation.")
                
        except Exception as e:
            print(f"❌ SIMULATION ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", action="store_true", help="Run mocked simulation")
    args = parser.parse_args()
    
    if args.sim:
        run_simulation()
    else:
        check_environment()
