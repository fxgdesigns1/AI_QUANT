#!/usr/bin/env python3
"""
Strategy Tournament Runner
Runs multiple strategy variants against cached candle data.
"""

import os
import sys
import json
import copy
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.research.backtest_core import BacktestEngine, run_sma_crossover_research_backtest
from src.research.tournament_artifacts import (
    write_champions,
    write_report,
    write_tournament_config_resolved,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_tournament_config(config_path: Path) -> Dict[str, Any]:
    """Load tournament configuration"""
    with open(config_path, 'r') as f:
        return json.load(f)


def resolve_config_paths(config: Dict[str, Any], base_path: Path) -> Dict[str, Any]:
    """Resolve relative paths in config to absolute paths"""
    resolved = config.copy()

    def _abs(p: str) -> str:
        exp = Path(p).expanduser()
        if exp.is_absolute():
            return str(exp.resolve())
        return str((base_path / exp).resolve())

    if "dataset_path" in resolved and resolved["dataset_path"]:
        resolved["dataset_path"] = _abs(str(resolved["dataset_path"]))

    if "cache_path" in resolved and resolved["cache_path"]:
        resolved["cache_path"] = _abs(str(resolved["cache_path"]))

    if "candle_cache_path" in resolved and resolved["candle_cache_path"]:
        resolved["candle_cache_path"] = _abs(str(resolved["candle_cache_path"]))

    return resolved


def run_tournament(config: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """Run tournament with given config"""
    run_id = f"tournament_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    logger.info(f"Starting tournament: {run_id}")
    
    # Setup backtest engine with cached candles
    raw_cache = config.get("cache_path") or config.get("candle_cache_path")
    if not raw_cache:
        raise ValueError("Config must set cache_path or candle_cache_path")
    cache_path = Path(raw_cache).expanduser().resolve()
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache path does not exist: {cache_path}")

    engine = BacktestEngine(use_cached=True, cache_root=cache_path)

    variants = config.get("variants", [])
    instruments = config.get("instruments", ["EUR_USD"])
    results: List[Dict[str, Any]] = []

    risk_per_trade = float(config.get("risk_per_trade", 0.01))
    stop_atr_mult = float(config.get("stop_atr_mult", 1.5))
    rr = float(config.get("risk_reward", 2.0))
    granularity = config.get("granularity", "M5")

    for variant in variants:
        strategy_name = str(variant.get("strategy", "sma_crossover_research"))
        variant_id = str(variant.get("variant_id", "default"))
        fast_period = int(variant.get("fast_period", config.get("default_fast_period", 5)))
        slow_period = int(variant.get("slow_period", config.get("default_slow_period", 20)))

        logger.info(f"Running variant: {variant_id} ({strategy_name})")

        for instrument in instruments:
            try:
                candles = engine.get_candles(instrument, granularity=granularity)
                if not candles:
                    logger.warning(f"No candles for {instrument}, skipping")
                    continue

                if strategy_name in ("sma_crossover_research", "momentum_trading", "unknown"):
                    bt = run_sma_crossover_research_backtest(
                        candles,
                        instrument=instrument,
                        fast_period=fast_period,
                        slow_period=slow_period,
                        strategy_name=strategy_name,
                        risk_per_trade=risk_per_trade,
                        stop_atr_mult=stop_atr_mult,
                        rr=rr,
                    )
                    result = {
                        "variant_id": variant_id,
                        "strategy": strategy_name,
                        "instrument": instrument,
                        "fast_period": fast_period,
                        "slow_period": slow_period,
                        "total_trades": bt.total_trades,
                        "win_rate": bt.win_rate,
                        "expectancy_r": bt.expectancy_r,
                        "max_drawdown": bt.max_drawdown,
                        "total_pnl": bt.total_pnl,
                        "trades": bt.total_trades,
                        "trade_list": bt.trades,
                    }
                else:
                    logger.warning("Unknown strategy %s — using sma_crossover_research", strategy_name)
                    bt = run_sma_crossover_research_backtest(
                        candles,
                        instrument=instrument,
                        fast_period=fast_period,
                        slow_period=slow_period,
                        strategy_name="sma_crossover_research",
                        risk_per_trade=risk_per_trade,
                        stop_atr_mult=stop_atr_mult,
                        rr=rr,
                    )
                    result = {
                        "variant_id": variant_id,
                        "strategy": strategy_name,
                        "instrument": instrument,
                        "fast_period": fast_period,
                        "slow_period": slow_period,
                        "total_trades": bt.total_trades,
                        "win_rate": bt.win_rate,
                        "expectancy_r": bt.expectancy_r,
                        "max_drawdown": bt.max_drawdown,
                        "total_pnl": bt.total_pnl,
                        "trades": bt.total_trades,
                        "trade_list": bt.trades,
                    }
                results.append(result)

            except Exception as e:
                logger.error(f"Error running {variant_id} on {instrument}: {e}")
    
    # Write results
    output_dir.mkdir(parents=True, exist_ok=True)
    results_file = output_dir / "tournament_results.json"
    
    tournament_output = {
        "run_id": run_id,
        "config_source": str(config.get("_source_path", "")),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "variants_tested": len(variants),
        "instruments": instruments,
        "results": results,
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(tournament_output, f, indent=2)

    resolved_cfg = copy.deepcopy(config)
    resolved_cfg.pop("_source_path", None)
    write_tournament_config_resolved(resolved_cfg, output_dir / "tournament_config_resolved.json")
    write_report(tournament_output, output_dir / "report.json")
    write_champions(tournament_output, output_dir / "champions.json", top_n=int(config.get("champions_top_n", 10)))

    logger.info(f"Tournament complete: {len(results)} results written to {results_file}")
    return tournament_output


def main():
    parser = argparse.ArgumentParser(description="Run strategy tournament")
    parser.add_argument("--config", type=Path, required=True, help="Tournament config JSON")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--use-cached-candles", action="store_true", default=True,
                       help="Use cached candles (default: True)")
    
    args = parser.parse_args()
    
    # Verify cached mode doesn't require OANDA
    if args.use_cached_candles:
        oanda_key = os.getenv("OANDA_API_KEY")
        if oanda_key:
            logger.info("OANDA_API_KEY present but using cached mode - will ignore live API")
        else:
            logger.info("Using cached candles - no OANDA env vars required")
    
    if not args.config.exists():
        logger.error(f"Config file does not exist: {args.config}")
        return 1
    
    try:
        config = load_tournament_config(args.config)
        config["_source_path"] = str(args.config)
        
        # Resolve paths relative to config file location
        config = resolve_config_paths(config, args.config.parent)
        
        result = run_tournament(config, args.output)
        
        logger.info("Tournament complete")
        return 0
    except Exception as e:
        logger.error(f"Tournament failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
