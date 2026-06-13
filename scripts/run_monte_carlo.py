#!/usr/bin/env python3
"""
Monte Carlo Research Entrypoint
Production-grade Monte Carlo runner for deterministic research.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.research.monte_carlo import MonteCarloRunner, MonteCarloConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run Monte Carlo research")
    parser.add_argument("--input-tournament", type=Path, help="Input tournament results JSON")
    parser.add_argument("--input-candles", type=Path, help="Input candle cache directory")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--iterations", type=int, default=1000, help="Number of iterations")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers (default: CPU count)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--mode",
        choices=["reshuffle", "resample", "jitter", "combined"],
        default="reshuffle",
        help=(
            "Monte Carlo mode. reshuffle/combined shuffle-only: expectancy_r and win_rate are "
            "order-invariant (same multiset each iteration). Use resample for bootstrap variation "
            "in those metrics."
        ),
    )
    parser.add_argument("--jitter-params", type=str, help="Parameter jitter config JSON")
    
    args = parser.parse_args()
    
    # Determine worker count
    if args.workers is None:
        args.workers = max(1, os.cpu_count() or 1)
    
    # Verify cached mode doesn't require OANDA
    oanda_key = os.getenv("OANDA_API_KEY")
    if oanda_key:
        logger.info("OANDA_API_KEY present but Monte Carlo uses cached data only")
    else:
        logger.info("Monte Carlo mode: cached data only (no OANDA env vars required)")
    
    # Parse jitter params if provided
    jitter_params = None
    if args.jitter_params:
        if Path(args.jitter_params).exists():
            with open(args.jitter_params, 'r') as f:
                jitter_params = json.load(f)
        else:
            jitter_params = json.loads(args.jitter_params)
    
    # Create run ID
    run_id = f"mc_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    
    # Create config
    config = MonteCarloConfig(
        run_id=run_id,
        seed=args.seed,
        iterations=args.iterations,
        workers=args.workers,
        mode=args.mode,
        jitter_params=jitter_params,
        input_tournament=str(args.input_tournament) if args.input_tournament else None,
        input_candles=str(args.input_candles) if args.input_candles else None
    )
    
    # Run Monte Carlo
    runner = MonteCarloRunner(config, args.output)
    
    try:
        summary = runner.run()
        
        logger.info("=" * 60)
        logger.info("MONTE CARLO SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Run ID: {summary.run_id}")
        logger.info(f"Iterations: {summary.completed}/{summary.iterations}")
        logger.info(f"Expectancy - Mean: {summary.expectancy_distribution['mean']:.4f}, "
                   f"Std: {summary.expectancy_distribution['std']:.4f}")
        wr = summary.win_rate_distribution
        dd = summary.drawdown_distribution
        logger.info(
            f"Win Rate - Mean: {wr['mean']:.4f}, Std: {wr.get('std', 0.0):.4f}"
        )
        logger.info(
            f"Max Drawdown (iter max): {dd['max']:.4f}, Std across iterations: {dd.get('std', 0.0):.4f}"
        )
        logger.info(f"Robustness P5-P95: {summary.robustness_percentiles['expectancy_p5']:.4f} to "
                   f"{summary.robustness_percentiles['expectancy_p95']:.4f}")
        logger.info("=" * 60)
        
        return 0
    except Exception as e:
        logger.error(f"Monte Carlo failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
