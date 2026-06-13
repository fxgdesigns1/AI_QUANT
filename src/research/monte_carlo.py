"""
Monte Carlo Research Runner
Deterministic resampling and parameter jitter for robustness testing.
"""

import copy
import json
import random
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def extract_trades_from_tournament_data(tournament_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect per-trade dicts from tournament_results.json-style payloads."""
    out: List[Dict[str, Any]] = []
    for row in tournament_data.get("results", []) or []:
        tl = row.get("trade_list")
        if isinstance(tl, list):
            for t in tl:
                if isinstance(t, dict):
                    out.append(dict(t))
    return out


def extract_trades_from_tournament_path(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return extract_trades_from_tournament_data(json.load(f))


def _sample_stdev(values: List[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5


def _iteration_metrics(
    iteration: int,
    seed: int,
    mode: str,
    trades: List[Dict[str, Any]],
    jitter_params: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    all_trades = copy.deepcopy(trades)

    if mode == "reshuffle":
        processed = list(all_trades)
        rng.shuffle(processed)
    elif mode == "resample":
        if not all_trades:
            processed = []
        else:
            processed = [rng.choice(all_trades) for _ in range(len(all_trades))]
    elif mode == "jitter":
        processed = list(all_trades)
        if jitter_params:
            for t in processed:
                for param, jitter_range in jitter_params.items():
                    if param in t and isinstance(t[param], (int, float)):
                        base = float(t[param])
                        t[param] = base * (1.0 + rng.uniform(-jitter_range, jitter_range))
    elif mode == "combined":
        processed = list(all_trades)
        rng.shuffle(processed)
    else:
        processed = list(all_trades)

    winning = sum(1 for t in processed if float(t.get("pnl") or 0) > 0)
    total = len(processed)
    win_rate = winning / total if total > 0 else 0.0
    total_pnl = sum(float(t.get("pnl") or 0.0) for t in processed)
    r_values = [float(t["pnl_r"]) for t in processed if t.get("pnl_r") is not None]
    expectancy_r = sum(r_values) / len(r_values) if r_values else 0.0

    equity = 10000.0
    equity_curve: List[float] = []
    for t in processed:
        equity += float(t.get("pnl") or 0.0)
        equity_curve.append(equity)
    if not equity_curve:
        equity_curve = [equity]

    max_equity = equity_curve[0]
    max_dd = 0.0
    peak = max_equity
    for eq in equity_curve:
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak if peak > 0 else 0.0)

    return {
        "iteration": iteration,
        "seed": seed,
        "trades": total,
        "win_rate": win_rate,
        "expectancy_r": expectancy_r,
        "total_pnl": total_pnl,
        "max_drawdown": max_dd,
        "sharpe_ratio": None,
        "equity_curve": equity_curve[-200:],
    }


def _iteration_worker_pickled(
    iteration: int,
    seed: int,
    mode: str,
    trades_snapshot: List[Dict[str, Any]],
    jitter_params: Optional[Dict[str, float]],
) -> Dict[str, Any]:
    """Top-level worker for ProcessPoolExecutor (pickle-safe)."""
    return _iteration_metrics(iteration, seed, mode, trades_snapshot, jitter_params)


@dataclass
class MonteCarloConfig:
    """Monte Carlo run configuration"""
    run_id: str
    seed: int
    iterations: int
    workers: int
    mode: str  # "reshuffle", "resample", "jitter", "combined"
    jitter_params: Optional[Dict[str, float]] = None
    input_tournament: Optional[str] = None
    input_candles: Optional[str] = None


@dataclass
class MonteCarloResult:
    """Single Monte Carlo iteration result"""
    iteration: int
    seed: int
    trades: int
    win_rate: float
    expectancy_r: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: Optional[float]


@dataclass
class MonteCarloSummary:
    """Aggregated Monte Carlo results"""
    run_id: str
    config: Dict[str, Any]
    iterations: int
    completed: int
    expectancy_distribution: Dict[str, float]
    win_rate_distribution: Dict[str, float]
    drawdown_distribution: Dict[str, float]
    robustness_percentiles: Dict[str, float]
    results: List[Dict[str, Any]]


class MonteCarloRunner:
    """Monte Carlo research runner"""
    
    def __init__(self, config: MonteCarloConfig, output_dir: Path):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set seed for reproducibility
        random.seed(config.seed)
        if config.workers > 1:
            # For multiprocessing, we'll seed each worker separately
            pass
    
    def run(self) -> MonteCarloSummary:
        """Run Monte Carlo simulation"""
        logger.info(f"Starting Monte Carlo run: {self.config.run_id}")
        logger.info(f"Iterations: {self.config.iterations}, Workers: {self.config.workers}")

        trades_snapshot: List[Dict[str, Any]] = []
        if self.config.input_tournament:
            trades_snapshot = extract_trades_from_tournament_path(Path(self.config.input_tournament))
        if not trades_snapshot:
            logger.warning("Monte Carlo: no trades loaded — iterations return flat zero metrics.")

        results: List[MonteCarloResult] = []
        curve_samples: List[Dict[str, Any]] = []

        use_parallel = self.config.workers > 1 and self.config.iterations > 1
        if use_parallel:
            with ProcessPoolExecutor(max_workers=self.config.workers) as executor:
                futures = []
                for i in range(self.config.iterations):
                    seed = self.config.seed + i
                    futures.append(
                        executor.submit(
                            _iteration_worker_pickled,
                            i,
                            seed,
                            self.config.mode,
                            trades_snapshot,
                            self.config.jitter_params,
                        )
                    )

                for future in as_completed(futures):
                    try:
                        payload = future.result()
                        results.append(
                            MonteCarloResult(
                                iteration=payload["iteration"],
                                seed=payload["seed"],
                                trades=payload["trades"],
                                win_rate=payload["win_rate"],
                                expectancy_r=payload["expectancy_r"],
                                total_pnl=payload["total_pnl"],
                                max_drawdown=payload["max_drawdown"],
                                sharpe_ratio=payload["sharpe_ratio"],
                            )
                        )
                        if len(curve_samples) < 50:
                            curve_samples.append(
                                {
                                    "iteration": payload["iteration"],
                                    "seed": payload["seed"],
                                    "curve": payload.get("equity_curve", []),
                                }
                            )
                        if len(results) % 100 == 0:
                            logger.info(f"Completed {len(results)}/{self.config.iterations} iterations")
                    except Exception as e:
                        logger.error(f"Iteration failed: {e}")
        else:
            for i in range(self.config.iterations):
                seed = self.config.seed + i
                payload = _iteration_metrics(
                    i,
                    seed,
                    self.config.mode,
                    trades_snapshot,
                    self.config.jitter_params,
                )
                results.append(
                    MonteCarloResult(
                        iteration=payload["iteration"],
                        seed=payload["seed"],
                        trades=payload["trades"],
                        win_rate=payload["win_rate"],
                        expectancy_r=payload["expectancy_r"],
                        total_pnl=payload["total_pnl"],
                        max_drawdown=payload["max_drawdown"],
                        sharpe_ratio=payload["sharpe_ratio"],
                    )
                )
                if len(curve_samples) < 50:
                    curve_samples.append(
                        {
                            "iteration": payload["iteration"],
                            "seed": payload["seed"],
                            "curve": payload.get("equity_curve", []),
                        }
                    )
                if (i + 1) % 100 == 0:
                    logger.info(f"Completed {i + 1}/{self.config.iterations} iterations")

        results.sort(key=lambda r: r.iteration)

        # Calculate distributions
        expectancy_values = [r.expectancy_r for r in results]
        win_rate_values = [r.win_rate for r in results]
        drawdown_values = [r.max_drawdown for r in results]
        
        def percentile(values: List[float], p: float) -> float:
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * p)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]

        win_rate_std = _sample_stdev(win_rate_values)
        drawdown_std = _sample_stdev(drawdown_values)

        summary = MonteCarloSummary(
            run_id=self.config.run_id,
            config=asdict(self.config),
            iterations=self.config.iterations,
            completed=len(results),
            expectancy_distribution={
                "mean": sum(expectancy_values) / len(expectancy_values) if expectancy_values else 0.0,
                "std": (sum((x - sum(expectancy_values)/len(expectancy_values))**2 for x in expectancy_values) / len(expectancy_values))**0.5 if expectancy_values else 0.0,
                "min": min(expectancy_values) if expectancy_values else 0.0,
                "max": max(expectancy_values) if expectancy_values else 0.0,
                "p25": percentile(expectancy_values, 0.25),
                "p50": percentile(expectancy_values, 0.50),
                "p75": percentile(expectancy_values, 0.75),
                "p95": percentile(expectancy_values, 0.95)
            },
            win_rate_distribution={
                "mean": sum(win_rate_values) / len(win_rate_values) if win_rate_values else 0.0,
                "std": win_rate_std,
                "min": min(win_rate_values) if win_rate_values else 0.0,
                "max": max(win_rate_values) if win_rate_values else 0.0,
                "p50": percentile(win_rate_values, 0.50)
            },
            drawdown_distribution={
                "mean": sum(drawdown_values) / len(drawdown_values) if drawdown_values else 0.0,
                "std": drawdown_std,
                "min": min(drawdown_values) if drawdown_values else 0.0,
                "max": max(drawdown_values) if drawdown_values else 0.0,
                "p95": percentile(drawdown_values, 0.95)
            },
            robustness_percentiles={
                "expectancy_p5": percentile(expectancy_values, 0.05),
                "expectancy_p95": percentile(expectancy_values, 0.95),
                "win_rate_p5": percentile(win_rate_values, 0.05),
                "win_rate_p95": percentile(win_rate_values, 0.95)
            },
            results=[asdict(r) for r in results]
        )
        
        # Write output (include diagnostics: reshuffle leaves expectancy/win_rate invariant)
        summary_file = self.output_dir / "monte_carlo_summary.json"
        mode = self.config.mode
        trades_n = len(trades_snapshot)
        inv_shuffle = mode in ("reshuffle", "combined") and trades_n > 0
        summary_payload = asdict(summary)
        summary_payload["diagnostics"] = {
            "trades_loaded": trades_n,
            "mode": mode,
            "expectancy_r_std_across_iterations": summary.expectancy_distribution["std"],
            "win_rate_std_across_iterations": win_rate_std,
            "max_drawdown_std_across_iterations": drawdown_std,
            "permutation_invariant_expectancy_and_win_rate": inv_shuffle,
            "note": (
                "Under reshuffle/combined (shuffle-only), win_rate and expectancy_r are multiset "
                "statistics: identical for every permutation of the same trade list. std≈0 is "
                "expected and does not indicate a broken runner. For variation in those metrics "
                "use --mode resample (bootstrap with replacement) or jitter; interpret "
                "max_drawdown std for path-sequence risk under reshuffle."
                if inv_shuffle
                else (
                    "Bootstrap/resample or jitter alters the multiset or marks; non-zero spread in "
                    "expectancy/win_rate is meaningful if trades_loaded > 0."
                )
            ),
        }
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

        drawdown_payload = {
            "schema": "fxg.monte_carlo.drawdown_distribution.v1",
            "run_id": self.config.run_id,
            "stats": summary.drawdown_distribution,
            "values": drawdown_values,
        }
        with open(self.output_dir / "drawdown_distribution.json", "w", encoding="utf-8") as f:
            json.dump(drawdown_payload, f, indent=2)

        with open(self.output_dir / "equity_curve_samples.json", "w", encoding="utf-8") as f:
            json.dump(
                {"schema": "fxg.monte_carlo.equity_curve_samples.v1", "run_id": self.config.run_id, "samples": curve_samples},
                f,
                indent=2,
            )

        risk_summary = {
            "schema": "fxg.monte_carlo.risk_summary.v1",
            "run_id": self.config.run_id,
            "input_trades": len(trades_snapshot),
            "iterations": summary.iterations,
            "completed": summary.completed,
            "expectancy": summary.expectancy_distribution,
            "win_rate": summary.win_rate_distribution,
            "drawdown": summary.drawdown_distribution,
            "robustness_percentiles": summary.robustness_percentiles,
        }
        with open(self.output_dir / "risk_summary.json", "w", encoding="utf-8") as f:
            json.dump(risk_summary, f, indent=2)

        logger.info(f"Monte Carlo complete: {summary_file}")
        return summary
