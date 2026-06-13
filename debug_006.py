
import sys
import os
import logging

# Add workspace root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_006")

print("--- DEBUG 006 START ---")

try:
    from src.strategies.session_execution_strategy import SessionExecutionStrategy
    # Access the module-level variable manually if possible, or infer from instance
    print("Successfully imported SessionExecutionStrategy")
    
    strategy = SessionExecutionStrategy()
    print(f"Strategy initialized: {strategy}")
    
    # Check dependencies via private attributes or introspection
    # The file has a module-level HAS_DEPENDENCIES, let's try to find it
    import src.strategies.session_execution_strategy as mod
    print(f"HAS_DEPENDENCIES: {getattr(mod, 'HAS_DEPENDENCIES', 'UNKNOWN')}")
    
    if getattr(mod, 'HAS_DEPENDENCIES', False):
        print("Dependencies are loaded.")
        if strategy.outlook_engine:
            print("Outlook Engine: LOADED")
            # Try to fetch outlook to see if it works
            try:
                daily = strategy.outlook_engine.get_latest("daily")
                print(f"Outlook Daily: {daily is not None} (keys: {list(daily.keys()) if daily else 'None'})")
            except Exception as e:
                print(f"Error fetching outlook: {e}")
        else:
            print("Outlook Engine: NONE (Failed to init?)")
            
        if strategy.regime_detector:
            print("Regime Detector: LOADED")
        else:
            print("Regime Detector: NONE")
            
    else:
        print("Dependencies are NOT loaded (HAS_DEPENDENCIES=False).")
        
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Runtime Error: {e}")

print("--- DEBUG 006 END ---")
