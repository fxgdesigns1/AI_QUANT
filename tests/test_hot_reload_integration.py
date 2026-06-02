"""Integration test: Hot-reload in signals-only mode

Run with: pytest tests/test_hot_reload_integration.py -v

Tests that config changes are detected and applied without restarting runner.
Tests that signals-only mode remains safe even after config changes.
"""

import os
import time
import pytest
from unittest.mock import Mock, patch
from src.control_plane.config_store import ConfigStore
from src.control_plane.schema import RuntimeConfig


def test_config_hot_reload_simulation():
    """Test config hot-reload detection logic"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.yaml")
        store = ConfigStore(config_path)
        
        # Initial load
        config1 = store.load()
        assert config1.active_strategy_key == "momentum"
        
        # Simulate time passing
        time.sleep(0.1)
        
        # No changes yet
        assert not store.has_changed()
        
        # Update config (simulate dashboard change)
        store.save({"active_strategy_key": "gold"})
        
        # Should detect change
        assert store.has_changed()
        
        # Reload
        config2 = store.load()
        assert config2.active_strategy_key == "gold"


def test_signals_only_no_execution_markers():
    """Test that signals-only mode never initializes execution components
    
    This is a critical safety test.
    """
    # This would be run as a full integration test with actual runner
    # For now, we verify the logic pattern
    
    # Simulate signals-only mode environment
    env = {
        'TRADING_MODE': 'paper',
        'PAPER_EXECUTION_ENABLED': 'false',
        'PAPER_ALLOW_OANDA_NETWORK': 'true',
    }
    
    with patch.dict(os.environ, env):
        # Import after setting env
        from working_trading_system import _can_execute
        
        can_exec, reason = _can_execute()
        assert not can_exec
        assert reason == "paper_signals_only"


def test_strategy_change_applies_correctly():
    """Test strategy change from config is applied in scan loop"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.yaml")
        store = ConfigStore(config_path)
        
        # Simulate runner loading config
        config = store.load()
        active_strategy = config.active_strategy_key
        assert active_strategy == "momentum"
        
        # Simulate dashboard changing strategy
        store.save({"active_strategy_key": "gold"})
        
        # Simulate runner detecting change (before next scan)
        if store.has_changed():
            config = store.load()
            active_strategy = config.active_strategy_key
        
        assert active_strategy == "gold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
