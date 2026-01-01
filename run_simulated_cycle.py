import sys
import os
import importlib.util
from datetime import datetime


def main():
    """
    Runs a single, simulated, end-to-end trading cycle to verify system health
    without placing any real orders or making live network calls.
    """
    project_root = os.getcwd()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # --- Safely import modules by path to avoid package issues ---
    try:
        # Load ai_trading_system module
        ats_path = os.path.join(project_root, 'ai_trading_system.py')
        spec = importlib.util.spec_from_file_location('ai_trading_system', ats_path)
        ats_module = importlib.util.module_from_spec(spec)
        # Add parent directories to sys.path to mimic how ai_trading_system.py does it
        # This helps resolve sibling modules like src.*
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_for_imports = os.path.abspath(os.path.join(script_dir, "."))
        if project_root_for_imports not in sys.path:
            sys.path.insert(0, project_root_for_imports)
        
        spec.loader.exec_module(ats_module)
        AITradingSystem = getattr(ats_module, 'AITradingSystem')

        # Ensure strategy registry path is available for dynamic loading
        registry_parent_path = os.path.join(project_root, 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system')
        if os.path.exists(os.path.join(registry_parent_path, 'src', 'strategies', 'registry.py')) and registry_parent_path not in sys.path:
            sys.path.insert(0, registry_parent_path)
        from src.strategies.registry import create_strategy
    except (ModuleNotFoundError, FileNotFoundError, ImportError) as e:
        print(f"❌ CRITICAL: Failed to load core modules for simulation: {e}")
        return

    print("✅ Core modules loaded successfully.")

    # --- Create and configure a simulated system instance ---
    sim_account_id = 'sim-acct-001'
    sim_config = {'trading_pairs': ['GBP_USD'], 'strategy': 'momentum_trading'}
    system_instance = AITradingSystem(account_id=sim_account_id, account_config=sim_config)

    # --- Attach and configure a live strategy instance ---
    try:
        strategy = create_strategy('momentum_trading')
        strategy.account_id = system_instance.account_id
        # Relax filters to guarantee a signal is generated for the test
        strategy.min_adx = 0
        strategy.min_momentum = 0
        strategy.min_volume = 0
        strategy.require_trend_continuation = False
        # Create synthetic price history to ensure calculations can run
        inst = strategy.instruments[0]
        base_price = 1.2500
        prices = [round(base_price * (1 + 0.0005 * i), 5) for i in range(250)]
        strategy.price_history[inst] = prices
        system_instance.strategy = strategy
        print(f"✅ Attached and configured '{type(strategy).__name__}' strategy for simulation.")
    except Exception as e:
        print(f"❌ CRITICAL: Failed to create and configure strategy: {e}")
        return

    # --- Monkey-patch network-dependent methods for safe, local execution ---
    # 1. Patch price fetching to return synthetic data
    latest_price = prices[-1]
    synthetic_prices = {inst: {'bid': latest_price - 0.0001, 'ask': latest_price + 0.0001, 'mid': latest_price, 'spread': 0.0002}}
    def fake_get_current_prices():
        print("   (MOCK) Returning synthetic market prices.")
        return synthetic_prices
    system_instance.get_current_prices = fake_get_current_prices

    # 2. Patch trade execution to record signals instead of sending orders
    executed_signals = []
    def fake_execute_trade(signal):
        executed_signals.append(signal)
        print(f"   (MOCK) Executing trade for: {signal.get('instrument') if isinstance(signal, dict) else getattr(signal, 'instrument', 'Unknown')}")
        return True
    system_instance.execute_trade = fake_execute_trade

    print("✅ System monkey-patched for safe local simulation.")

    # --- Run one full, simulated trading cycle ---
    print("\n🚀 Running one simulated trading cycle...")
    try:
        system_instance.run_trading_cycle()
    except Exception as e:
        print(f"❌ CRITICAL: The trading cycle failed with an error: {e}")
        return

    # --- Report Results ---
    print("\n--- SIMULATION COMPLETE ---")
    print(f"Total signals mock-executed: {len(executed_signals)}")

    if executed_signals:
        signal_details = executed_signals[0]
        print(f"\n✅ SUCCESS: End-to-end cycle is working correctly.")
        print("   - Strategy generated a signal as expected.")
        print("   - Main loop received the signal.")
        print("   - Signal was routed to the (mock) execution function.")
        print("\n--- Sample Executed Signal ---")
        print(signal_details)
    else:
        print("\n⚠️ WARNING: No signals were generated during the cycle.")
        print("   - The system ran without errors, but the strategy's conditions were not met.")
        print("   - This may be normal, but check strategy logic if signals were expected.")


if __name__ == "__main__":
    main()
