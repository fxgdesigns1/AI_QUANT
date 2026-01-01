#!/usr/bin/env python3
"""
Verify the new dynamic_multi_pair_unified strategy is properly installed
"""

import sys
import os

# Add the strategy path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system'))

try:
    from src.strategies.registry import create_strategy, resolve_strategy_key, STRATEGY_REGISTRY
    print("✅ Strategy registry imported successfully")
    
    # Test strategy key resolution
    key = resolve_strategy_key("dynamic_multi_pair_unified")
    print(f"✅ Strategy key resolved: {key}")
    
    if key and key in STRATEGY_REGISTRY:
        print(f"✅ Strategy found in registry: {STRATEGY_REGISTRY[key].display_name}")
        
        # Try to create strategy instance
        try:
            strategy = create_strategy("dynamic_multi_pair_unified")
            if strategy:
                print(f"✅ Strategy instance created successfully")
                print(f"   Name: {strategy.name}")
                print(f"   Instruments: {', '.join(strategy.instruments)}")
                print(f"   Max trades/day: {strategy.max_trades_per_day}")
                print(f"   Position multiplier: {strategy.position_multiplier}x")
                print(f"   Pair configs loaded: {len(strategy.pair_configs)}")
                print("\n✅ Strategy verification PASSED")
            else:
                print("❌ Failed to create strategy instance")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error creating strategy: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print(f"❌ Strategy not found in registry")
        print(f"   Available strategies: {list(STRATEGY_REGISTRY.keys())}")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)








