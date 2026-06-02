"""Tests for Control Plane ConfigStore

Run with: pytest tests/test_config_store.py -v
"""

import os
import tempfile
import pytest
from pathlib import Path
from src.control_plane.config_store import ConfigStore
from src.control_plane.schema import RuntimeConfig


@pytest.fixture
def temp_config_path():
    """Create temporary config file path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test_config.yaml")


def test_load_creates_default_if_missing(temp_config_path):
    """Test load creates default config if file doesn't exist"""
    store = ConfigStore(temp_config_path)
    config = store.load()
    
    assert config is not None
    assert config.active_strategy_key == "momentum"  # Default
    assert Path(temp_config_path).exists()


def test_save_creates_backup(temp_config_path):
    """Test save creates .bak backup file"""
    store = ConfigStore(temp_config_path)
    
    # Initial save
    store.save()
    assert Path(temp_config_path).exists()
    
    # Second save should create backup
    store.save({"active_strategy_key": "gold"})
    backup_path = Path(temp_config_path).with_suffix('.yaml.bak')
    assert backup_path.exists()


def test_save_rejects_invalid_config(temp_config_path):
    """Test save rejects invalid config and preserves old config"""
    store = ConfigStore(temp_config_path)
    
    # Save valid config first
    store.save({"active_strategy_key": "momentum"})
    
    # Try to save invalid config
    with pytest.raises(ValueError):
        store.save({"active_strategy_key": "invalid_strategy"})
    
    # Old config should be preserved
    config = store.load()
    assert config.active_strategy_key == "momentum"


def test_partial_update_merges_correctly(temp_config_path):
    """Test partial update merges with existing config"""
    store = ConfigStore(temp_config_path)
    
    # Initial config
    store.save({"active_strategy_key": "momentum", "scan_interval_seconds": 30})
    
    # Partial update (only change strategy)
    store.save({"active_strategy_key": "gold"})
    
    config = store.load()
    assert config.active_strategy_key == "gold"
    assert config.scan_interval_seconds == 30  # Should be preserved


def test_has_changed_detects_modifications(temp_config_path):
    """Test has_changed detects config file modifications"""
    store = ConfigStore(temp_config_path)
    
    # Load initial config
    config1 = store.load()
    assert not store.has_changed()  # No change yet
    
    # Modify config externally
    config1.active_strategy_key = "gold"
    config1.save_to_yaml(temp_config_path)
    
    # Should detect change
    assert store.has_changed()
    
    # Reload should reset change detection
    config2 = store.load()
    assert not store.has_changed()
    assert config2.active_strategy_key == "gold"


def test_atomic_write_on_validation_failure(temp_config_path):
    """Test atomic write doesn't corrupt config on validation failure"""
    store = ConfigStore(temp_config_path)
    
    # Save valid config
    store.save({"active_strategy_key": "momentum"})
    old_mtime = store.get_mtime()
    
    # Try to save invalid config
    try:
        store.save({"scan_interval_seconds": -1})  # Invalid
    except ValueError:
        pass
    
    # Config should be unchanged
    config = store.load()
    assert config.active_strategy_key == "momentum"
    assert config.scan_interval_seconds == 30  # Default


def test_no_secrets_in_saved_config(temp_config_path):
    """Test saved config file never contains secrets"""
    store = ConfigStore(temp_config_path)
    store.save()
    
    with open(temp_config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Should not contain any secret patterns
    assert 'OANDA_API_KEY' not in content
    assert 'api_key' not in content.lower() or 'active_strategy_key' in content.lower()
    assert 'password' not in content.lower()
    assert 'secret' not in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
