import os
import sys
import json
import time
import math
import random
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

# Add repo root to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# Mock Data Generators
def generate_mock_candles(instrument, count, granularity):
    """Generate realistic-looking candle data"""
    candles = []
    base_price = 1.1000 if "EUR" in instrument else (1800.0 if "XAU" in instrument else 1.2000)
    
    # Create a trend
    trend_dir = 1 if "EUR" in instrument else -1
    
    now = datetime.now(timezone.utc)
    for i in range(count):
        # Time going backwards? No, list usually newest last or first? OANDA is oldest first.
        # Let's generate oldest first.
        t = now - timedelta(days=(count - i))
        
        # Random walk
        change = (random.random() - 0.5) * 0.01 + (trend_dir * 0.001)
        close = base_price * (1 + change)
        high = close * (1 + random.random() * 0.005)
        low = close * (1 - random.random() * 0.005)
        open_p = base_price
        
        candles.append({
            "time": t.isoformat(),
            "complete": True,
            "volume": 1000 + int(random.random() * 500),
            "mid": {"o": str(open_p), "h": str(high), "l": str(low), "c": str(close)}
        })
        base_price = close
        
    return {"candles": candles}

def generate_mock_price(instrument):
    """Generate realistic price"""
    base = 1.1050 if "EUR" in instrument else (1850.50 if "XAU" in instrument else 1.2500)
    bid = base
    ask = base + 0.0001
    return {
        "prices": [{
            "instrument": instrument,
            "bids": [{"price": str(bid), "liquidity": 10}],
            "asks": [{"price": str(ask), "liquidity": 10}],
            "closeoutBid": str(bid),
            "closeoutAsk": str(ask),
            "time": datetime.now(timezone.utc).isoformat()
        }]
    }

# Mock requests.get
original_get = None # We might need this if we want to allow other requests, but likely not.

def mock_get(url, **kwargs):
    """Intercept OANDA calls"""
    print(f"DEBUG: Mocking GET {url}")
    # Create a mock response object
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    
    if "pricing" in url:
        # Extract instrument from params
        params = kwargs.get("params", {})
        instruments = params.get("instruments", "EUR_USD")
        # Handle multiple? Just take first for simplicity or loop
        inst = instruments.split(",")[0]
        mock_resp.json.return_value = generate_mock_price(inst)
        return mock_resp
        
    if "candles" in url:
        # Extract instrument from URL
        # URL format: .../instruments/{instrument}/candles
        parts = url.split("/")
        try:
            idx = parts.index("instruments")
            inst = parts[idx+1]
        except:
            inst = "EUR_USD"
            
        params = kwargs.get("params", {})
        requested_count = int(params.get("count", 50))
        # FORCE return at least 100 candles to pass strict validation
        count = max(requested_count, 100)
        granularity = params.get("granularity", "D")
        
        mock_resp.json.return_value = generate_mock_candles(inst, count, granularity)
        print(f"DEBUG: Generated {count} candles for {inst}")
        return mock_resp
    
    # Default fallback (shouldn't happen for OANDA calls in this test)
    mock_resp.status_code = 404
    return mock_resp

def main():
    print("🚀 Starting Mock API Server for Verification...")
    
    # Ensure environment variables are set for the provider to "work"
    os.environ["OANDA_API_KEY"] = "mock_key"
    os.environ["OANDA_ACCOUNT_ID"] = "mock_account"
    os.environ["CONTROL_PLANE_PORT"] = "8787"
    
    # Patch requests.get
    patcher = patch('requests.get', side_effect=mock_get)
    patcher.start()
    
    # Import and run API
    try:
        from src.control_plane.api import run
        run()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        patcher.stop()

if __name__ == "__main__":
    main()
