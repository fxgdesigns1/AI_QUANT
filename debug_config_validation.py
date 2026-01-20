import sys
import os
from src.control_plane.schema import RuntimeConfig
from src.control_plane.strategy_registry import get_strategy_registry

def check_config():
    path = "runtime/config.yaml"
    if not os.path.exists(path):
        print(f"File {path} does not exist")
        return

    print(f"Loading {path}...")
    try:
        config = RuntimeConfig.load_from_yaml(path)
        print("Config loaded successfully.")
    except Exception as e:
        print(f"Failed to load yaml: {e}")
        return

    print("Validating...")
    try:
        errors = config.validate()
        if errors:
            print("❌ Validation Errors:")
            for err in errors:
                print(f"  - {err}")
        else:
            print("✅ Config is valid.")
    except Exception as e:
        print(f"Validation crashed: {e}")

if __name__ == "__main__":
    check_config()
