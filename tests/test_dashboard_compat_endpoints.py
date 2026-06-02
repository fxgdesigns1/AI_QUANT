"""Tests for dashboard compatibility endpoints"""

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from src.control_plane.api import app

client = TestClient(app)


def test_health_endpoint():
    """Test /health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_api_status_endpoint():
    """Test /api/status endpoint returns valid structure"""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    
    # Required fields
    assert "mode" in data
    assert "execution_enabled" in data
    assert "accounts_loaded" in data
    assert "active_strategy_key" in data
    assert data["mode"] in ["paper", "live"]
    assert isinstance(data["execution_enabled"], bool)


def test_api_accounts_endpoint():
    """Test /api/accounts endpoint"""
    response = client.get("/api/accounts")
    assert response.status_code == 200
    data = response.json()
    
    assert "ok" in data
    assert "accounts" in data
    assert "execution_capable" in data
    assert isinstance(data["accounts"], list)
    assert isinstance(data["execution_capable"], int)


def test_api_strategies_overview_endpoint():
    """Test /api/strategies/overview endpoint"""
    response = client.get("/api/strategies/overview")
    assert response.status_code == 200
    data = response.json()
    
    assert "ok" in data
    assert "active_strategy" in data
    assert "strategies" in data
    assert isinstance(data["strategies"], list)
    
    # Should have at least one strategy
    assert len(data["strategies"]) > 0
    
    # Each strategy should have required fields
    for strategy in data["strategies"]:
        assert "key" in strategy
        assert "name" in strategy
        assert "active" in strategy
        assert isinstance(strategy["active"], bool)


def test_api_positions_endpoint():
    """Test /api/positions endpoint"""
    response = client.get("/api/positions")
    assert response.status_code == 200
    data = response.json()
    
    assert "ok" in data
    assert "positions" in data
    assert "execution_enabled" in data
    assert "reason" in data
    assert isinstance(data["positions"], list)


def test_api_signals_pending_endpoint():
    """Test /api/signals/pending endpoint"""
    response = client.get("/api/signals/pending")
    assert response.status_code == 200
    data = response.json()
    
    assert "ok" in data
    assert "signals" in data
    assert "active_strategy" in data
    assert "execution_enabled" in data
    assert isinstance(data["signals"], list)


def test_api_trades_pending_endpoint():
    """Test /api/trades/pending endpoint"""
    response = client.get("/api/trades/pending")
    assert response.status_code == 200
    data = response.json()
    
    assert "ok" in data
    assert "trades" in data
    assert "execution_enabled" in data
    assert isinstance(data["trades"], list)


def test_api_news_endpoint():
    """Test /api/news endpoint"""
    response = client.get("/api/news")
    assert response.status_code == 200
    data = response.json()
    
    assert "ok" in data
    assert "enabled" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_api_contextual_endpoint():
    """Test /api/contextual/{instrument} endpoint"""
    response = client.get("/api/contextual/XAU_USD")
    assert response.status_code == 200
    data = response.json()
    
    assert "instrument" in data
    assert data["instrument"] == "XAU_USD"


def test_no_secrets_in_api_responses():
    """Test that API responses never contain secrets"""
    endpoints = [
        "/api/status",
        "/api/accounts",
        "/api/config",
        "/api/strategies",
        "/api/positions",
        "/api/signals/pending",
        "/api/trades/pending"
    ]
    
    secret_patterns = [
        "OANDA_API_KEY",
        "api_key",
        "token",
        "secret",
        "password",
        "credential"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200
        
        response_text = response.text.lower()
        
        # Check for secret patterns (except allowed keys like 'active_strategy_key')
        for pattern in secret_patterns:
            if pattern == "api_key":
                # Allow 'active_strategy_key' but not 'api_key' alone
                assert "oanda_api_key" not in response_text
            else:
                # More lenient check - look for actual secret values, not just field names
                assert f'"{pattern}":"' not in response_text.replace(" ", "")


def test_truthful_signals_only_mode():
    """Test that signals-only mode is reported truthfully"""
    response = client.get("/api/status")
    data = response.json()
    
    # In test environment, should be paper/signals-only
    if not data["execution_enabled"]:
        # Verify truthful reporting
        assert data["accounts_execution_capable"] == 0
        
        # Check positions/trades are empty
        positions_resp = client.get("/api/positions")
        positions_data = positions_resp.json()
        assert positions_data["execution_enabled"] is False
        assert len(positions_data["positions"]) == 0
        
        trades_resp = client.get("/api/trades/pending")
        trades_data = trades_resp.json()
        assert trades_data["execution_enabled"] is False
        assert len(trades_data["trades"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
