"""Tests for status snapshot read/write (no secrets)"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from src.control_plane.status_snapshot import StatusSnapshot, get_status_snapshot


def test_snapshot_write_read_roundtrip():
    """Test atomic write and read"""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = os.path.join(tmpdir, "status.json")
        writer = StatusSnapshot(snapshot_path)
        
        # Write snapshot
        status = {
            "mode": "paper",
            "execution_enabled": False,
            "accounts_total": 1,
            "active_strategy_key": "momentum"
        }
        writer.write(status)
        
        # Verify file exists
        assert Path(snapshot_path).exists()
        
        # Read back
        reader = StatusSnapshot(snapshot_path)
        data = reader.read(max_age_seconds=10)
        
        assert data is not None
        assert data["mode"] == "paper"
        assert data["execution_enabled"] is False
        assert "timestamp_utc" in data
        assert "timestamp_iso" in data


def test_snapshot_rejects_secrets():
    """Test that secrets are filtered out"""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = os.path.join(tmpdir, "status.json")
        writer = StatusSnapshot(snapshot_path)
        
        # Try to write data with secret-like keys
        status = {
            "mode": "paper",
            "OANDA_API_KEY": "should-be-removed",
            "secret_token": "should-be-removed",
            "password": "should-be-removed",
            "safe_field": "should-remain"
        }
        writer.write(status)
        
        # Read back
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Secrets should be filtered
        assert "OANDA_API_KEY" not in data
        assert "secret_token" not in data
        assert "password" not in data
        
        # Safe fields should remain
        assert "safe_field" in data
        assert data["safe_field"] == "should-remain"


def test_snapshot_freshness_check():
    """Test freshness/staleness detection"""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = os.path.join(tmpdir, "status.json")
        writer = StatusSnapshot(snapshot_path)
        
        # Write snapshot
        writer.write({"mode": "paper"})
        
        # Read immediately (should be fresh)
        reader = StatusSnapshot(snapshot_path)
        data = reader.read(max_age_seconds=2)
        assert data is not None
        
        # Wait for staleness
        time.sleep(2.5)
        
        # Read with strict freshness (should be stale)
        data = reader.read(max_age_seconds=2)
        assert data is None  # Stale


def test_snapshot_missing_file_returns_none():
    """Test that missing file returns None gracefully"""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = os.path.join(tmpdir, "nonexistent.json")
        reader = StatusSnapshot(snapshot_path)
        
        data = reader.read()
        assert data is None


def test_snapshot_atomic_write():
    """Test atomic write prevents corruption"""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = os.path.join(tmpdir, "status.json")
        writer = StatusSnapshot(snapshot_path)
        
        # Write first version
        writer.write({"version": 1})
        
        # Verify readable
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        assert data1["version"] == 1
        
        # Write second version
        writer.write({"version": 2})
        
        # Verify readable and updated
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
        assert data2["version"] == 2


def test_nested_secret_filtering():
    """Test secrets are filtered from nested structures"""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = os.path.join(tmpdir, "status.json")
        writer = StatusSnapshot(snapshot_path)
        
        # Nested structure with secrets
        status = {
            "mode": "paper",
            "accounts": [
                {
                    "id": "acc1",
                    "api_key": "secret123",  # Should be removed
                    "balance": 1000  # Should remain
                }
            ],
            "config": {
                "token": "bearer-xyz",  # Should be removed
                "scan_interval": 30  # Should remain
            }
        }
        writer.write(status)
        
        # Read back
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check nested filtering
        assert len(data["accounts"]) == 1
        assert "api_key" not in data["accounts"][0]
        assert data["accounts"][0]["balance"] == 1000
        
        assert "token" not in data["config"]
        assert data["config"]["scan_interval"] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
