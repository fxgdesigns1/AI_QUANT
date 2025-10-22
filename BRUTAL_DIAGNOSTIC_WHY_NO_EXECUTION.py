#!/usr/bin/env python3
"""
BRUTAL DIAGNOSTIC - Why Are Trades Not Executing?
Find the EXACT failure point in the execution chain
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.insert(0, str(Path(__file__).parent / "google-cloud-trading-system"))

print("="*80)
print("🔍 BRUTAL DIAGNOSTIC - WHY NO TRADE EXECUTION?")
print("="*80)
print("\nFinding the EXACT failure point...\n")

# Test 1: Environment & Credentials
print("[TEST 1/10] Checking Credentials & Environment")
print("-"*80)

try:
    from dotenv import load_dotenv
    load_dotenv('google-cloud-trading-system/oanda_config.env')
    
    api_key = os.getenv('OANDA_API_KEY')
    primary_account = os.getenv('PRIMARY_ACCOUNT')
    
    if api_key:
        print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("✗ FAILURE: No API key found")
        
    if primary_account:
        print(f"✓ Primary Account: {primary_account}")
    else:
        print("✗ FAILURE: No primary account")
        
    print(f"✓ Environment: {os.getenv('OANDA_ENVIRONMENT', 'NOT SET')}")
    
except Exception as e:
    print(f"✗ FAILURE loading credentials: {e}")
    api_key = None
    primary_account = None

# Test 2: Network Connectivity
print("\n[TEST 2/10] Testing Network Connectivity")
print("-"*80)

try:
    import socket
    socket.setdefaulttimeout(5)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("api-fxpractice.oanda.com", 443))
    print("✓ Network connection to OANDA API: SUCCESS")
except Exception as e:
    print(f"✗ FAILURE: Cannot reach OANDA API: {e}")
    print("  → This is likely THE problem - no network = no trades")

# Test 3: OANDA Client Initialization
print("\n[TEST 3/10] Testing OANDA Client")
print("-"*80)

try:
    from src.core.oanda_client import OandaClient
    
    if api_key and primary_account:
        client = OandaClient(api_key=api_key, account_id=primary_account)
        print("✓ OANDA Client initialized")
        
        # Test actual API call
        try:
            account_info = client.get_account_summary()
            if account_info:
                print(f"✓ API Connection Working - Balance: ${account_info.get('balance', 'N/A')}")
            else:
                print("✗ FAILURE: API call returned None")
        except Exception as e:
            print(f"✗ FAILURE: Cannot fetch account info: {e}")
    else:
        print("✗ FAILURE: Missing credentials, cannot test client")
        client = None
        
except Exception as e:
    print(f"✗ FAILURE initializing client: {e}")
    client = None

# Test 4: Check Current Prices
print("\n[TEST 4/10] Testing Price Data Access")
print("-"*80)

if client:
    try:
        price = client.get_current_price('EUR_USD')
        if price:
            print(f"✓ Can fetch prices - EUR/USD: {price.get('mid', 'N/A')}")
        else:
            print("✗ FAILURE: get_current_price returned None")
            print("  → If we can't get prices, we can't trade")
    except Exception as e:
        print(f"✗ FAILURE fetching prices: {e}")
else:
    print("✗ SKIPPED: No client available")

# Test 5: Order Manager
print("\n[TEST 5/10] Testing Order Manager")
print("-"*80)

try:
    from src.core.order_manager import OrderManager
    
    if api_key and primary_account:
        order_mgr = OrderManager(api_key=api_key, account_id=primary_account)
        print("✓ Order Manager initialized")
        
        # Check if it has required methods
        if hasattr(order_mgr, 'place_order'):
            print("✓ place_order method exists")
        else:
            print("✗ FAILURE: place_order method missing")
            
        if hasattr(order_mgr, 'place_market_order'):
            print("✓ place_market_order method exists")
        else:
            print("✗ FAILURE: place_market_order method missing")
    else:
        print("✗ FAILURE: Missing credentials")
        order_mgr = None
        
except Exception as e:
    print(f"✗ FAILURE initializing order manager: {e}")
    order_mgr = None

# Test 6: Strategy Loading
print("\n[TEST 6/10] Testing Strategy System")
print("-"*80)

try:
    # Check if strategies exist
    strategy_files = list(Path("google-cloud-trading-system/src/strategies").glob("*.py"))
    print(f"✓ Found {len(strategy_files)} strategy files")
    
    # Try to import a strategy
    from src.strategies.momentum_trading import MomentumTradingStrategy
    print("✓ Can import strategy classes")
    
    # Try to instantiate
    if api_key and primary_account:
        strategy = MomentumTradingStrategy(api_key=api_key, account_id=primary_account)
        print("✓ Strategy instantiated successfully")
        
        # Check critical methods
        if hasattr(strategy, 'generate_signals'):
            print("✓ generate_signals method exists")
        else:
            print("✗ FAILURE: generate_signals missing")
            
        if hasattr(strategy, 'execute_signal'):
            print("✓ execute_signal method exists")
        else:
            print("✗ FAILURE: execute_signal missing - THIS IS CRITICAL")
    else:
        print("⚠ Cannot instantiate strategy - missing credentials")
        
except Exception as e:
    print(f"✗ FAILURE with strategies: {e}")

# Test 7: Check Logs for Signals
print("\n[TEST 7/10] Analyzing Recent Logs for Signals")
print("-"*80)

log_files = [
    "logs/real_system_manual_fix.log",
    "logs/real_system_final.log",
    "google-cloud-trading-system/working_server.log"
]

signals_found = []
execution_attempts = []
execution_failures = []

for log_path in log_files:
    if not Path(log_path).exists():
        continue
        
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()[-5000:]  # Last 5000 lines
            
        for line in lines:
            line_lower = line.lower()
            
            # Look for signals
            if any(word in line_lower for word in ['signal generated', 'opportunity found', 'entry signal']):
                signals_found.append(line.strip())
                
            # Look for execution attempts
            if any(word in line_lower for word in ['placing order', 'executing trade', 'submitting order']):
                execution_attempts.append(line.strip())
                
            # Look for execution failures
            if any(word in line_lower for word in ['order failed', 'execution failed', 'trade rejected', 'insufficient']):
                execution_failures.append(line.strip())
                
    except Exception as e:
        continue

print(f"📊 Signals found in logs: {len(signals_found)}")
if signals_found:
    print("\nMost recent signals:")
    for sig in signals_found[-3:]:
        print(f"  • {sig[:150]}")
else:
    print("  → NO SIGNALS FOUND IN LOGS")
    print("  → Problem: Strategy is not generating signals")

print(f"\n🔧 Execution attempts: {len(execution_attempts)}")
if execution_attempts:
    print("\nMost recent attempts:")
    for attempt in execution_attempts[-3:]:
        print(f"  • {attempt[:150]}")
else:
    print("  → NO EXECUTION ATTEMPTS FOUND")
    print("  → Problem: Signals not being passed to execution")

print(f"\n❌ Execution failures: {len(execution_failures)}")
if execution_failures:
    print("\nRecent failures:")
    for failure in execution_failures[-3:]:
        print(f"  • {failure[:150]}")

# Test 8: Configuration Check
print("\n[TEST 8/10] Checking System Configuration")
print("-"*80)

try:
    # Check if trading is enabled
    mock_trading = os.getenv('MOCK_TRADING', 'False')
    development_mode = os.getenv('DEVELOPMENT_MODE', 'False')
    forced_trading = os.getenv('FORCED_TRADING_MODE', 'disabled')
    
    print(f"MOCK_TRADING: {mock_trading}")
    print(f"DEVELOPMENT_MODE: {development_mode}")
    print(f"FORCED_TRADING_MODE: {forced_trading}")
    
    if mock_trading.lower() == 'true':
        print("⚠ WARNING: MOCK_TRADING is enabled - no real trades")
        
    if development_mode.lower() == 'true':
        print("⚠ WARNING: DEVELOPMENT_MODE is enabled - may limit trading")
        
    if forced_trading.lower() != 'enabled':
        print("⚠ WARNING: FORCED_TRADING_MODE not enabled - may be too conservative")
        
except Exception as e:
    print(f"Error checking config: {e}")

# Test 9: Check Account Configuration
print("\n[TEST 9/10] Checking Account Configuration")
print("-"*80)

try:
    from src.core.yaml_manager import YAMLManager
    
    yaml_path = "google-cloud-trading-system/accounts.yaml"
    if Path(yaml_path).exists():
        yaml_mgr = YAMLManager(yaml_path)
        accounts = yaml_mgr.get_all_accounts()
        
        print(f"✓ Found {len(accounts)} configured accounts")
        
        active_count = sum(1 for acc in accounts if acc.get('active', False))
        print(f"✓ Active accounts: {active_count}")
        
        if active_count == 0:
            print("✗ CRITICAL: NO ACTIVE ACCOUNTS")
            print("  → This is THE problem - all accounts disabled")
            
        for acc in accounts[:3]:
            status = "ACTIVE" if acc.get('active', False) else "INACTIVE"
            print(f"  • {acc.get('name', 'Unknown')}: {status}")
            
    else:
        print("✗ FAILURE: accounts.yaml not found")
        
except Exception as e:
    print(f"✗ FAILURE checking accounts: {e}")

# Test 10: Live Signal Generation Test
print("\n[TEST 10/10] LIVE SIGNAL GENERATION TEST")
print("-"*80)

if client and api_key and primary_account:
    try:
        print("Attempting to generate a signal RIGHT NOW...")
        
        from src.strategies.momentum_trading import MomentumTradingStrategy
        
        strategy = MomentumTradingStrategy(
            api_key=api_key,
            account_id=primary_account,
            trading_pairs=['EUR_USD'],
            timeframe='5m'
        )
        
        # Try to generate signals
        signals = strategy.generate_signals('EUR_USD')
        
        if signals:
            print(f"✓ SIGNAL GENERATED: {signals}")
            print("\nNow testing if it would execute...")
            
            # Check if execute_signal exists and works
            if hasattr(strategy, 'execute_signal'):
                print("✓ execute_signal method exists")
                print("\n⚠ NOT actually executing (this is a diagnostic)")
                print("But the capability exists")
            else:
                print("✗ CRITICAL: execute_signal method MISSING")
                print("  → Signals generated but cannot execute")
        else:
            print("⚠ No signal generated (market conditions may not meet criteria)")
            print("  Try again during London/NY overlap (1-5 PM London)")
            
    except Exception as e:
        print(f"✗ FAILURE in live test: {e}")
        import traceback
        traceback.print_exc()
else:
    print("✗ SKIPPED: No client or credentials available")

# DIAGNOSIS SUMMARY
print("\n" + "="*80)
print("🔍 DIAGNOSIS SUMMARY")
print("="*80)

problems = []

# Analyze results
if not api_key:
    problems.append("❌ CRITICAL: No API credentials")
    
if signals_found and not execution_attempts:
    problems.append("❌ CRITICAL: Signals generated but NEVER passed to execution")
    problems.append("   → The gap is between signal generation and order placement")
    
if execution_attempts and execution_failures:
    problems.append("❌ Execution attempted but failed")
    problems.append("   → Check failure messages in logs")
    
if not signals_found:
    problems.append("❌ No signals being generated")
    problems.append("   → Check strategy logic and market conditions")

if problems:
    print("\n🚨 PROBLEMS IDENTIFIED:\n")
    for i, problem in enumerate(problems, 1):
        print(f"{i}. {problem}")
else:
    print("\n✅ All systems operational")
    print("   If still no trades, check:")
    print("   - Market conditions may not meet strategy criteria")
    print("   - Trading during optimal hours (1-5 PM London)?")
    print("   - Risk limits reached?")

# RECOMMENDED FIX
print("\n" + "="*80)
print("💡 RECOMMENDED FIX")
print("="*80)

if not api_key:
    print("\n1. Fix credentials:")
    print("   cd google-cloud-trading-system")
    print("   cat oanda_config.env")
    print("   # Verify OANDA_API_KEY is set")

elif signals_found and not execution_attempts:
    print("\n1. THE PROBLEM: Signals generated but not executed")
    print("   This means the connection between signal → execution is broken")
    print("\n2. Check these files:")
    print("   - src/core/strategy_executor.py (should call execute_signal)")
    print("   - src/strategies/*.py (should have execute_signal method)")
    print("   - main.py (should have execution loop)")
    print("\n3. Likely causes:")
    print("   - Strategy executor not configured")
    print("   - Execution method not called")
    print("   - Silent failure (no error, no execution)")

else:
    print("\n1. Run the trading system manually:")
    print("   cd google-cloud-trading-system")
    print("   python3 main.py")
    print("\n2. Watch for:")
    print("   - Signal generation messages")
    print("   - Execution attempt messages")
    print("   - Any error messages")

print("\n" + "="*80)
print("✅ DIAGNOSTIC COMPLETE")
print("="*80)
print("\nSaved detailed results for analysis")

