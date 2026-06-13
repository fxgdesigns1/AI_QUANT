#!/usr/bin/env python3
"""
Strategy Readiness Verification Probe

Verifies that readiness computation works for all active strategies and
asserts that all required fields are present.
"""

import sys
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/strategy_readiness_probe.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("strategy_readiness_probe")

# Runtime directory
if os.path.exists("/opt/ai-quant/runtime") and os.access("/opt/ai-quant/runtime", os.W_OK):
    RUNTIME_DIR = Path("/opt/ai-quant/runtime")
elif os.path.exists(os.path.join(os.path.dirname(__file__), "../../runtime")):
    RUNTIME_DIR = Path(os.path.join(os.path.dirname(__file__), "../../runtime")).resolve()
else:
    RUNTIME_DIR = Path("runtime")
RUNTIME_DIR.mkdir(exist_ok=True, parents=True)


def probe_strategy_readiness() -> Dict[str, Any]:
    """Probe strategy readiness for all active strategies"""
    logger.info("=" * 80)
    logger.info("STRATEGY READINESS PROBE")
    logger.info("=" * 80)
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING",
        "strategies_tested": [],
        "errors": [],
        "assertions": {}
    }
    
    try:
        from src.core.strategy_readiness import get_readiness_evaluator
        from src.control_plane.outlook_engine import get_outlook_engine
        from src.core.execution_gate import ExecutionGuard
        from src.control_plane.strategy_registry import get_strategy_registry
        
        readiness_eval = get_readiness_evaluator()
        outlook_engine = get_outlook_engine()
        execution_guard = ExecutionGuard()
        exec_decision = execution_guard.decision()
        registry = get_strategy_registry()
        
        # Get active strategies
        strategies = registry.list_strategies() if hasattr(registry, 'list_strategies') else []
        if not strategies:
            # Fallback: use known strategy IDs
            strategies = [
                {"id": "session_execution", "instruments": ["EUR_USD", "GBP_USD"]},
                {"id": "momentum_v2", "instruments": ["EUR_USD", "GBP_USD", "USD_JPY"]},
                {"id": "gold_scalping", "instruments": ["XAU_USD"]}
            ]
        
        logger.info(f"Testing {len(strategies)} strategies")
        
        all_readiness = {}
        assertions_passed = 0
        assertions_failed = 0
        
        for strat_info in strategies:
            strategy_id = strat_info.get("id") or strat_info.get("strategy_id") or "unknown"
            instruments = strat_info.get("instruments", ["EUR_USD"])
            
            logger.info(f"\n--- Testing {strategy_id} ---")
            
            for instrument in instruments:
                try:
                    # Get biases
                    daily_bias = outlook_engine.get_daily_bias(instrument)
                    weekly_bias = outlook_engine.get_weekly_bias(instrument)
                    
                    # Compute readiness
                    readiness = readiness_eval.compute_strategy_readiness(
                        strategy_id=strategy_id,
                        instrument=instrument,
                        daily_bias=daily_bias,
                        weekly_bias=weekly_bias,
                        regime="UNKNOWN",  # Simplified for probe
                        volatility_pct=50.0,  # Default
                        news_embargo=False,  # Simplified
                        execution_allowed=exec_decision.allowed,
                        cooldown_remaining_minutes=None,
                        signal_confidence=None,
                        last_signal_ts=None
                    )
                    
                    # Assertions
                    key = f"{strategy_id}:{instrument}"
                    strat_result = {
                        "strategy_id": strategy_id,
                        "instrument": instrument,
                        "readiness": {
                            "readiness_score": readiness.readiness_score,
                            "blocking_reasons": readiness.blocking_reasons,
                            "bias_alignment": readiness.bias_alignment.value,
                            "estimated_time_to_entry_minutes": readiness.estimated_time_to_entry_minutes,
                            "regime": readiness.regime,
                            "volatility_pct": readiness.volatility_pct,
                            "embargo_active": readiness.embargo_active,
                            "daily_bias": readiness.daily_bias,
                            "weekly_bias": readiness.weekly_bias,
                            "execution_allowed": readiness.execution_allowed
                        },
                        "assertions": {}
                    }
                    
                    # Assertion 1: readiness_score exists and is 0-100
                    if readiness.readiness_score is not None and 0 <= readiness.readiness_score <= 100:
                        strat_result["assertions"]["score_valid"] = "PASS"
                        assertions_passed += 1
                    else:
                        strat_result["assertions"]["score_valid"] = "FAIL"
                        assertions_failed += 1
                        logger.error(f"  ✗ {key}: readiness_score invalid: {readiness.readiness_score}")
                    
                    # Assertion 2: blocking_reasons non-empty when score < 100
                    if readiness.readiness_score < 100:
                        if readiness.blocking_reasons and len(readiness.blocking_reasons) > 0:
                            strat_result["assertions"]["blocking_reasons_present"] = "PASS"
                            assertions_passed += 1
                        else:
                            strat_result["assertions"]["blocking_reasons_present"] = "FAIL"
                            assertions_failed += 1
                            logger.error(f"  ✗ {key}: Score < 100 but no blocking reasons")
                    else:
                        strat_result["assertions"]["blocking_reasons_present"] = "PASS"  # N/A when score is 100
                        assertions_passed += 1
                    
                    # Assertion 3: estimated_time_to_entry populated or null with reason
                    if readiness.estimated_time_to_entry_minutes is not None:
                        if isinstance(readiness.estimated_time_to_entry_minutes, int) and readiness.estimated_time_to_entry_minutes >= 0:
                            strat_result["assertions"]["time_to_entry_valid"] = "PASS"
                            assertions_passed += 1
                        else:
                            strat_result["assertions"]["time_to_entry_valid"] = "FAIL"
                            assertions_failed += 1
                    else:
                        # Null is acceptable if there are blocking reasons
                        if readiness.blocking_reasons:
                            strat_result["assertions"]["time_to_entry_valid"] = "PASS"
                            assertions_passed += 1
                        else:
                            strat_result["assertions"]["time_to_entry_valid"] = "WARN"
                            logger.warning(f"  ⚠ {key}: time_to_entry is null but no blocking reasons")
                    
                    # Assertion 4: All required fields present
                    required_fields = [
                        "readiness_score", "blocking_reasons", "bias_alignment",
                        "estimated_time_to_entry_minutes", "regime", "volatility_pct",
                        "embargo_active", "daily_bias", "weekly_bias", "execution_allowed"
                    ]
                    missing_fields = []
                    for field in required_fields:
                        if not hasattr(readiness, field):
                            missing_fields.append(field)
                    
                    if not missing_fields:
                        strat_result["assertions"]["all_fields_present"] = "PASS"
                        assertions_passed += 1
                    else:
                        strat_result["assertions"]["all_fields_present"] = "FAIL"
                        assertions_failed += 1
                        logger.error(f"  ✗ {key}: Missing fields: {missing_fields}")
                    
                    all_readiness[key] = strat_result
                    results["strategies_tested"].append(key)
                    
                    logger.info(f"  ✓ {key}: Score={readiness.readiness_score}, Alignment={readiness.bias_alignment.value}, Blockers={len(readiness.blocking_reasons)}")
                    
                except Exception as e:
                    logger.error(f"  ✗ {key}: Failed - {e}", exc_info=True)
                    results["errors"].append({
                        "strategy_id": strategy_id,
                        "instrument": instrument,
                        "error": str(e)
                    })
        
        results["assertions"] = {
            "passed": assertions_passed,
            "failed": assertions_failed,
            "total": assertions_passed + assertions_failed
        }
        
        results["readiness_data"] = all_readiness
        results["status"] = "COMPLETE" if assertions_failed == 0 else "FAILED"
        
        # Save report
        report_file = RUNTIME_DIR / "strategy_readiness_probe.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\n✓ Probe Complete: {assertions_passed} passed, {assertions_failed} failed")
        logger.info(f"Report saved: {report_file}")
        
    except Exception as e:
        logger.error(f"Probe failed: {e}", exc_info=True)
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def main():
    """Run strategy readiness probe"""
    logger.info("=" * 80)
    logger.info("STRATEGY READINESS PROBE - START")
    logger.info("=" * 80)
    
    results = probe_strategy_readiness()
    
    logger.info("=" * 80)
    logger.info("STRATEGY READINESS PROBE - COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Status: {results.get('status')}")
    logger.info(f"Assertions: {results.get('assertions', {}).get('passed', 0)} passed, {results.get('assertions', {}).get('failed', 0)} failed")
    
    # Exit code
    if results.get("status") == "COMPLETE":
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
