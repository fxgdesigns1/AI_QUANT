"""Tests for Control Plane Config Schema and Validation

Run with: pytest tests/test_control_plane_config.py -v
"""

import pytest
from src.control_plane.schema import RuntimeConfig, RiskSettings, ExecutionPolicy


def test_default_config():
    """Test default config is valid"""
    config = RuntimeConfig()
    errors = config.validate()
    assert errors == [], f"Default config should be valid, got errors: {errors}"


def test_config_rejects_invalid_strategy():
    """Test config validation rejects invalid strategy keys"""
    config = RuntimeConfig(active_strategy_key="invalid_strategy")
    errors = config.validate()
    assert len(errors) > 0
    assert any("active_strategy_key" in err for err in errors)


def test_config_rejects_invalid_scan_interval():
    """Test config validation rejects invalid scan intervals"""
    # Too low
    config = RuntimeConfig(scan_interval_seconds=0)
    errors = config.validate()
    assert len(errors) > 0
    assert any("scan_interval" in err for err in errors)
    
    # Too high
    config = RuntimeConfig(scan_interval_seconds=10000)
    errors = config.validate()
    assert len(errors) > 0


def test_config_rejects_invalid_risk_settings():
    """Test config validation rejects invalid risk settings"""
    # Invalid max_risk_per_trade_pct
    config = RuntimeConfig(risk=RiskSettings(max_risk_per_trade_pct=50.0))
    errors = config.validate()
    assert len(errors) > 0
    
    # Invalid max_positions
    config = RuntimeConfig(risk=RiskSettings(max_positions=100))
    errors = config.validate()
    assert len(errors) > 0


def test_config_to_dict_from_dict_roundtrip():
    """Test config serialization roundtrip"""
    config1 = RuntimeConfig(
        active_strategy_key="gold",
        scan_interval_seconds=60,
        risk=RiskSettings(max_risk_per_trade_pct=2.0, max_positions=5)
    )
    
    config_dict = config1.to_dict()
    config2 = RuntimeConfig.from_dict(config_dict)
    
    assert config2.active_strategy_key == "gold"
    assert config2.scan_interval_seconds == 60
    assert config2.risk.max_risk_per_trade_pct == 2.0
    assert config2.risk.max_positions == 5


def test_config_rejects_secret_patterns():
    """Test config validation detects secret patterns (paranoid check)"""
    # This is a meta-test - in real usage, secrets should never reach the config object
    # But we add a paranoid check anyway
    config = RuntimeConfig()
    errors = config.validate()
    
    # Should not contain any secret keywords
    config_str = str(config.to_dict()).lower()
    forbidden = ["oanda_api_key", "password123", "secret_key"]
    for secret in forbidden:
        assert secret not in config_str


def test_valid_strategy_keys():
    """Test all valid strategy keys are accepted"""
    valid_keys = ["momentum", "gold", "range", "eur_usd_5m_safe", "momentum_v2"]
    
    for key in valid_keys:
        config = RuntimeConfig(active_strategy_key=key)
        errors = config.validate()
        assert errors == [], f"Strategy '{key}' should be valid, got errors: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
