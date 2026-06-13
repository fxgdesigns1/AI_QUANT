#!/usr/bin/env python3
"""
Dataset to Backtest Cache Builder
Converts dataset artifacts into cached candle format for deterministic backtesting.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_dataset(dataset_path: Path) -> Dict[str, Any]:
    """Load dataset from artifact directory"""
    dataset_file = dataset_path / "dataset.json"
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_file}")
    
    with open(dataset_file, 'r') as f:
        return json.load(f)


def extract_candles(dataset: Dict[str, Any], instrument: str) -> List[Dict[str, Any]]:
    """Extract candles for a specific instrument from dataset"""
    candles = []
    
    # Dataset structure may vary - try common patterns
    if "instruments" in dataset:
        inst_data = dataset["instruments"].get(instrument, {})
        candles = inst_data.get("candles", [])
    elif "candles" in dataset:
        # Flat structure - filter by instrument
        all_candles = dataset["candles"]
        candles = [c for c in all_candles if c.get("instrument") == instrument]
    elif instrument in dataset:
        # Instrument is top-level key
        candles = dataset[instrument].get("candles", [])
    
    return candles


def build_cache(dataset_path: Path, output_path: Path, instruments: List[str]) -> None:
    """Build cached candle files from dataset"""
    logger.info(f"Loading dataset from {dataset_path}")
    dataset = load_dataset(dataset_path)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    for instrument in instruments:
        logger.info(f"Extracting candles for {instrument}")
        candles = extract_candles(dataset, instrument)
        
        if not candles:
            logger.warning(f"No candles found for {instrument}")
            continue
        
        # Normalize candle format
        normalized = []
        for c in candles:
            # Handle various input formats
            if isinstance(c, dict):
                normalized.append({
                    "time": c.get("time", c.get("timestamp", "")),
                    "complete": c.get("complete", True),
                    "volume": c.get("volume", 0),
                    "o": float(c.get("o", c.get("open", 0.0))),
                    "h": float(c.get("h", c.get("high", 0.0))),
                    "l": float(c.get("l", c.get("low", 0.0))),
                    "c": float(c.get("c", c.get("close", 0.0)))
                })
        
        # Write cache file
        cache_file = output_path / f"{instrument}_M5.json"
        cache_data = {
            "instrument": instrument,
            "granularity": "M5",
            "count": len(normalized),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_dataset": str(dataset_path),
            "candles": normalized
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Wrote {len(normalized)} candles to {cache_file}")


def main():
    parser = argparse.ArgumentParser(description="Build backtest cache from dataset")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to dataset directory")
    parser.add_argument("--output", type=Path, required=True, help="Output cache directory")
    parser.add_argument("--instruments", nargs="+", default=["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "NZD_USD"],
                       help="Instruments to extract")
    
    args = parser.parse_args()
    
    if not args.dataset.exists():
        logger.error(f"Dataset path does not exist: {args.dataset}")
        return 1
    
    try:
        build_cache(args.dataset, args.output, args.instruments)
        logger.info("Cache build complete")
        return 0
    except Exception as e:
        logger.error(f"Cache build failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
