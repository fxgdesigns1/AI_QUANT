"""Outlook Engine - Deterministic Market Analysis

Generates Daily/Weekly/Monthly outlooks based on market data snapshots.
READ-ONLY. No execution side effects.
"""

from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

class OutlookEngine:
    """Deterministic outlook generator"""
    
    def __init__(self):
        # Paths
        self._repo_root = Path(__file__).resolve().parents[2]
        self._runtime_dir = self._repo_root / "runtime"
        self._runtime_dir.mkdir(parents=True, exist_ok=True)
        
    def _compute_hash(self, data: Any) -> str:
        """Stable hash of input data"""
        s = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def _get_stub_outlook(self, horizon: str) -> Dict[str, Any]:
        """Generate a safe stub/baseline outlook if no models active"""
        ts = datetime.now(timezone.utc).isoformat()
        
        # Standard instrument set
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD", "AUD_USD"]
        
        outlooks = []
        for inst in instruments:
            outlooks.append({
                "instrument": inst,
                "bias": "NEUTRAL",
                "confidence": "LOW",
                "key_levels": {
                    "support": [],
                    "resistance": []
                },
                "scenarios": [
                    {
                        "name": "Range Bound",
                        "probability": "60%",
                        "description": "Price likely to consolidate within current range."
                    }
                ],
                "warnings": ["Data insufficient for directional bias"]
            })
            
        return {
            "horizon": horizon,
            "as_of": ts,
            "generated_at": time.time(),
            "engine_version": "1.0.0-stub",
            "inputs_hash": "stub_no_inputs",
            "outlooks": outlooks,
            "note": "Baseline outlook (waiting for full market data integration)"
        }

    def compute(self, horizon: str, market_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Compute outlook for horizon (daily, weekly, monthly)"""
        
        # In a full implementation, this would run technical analysis on market_data.
        # For this milestone, we provide the deterministic structure and stub logic.
        # This ensures the API contract is met and UI can be built.
        
        # If we had market data, we'd hash it:
        # inputs_hash = self._compute_hash(market_data)
        
        # Return stub for now
        result = self._get_stub_outlook(horizon)
        
        # Save snapshot
        self._save_snapshot(horizon, result)
        
        return result

    def _save_snapshot(self, horizon: str, data: Dict[str, Any]) -> None:
        """Save outlook snapshot atomically"""
        filename = f"outlook_{horizon}.json"
        path = self._runtime_dir / filename
        tmp_path = path.with_suffix(".tmp")
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        tmp_path.replace(path)

    def get_latest(self, horizon: str) -> Optional[Dict[str, Any]]:
        """Get latest cached outlook"""
        path = self._runtime_dir / f"outlook_{horizon}.json"
        if not path.exists():
            return None
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

# Singleton
_outlook_engine = None

def get_outlook_engine() -> OutlookEngine:
    global _outlook_engine
    if _outlook_engine is None:
        _outlook_engine = OutlookEngine()
    return _outlook_engine
