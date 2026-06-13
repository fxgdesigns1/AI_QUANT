#!/usr/bin/env python3
"""
Market Readiness Audit and GO/NO-GO Decision
Comprehensive audit of market conditions, system health, and execution readiness.
"""
import sys
import os
import json
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/market_readiness_audit.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("market_readiness_audit")

# Output paths (VM paths, will be adapted for local)
# Try /opt/ai-quant/runtime first, then fallback to project runtime, then local runtime
if os.path.exists("/opt/ai-quant/runtime") and os.access("/opt/ai-quant/runtime", os.W_OK):
    RUNTIME_DIR = Path("/opt/ai-quant/runtime")
elif os.path.exists(os.path.join(os.path.dirname(__file__), "../../runtime")):
    RUNTIME_DIR = Path(os.path.join(os.path.dirname(__file__), "../../runtime")).resolve()
else:
    RUNTIME_DIR = Path("runtime")
RUNTIME_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR = RUNTIME_DIR

# Load environment variables from /etc/ai-quant/.env if it exists (VM standard location)
ENV_FILE = Path("/etc/ai-quant/.env")
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    logger.info(f"Loaded environment from {ENV_FILE}")
elif Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(".env")
    logger.info("Loaded environment from .env")

# Audit results
AUDIT_RESULTS = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "phases": {}
}


def phase_1_market_readiness() -> Dict[str, Any]:
    """Phase 1: Market data freshness, volatility, trend, bias analysis"""
    logger.info("=" * 80)
    logger.info("PHASE 1: MARKET READINESS AUDIT")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "instruments": {},
        "summary": {}
    }
    
    instruments = ["XAU_USD", "EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]
    
    try:
        # Import market data provider
        from src.control_plane.market_data_provider import get_candles, get_latest_price
        from src.control_plane.outlook_engine import get_outlook_engine
        import pandas as pd
        import numpy as np
        
        outlook_engine = get_outlook_engine()
        
        # Helper functions for ATR/ADX
        def calculate_atr(df, period=14):
            high_low = df["high"] - df["low"]
            high_close = np.abs(df["high"] - df["close"].shift())
            low_close = np.abs(df["low"] - df["close"].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            return true_range.rolling(period).mean()
        
        def calculate_adx(df, period=14):
            plus_dm = df["high"].diff()
            minus_dm = df["low"].diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm > 0] = 0
            tr = calculate_atr(df, period)
            atr = tr.rolling(period).mean()
            plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
            minus_di = 100 * (minus_dm.ewm(alpha=1/period).mean() / atr)
            dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
            adx = dx.rolling(period).mean()
            return adx
        
        instruments_ready = 0
        instruments_shock = 0
        instruments_trending = 0
        instruments_with_bias = 0
        
        for instrument in instruments:
            logger.info(f"\n--- Analyzing {instrument} ---")
            inst_result = {
                "instrument": instrument,
                "status": "UNKNOWN",
                "data_freshness_seconds": None,
                "atr_percentile": None,
                "adx": None,
                "regime": None,
                "daily_bias": None,
                "weekly_bias": None,
                "session_alignment": None,
                "is_shock": False,
                "errors": []
            }
            
            try:
                # 1. Data Freshness
                price = get_latest_price(instrument, timeout_s=5.0)
                now = datetime.now(timezone.utc)
                if hasattr(price, 'time'):
                    price_time = price.time
                    if isinstance(price_time, str):
                        price_time = datetime.fromisoformat(price_time.replace('Z', '+00:00'))
                    age_seconds = (now - price_time).total_seconds()
                    inst_result["data_freshness_seconds"] = age_seconds
                    if age_seconds > 60:
                        inst_result["errors"].append(f"Stale data: {age_seconds:.1f}s old")
                
                # 2. Fetch H1 candles for analysis
                candles = get_candles(instrument, granularity="H1", count=24*90, timeout_s=10.0)
                if not candles or len(candles) < 24:
                    inst_result["errors"].append(f"Insufficient data: {len(candles) if candles else 0} candles")
                    results["instruments"][instrument] = inst_result
                    continue
                
                # Convert to DataFrame
                data_list = []
                for c in candles:
                    try:
                        d = {
                            "time": c.time,
                            "open": float(c.mid.o) if hasattr(c, 'mid') else float(c.o),
                            "high": float(c.mid.h) if hasattr(c, 'mid') else float(c.h),
                            "low": float(c.mid.l) if hasattr(c, 'mid') else float(c.l),
                            "close": float(c.mid.c) if hasattr(c, 'mid') else float(c.c),
                            "volume": float(c.volume) if hasattr(c, 'volume') else 0
                        }
                        data_list.append(d)
                    except Exception as e:
                        continue
                
                if not data_list:
                    inst_result["errors"].append("Failed to parse candle data")
                    results["instruments"][instrument] = inst_result
                    continue
                
                df = pd.DataFrame(data_list)
                df["time"] = pd.to_datetime(df["time"])
                df.set_index("time", inplace=True)
                
                # 3. ATR Analysis
                df["atr"] = calculate_atr(df)
                current_atr = df["atr"].iloc[-1]
                atr_history = df["atr"].dropna()
                atr_percentile = (atr_history < current_atr).mean() * 100
                inst_result["atr_percentile"] = atr_percentile
                
                is_shock = atr_percentile > 95
                inst_result["is_shock"] = is_shock
                if is_shock:
                    instruments_shock += 1
                    logger.warning(f"⚠️ {instrument}: SHOCK DETECTED (ATR% {atr_percentile:.1f} > 95%)")
                
                # 4. ADX & Trend
                df["adx"] = calculate_adx(df)
                current_adx = df["adx"].iloc[-1]
                inst_result["adx"] = float(current_adx) if not pd.isna(current_adx) else None
                
                regime = "RANGING"
                if is_shock:
                    regime = "SHOCK"
                elif current_adx > 25 and not pd.isna(current_adx):
                    regime = "TRENDING"
                    instruments_trending += 1
                
                inst_result["regime"] = regime
                
                # 5. Bias from OutlookEngine
                try:
                    daily_bias = outlook_engine.get_daily_bias(instrument)
                    weekly_bias = outlook_engine.get_weekly_bias(instrument)
                    inst_result["daily_bias"] = daily_bias
                    inst_result["weekly_bias"] = weekly_bias
                    
                    # Log explicit reason if bias is NEUTRAL (missing vs genuine neutral)
                    if daily_bias == "NEUTRAL":
                        logger.info(f"{instrument}: Daily bias is NEUTRAL (check logs for reason: missing snapshot vs genuine neutral)")
                    if weekly_bias == "NEUTRAL":
                        logger.info(f"{instrument}: Weekly bias is NEUTRAL (check logs for reason: missing snapshot vs genuine neutral)")
                    
                    # Count instruments with directional bias (not NEUTRAL)
                    if daily_bias not in ["NEUTRAL", None] or weekly_bias not in ["NEUTRAL", None]:
                        instruments_with_bias += 1
                except Exception as e:
                    inst_result["errors"].append(f"Bias lookup failed: {e}")
                    logger.error(f"Bias lookup exception for {instrument}: {e}", exc_info=True)
                
                # 6. Session Alignment
                current_hour = datetime.now(timezone.utc).hour
                session_ok = 6 <= current_hour < 16  # London + NY overlap
                inst_result["session_alignment"] = "ALIGNED" if session_ok else "OUTSIDE_SESSION"
                
                inst_result["status"] = "READY" if not inst_result["errors"] else "ERROR"
                if inst_result["status"] == "READY":
                    instruments_ready += 1
                
                results["instruments"][instrument] = inst_result
                logger.info(f"✓ {instrument}: {regime}, Daily={inst_result['daily_bias']}, Weekly={inst_result['weekly_bias']}")
                
            except Exception as e:
                logger.error(f"Failed to analyze {instrument}: {e}")
                inst_result["errors"].append(str(e))
                results["instruments"][instrument] = inst_result
        
        # Summary
        results["summary"] = {
            "total_instruments": len(instruments),
            "instruments_ready": instruments_ready,
            "instruments_shock": instruments_shock,
            "instruments_trending": instruments_trending,
            "instruments_with_bias": instruments_with_bias,
            "at_least_one_not_shock": instruments_shock < len(instruments),
            "at_least_one_trending": instruments_trending > 0,
            "at_least_one_with_bias": instruments_with_bias > 0
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 1 Complete: {instruments_ready}/{len(instruments)} instruments ready")
        
    except Exception as e:
        logger.error(f"Phase 1 failed: {e}")
        import traceback
        traceback.print_exc()
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_2_system_health() -> Dict[str, Any]:
    """Phase 2: System health audit (runner, execution gate, news, risk)"""
    logger.info("=" * 80)
    logger.info("PHASE 2: SYSTEM HEALTH AUDIT")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "runner": {},
        "execution_gate": {},
        "strategy_registry": {},
        "news": {},
        "risk_manager": {},
        "summary": {}
    }
    
    try:
        # 1. Runner Status
        logger.info("\n--- Checking Runner Status ---")
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "ai-quant-runner"],
                capture_output=True,
                text=True,
                timeout=5
            )
            runner_active = result.returncode == 0 and result.stdout.strip() == "active"
            results["runner"] = {
                "active": runner_active,
                "status": result.stdout.strip() if runner_active else "inactive",
                "error": result.stderr.strip() if result.stderr else None
            }
            logger.info(f"Runner: {'✓ ACTIVE' if runner_active else '✗ INACTIVE'}")
        except Exception as e:
            results["runner"] = {"active": False, "error": str(e)}
            logger.warning(f"Could not check runner status: {e}")
        
        # 2. Execution Gate
        logger.info("\n--- Checking Execution Gate ---")
        try:
            from src.core.execution_gate import ExecutionGuard
            guard = ExecutionGuard()
            decision = guard.decision()
            results["execution_gate"] = {
                "allowed": decision.allowed,
                "mode": decision.mode,
                "reason_code": decision.reason_code,
                "details": decision.details or {}
            }
            logger.info(f"Execution Gate: {'✓ ALLOWED' if decision.allowed else '✗ BLOCKED'} ({decision.reason_code})")
        except Exception as e:
            results["execution_gate"] = {"error": str(e)}
            logger.error(f"Execution gate check failed: {e}")
        
        # 3. Strategy Registry
        logger.info("\n--- Checking Strategy Registry ---")
        try:
            from src.control_plane.strategy_registry import get_strategy_registry
            registry = get_strategy_registry()
            strategies = registry.list_strategies()
            results["strategy_registry"] = {
                "status": "OK",
                "strategy_count": len(strategies),
                "strategies": [s.get("id", "unknown") for s in strategies]
            }
            logger.info(f"Strategy Registry: ✓ {len(strategies)} strategies registered")
        except Exception as e:
            results["strategy_registry"] = {"error": str(e)}
            logger.warning(f"Strategy registry check failed: {e}")
        
        # 4. News & Embargo
        logger.info("\n--- Checking News & Embargo ---")
        try:
            from src.control_plane.news_provider import fetch_news_with_registry
            news_items, status = fetch_news_with_registry(
                query="forex OR gold OR central bank OR fed OR ecb",
                threshold="high",
                max_items=10
            )
            
            now = datetime.now(timezone.utc).timestamp()
            embargo_window = 7200  # 2 hours
            active_embargoes = []
            for item in news_items:
                item_time = item.get("ts_utc") or item.get("datetime")
                if item_time:
                    try:
                        if isinstance(item_time, str):
                            item_dt = datetime.fromisoformat(item_time.replace('Z', '+00:00'))
                            item_ts = item_dt.timestamp()
                        else:
                            item_ts = float(item_time)
                        age = abs(now - item_ts)
                        if age < embargo_window:
                            impact = item.get("impact", "").lower()
                            category = item.get("category", "").lower()
                            if impact == "high" or category == "central_banks":
                                active_embargoes.append(item)
                    except Exception:
                        continue
            
            is_embargo = len(active_embargoes) > 0
            results["news"] = {
                "status": "OK",
                "items_fetched": len(news_items),
                "is_embargo": is_embargo,
                "active_embargoes": len(active_embargoes),
                "embargo_triggers": [{"title": e.get("title"), "impact": e.get("impact")} for e in active_embargoes[:3]]
            }
            logger.info(f"News: {'⚠️ EMBARGO ACTIVE' if is_embargo else '✓ NO EMBARGO'} ({len(active_embargoes)} triggers)")
        except Exception as e:
            results["news"] = {"error": str(e)}
            logger.warning(f"News check failed: {e}")
        
        # 5. Risk Manager (basic check)
        logger.info("\n--- Checking Risk Manager ---")
        try:
            # Check if risk manager module exists and can be imported
            from src.core.risk_manager import RiskManager
            risk_mgr = RiskManager()
            results["risk_manager"] = {"status": "OK", "available": True}
            logger.info("Risk Manager: ✓ Available")
        except ImportError:
            results["risk_manager"] = {"status": "NOT_AVAILABLE", "available": False}
            logger.warning("Risk Manager: Not available (optional)")
        except Exception as e:
            results["risk_manager"] = {"status": "ERROR", "error": str(e)}
            logger.warning(f"Risk Manager check failed: {e}")
        
        # Summary
        results["summary"] = {
            "runner_ok": results["runner"].get("active", False),
            "execution_gate_allowed": results["execution_gate"].get("allowed", False),
            "strategy_registry_ok": "error" not in results["strategy_registry"],
            "news_ok": "error" not in results["news"] and not results["news"].get("is_embargo", False),
            "risk_manager_ok": results["risk_manager"].get("available", False) or results["risk_manager"].get("status") == "NOT_AVAILABLE"
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 2 Complete")
        
    except Exception as e:
        logger.error(f"Phase 2 failed: {e}")
        import traceback
        traceback.print_exc()
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_3_execution_readiness() -> Dict[str, Any]:
    """Phase 3: Execution readiness dry-run test"""
    logger.info("=" * 80)
    logger.info("PHASE 3: EXECUTION READINESS DRY-RUN")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "execution_gate": {},
        "strategy_id_check": {},
        "trading_mode_check": {},
        "paper_mode_confirmed": False,
        "summary": {}
    }
    
    try:
        # 1. Execution Gate Decision
        logger.info("\n--- Execution Gate Decision ---")
        from src.core.execution_gate import ExecutionGuard
        guard = ExecutionGuard()
        decision = guard.decision()
        
        results["execution_gate"] = {
            "allowed": decision.allowed,
            "mode": decision.mode,
            "reason_code": decision.reason_code,
            "details": decision.details or {}
        }
        logger.info(f"Gate Decision: {'✓ ALLOWED' if decision.allowed else '✗ BLOCKED'} ({decision.reason_code})")
        
        # 2. Strategy ID Check
        logger.info("\n--- Strategy ID Validation ---")
        try:
            from src.control_plane.strategy_registry import validate_strategy_key
            test_strategies = ["session_execution", "momentum_v2", "gold_scalping"]
            valid_count = 0
            for strat_id in test_strategies:
                if validate_strategy_key(strat_id):
                    valid_count += 1
            results["strategy_id_check"] = {
                "status": "OK",
                "tested": len(test_strategies),
                "valid": valid_count
            }
            logger.info(f"Strategy ID Check: ✓ {valid_count}/{len(test_strategies)} valid")
        except Exception as e:
            results["strategy_id_check"] = {"error": str(e)}
            logger.warning(f"Strategy ID check failed: {e}")
        
        # 3. Trading Mode Check
        logger.info("\n--- Trading Mode Check ---")
        trading_mode = os.getenv("TRADING_MODE", "paper").lower()
        paper_enabled = (
            os.getenv("PAPER_EXECUTION_ENABLED", "").lower() in ("true", "1", "yes", "on") or
            os.getenv("EXECUTION_UNLOCK_OK", "").lower() in ("true", "1", "yes", "on")
        )
        results["trading_mode_check"] = {
            "mode": trading_mode,
            "paper_enabled": paper_enabled,
            "live_enabled": os.getenv("LIVE_TRADING_ENABLED", "").lower() in ("true", "1", "yes", "on")
        }
        results["paper_mode_confirmed"] = trading_mode == "paper" and paper_enabled
        logger.info(f"Trading Mode: {trading_mode.upper()}, Paper Enabled: {paper_enabled}")
        
        # Summary
        results["summary"] = {
            "execution_allowed": decision.allowed,
            "no_strategy_id_missing": "error" not in results["strategy_id_check"],
            "trading_disabled": not results["paper_mode_confirmed"],
            "paper_mode_confirmed": results["paper_mode_confirmed"]
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 3 Complete")
        
    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        import traceback
        traceback.print_exc()
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_4_go_no_go(phase1: Dict, phase2: Dict, phase3: Dict) -> Dict[str, Any]:
    """Phase 4: GO/NO-GO Decision"""
    logger.info("=" * 80)
    logger.info("PHASE 4: GO/NO-GO DECISION")
    logger.info("=" * 80)
    
    decision = {
        "status": "NO_GO",
        "reason": "Initial state",
        "criteria": {},
        "blockers": [],
        "warnings": []
    }
    
    # GO Criteria
    go_criteria = {
        "at_least_one_instrument_not_shock": phase1.get("summary", {}).get("at_least_one_not_shock", False),
        "directional_bias_present": phase1.get("summary", {}).get("at_least_one_with_bias", False),
        "execution_gate_allowed": phase3.get("execution_gate", {}).get("allowed", False),
        "no_news_embargo": not phase2.get("news", {}).get("is_embargo", True),
        "risk_manager_ok": phase2.get("summary", {}).get("risk_manager_ok", False)
    }
    
    decision["criteria"] = go_criteria
    
    # Check each criterion
    if not go_criteria["at_least_one_instrument_not_shock"]:
        decision["blockers"].append("All instruments in SHOCK regime")
    
    if not go_criteria["directional_bias_present"]:
        decision["blockers"].append("No directional bias present (all NEUTRAL)")
    
    if not go_criteria["execution_gate_allowed"]:
        reason = phase3.get("execution_gate", {}).get("reason_code", "UNKNOWN")
        decision["blockers"].append(f"Execution gate blocked: {reason}")
    
    if not go_criteria["no_news_embargo"]:
        embargo_count = phase2.get("news", {}).get("active_embargoes", 0)
        decision["blockers"].append(f"News embargo active ({embargo_count} triggers)")
    
    if not go_criteria["risk_manager_ok"]:
        decision["warnings"].append("Risk manager not available (non-blocking)")
    
    # Decision
    if len(decision["blockers"]) == 0:
        decision["status"] = "GO"
        decision["reason"] = "All GO criteria met"
    else:
        decision["status"] = "NO_GO"
        decision["reason"] = f"{len(decision['blockers'])} blocker(s) present"
    
    logger.info(f"\n{'='*80}")
    logger.info(f"DECISION: {decision['status']}")
    logger.info(f"Reason: {decision['reason']}")
    if decision["blockers"]:
        logger.info(f"\nBlockers:")
        for blocker in decision["blockers"]:
            logger.info(f"  ✗ {blocker}")
    if decision["warnings"]:
        logger.info(f"\nWarnings:")
        for warning in decision["warnings"]:
            logger.info(f"  ⚠ {warning}")
    logger.info(f"{'='*80}\n")
    
    return decision


def phase_5_conditional_enable(decision: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 5: Conditionally enable trading if GO"""
    logger.info("=" * 80)
    logger.info("PHASE 5: CONDITIONAL ENABLE TRADING")
    logger.info("=" * 80)
    
    results = {
        "status": "SKIPPED",
        "action": None,
        "flag_created": False
    }
    
    if decision.get("status") == "GO":
        try:
            flag_file = OUTPUT_DIR / "trading_ready.flag"
            with open(flag_file, "w") as f:
                f.write("PAPER_TRADING_ENABLED=true\n")
                f.write(f"ENABLED_AT={datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"DECISION={decision.get('status')}\n")
            results["status"] = "ENABLED"
            results["action"] = "trading_ready.flag created"
            results["flag_created"] = True
            results["flag_path"] = str(flag_file)
            logger.info(f"✓ Trading enabled: {flag_file}")
        except Exception as e:
            results["status"] = "FAILED"
            results["error"] = str(e)
            logger.error(f"Failed to create trading flag: {e}")
    else:
        results["action"] = "Trading NOT enabled (NO_GO decision)"
        logger.info("✗ Trading NOT enabled (NO_GO decision)")
    
    return results


def phase_6_verification(decision: Dict[str, Any], phase5: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 6: Final verification"""
    logger.info("=" * 80)
    logger.info("PHASE 6: FINAL VERIFICATION")
    logger.info("=" * 80)
    
    results = {
        "status": "COMPLETE",
        "decision_verified": False,
        "flag_verified": False,
        "summary": {}
    }
    
    # Verify decision file
    try:
        decision_file = OUTPUT_DIR / "WEEKLY_GO_NO_GO.json"
        with open(decision_file, "w") as f:
            json.dump(decision, f, indent=2)
        results["decision_verified"] = True
        results["decision_file"] = str(decision_file)
        logger.info(f"✓ Decision file: {decision_file}")
    except Exception as e:
        logger.error(f"Failed to write decision file: {e}")
    
    # Verify flag if GO
    if decision.get("status") == "GO":
        flag_file = OUTPUT_DIR / "trading_ready.flag"
        if flag_file.exists():
            results["flag_verified"] = True
            logger.info(f"✓ Trading flag exists: {flag_file}")
        else:
            logger.warning(f"⚠ Trading flag missing: {flag_file}")
    
    results["summary"] = {
        "decision": decision.get("status"),
        "decision_file_exists": results["decision_verified"],
        "flag_exists": results["flag_verified"] if decision.get("status") == "GO" else None
    }
    
    logger.info(f"\n✓ Phase 6 Complete")
    return results


def main():
    """Run complete market readiness audit"""
    logger.info("=" * 80)
    logger.info("MARKET READINESS AUDIT - START")
    logger.info("=" * 80)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Output Directory: {OUTPUT_DIR}")
    
    try:
        # Phase 1: Market Readiness
        phase1_result = phase_1_market_readiness()
        AUDIT_RESULTS["phases"]["phase_1_market_readiness"] = phase1_result
        
        # Phase 2: System Health
        phase2_result = phase_2_system_health()
        AUDIT_RESULTS["phases"]["phase_2_system_health"] = phase2_result
        
        # Phase 3: Execution Readiness
        phase3_result = phase_3_execution_readiness()
        AUDIT_RESULTS["phases"]["phase_3_execution_readiness"] = phase3_result
        
        # Phase 4: GO/NO-GO Decision
        decision = phase_4_go_no_go(phase1_result, phase2_result, phase3_result)
        AUDIT_RESULTS["phases"]["phase_4_go_no_go"] = decision
        AUDIT_RESULTS["final_decision"] = decision.get("status")
        
        # Phase 5: Conditional Enable
        phase5_result = phase_5_conditional_enable(decision)
        AUDIT_RESULTS["phases"]["phase_5_conditional_enable"] = phase5_result
        
        # Phase 6: Verification
        phase6_result = phase_6_verification(decision, phase5_result)
        AUDIT_RESULTS["phases"]["phase_6_verification"] = phase6_result
        
        # Save complete audit results
        # Convert numpy types to native Python types for JSON serialization
        def convert_to_native(obj):
            """Recursively convert numpy types to native Python types"""
            import numpy as np
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_native(item) for item in obj]
            return obj
        
        audit_file = OUTPUT_DIR / "MARKET_READINESS_AUDIT.json"
        with open(audit_file, "w") as f:
            json.dump(convert_to_native(AUDIT_RESULTS), f, indent=2)
        
        logger.info("=" * 80)
        logger.info("MARKET READINESS AUDIT - COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Final Decision: {decision.get('status')}")
        logger.info(f"Audit Report: {audit_file}")
        
        # Exit code based on decision
        if decision.get("status") == "GO":
            logger.info("✓ SYSTEM READY FOR PAPER TRADING")
            return 0
        else:
            logger.warning("✗ SYSTEM NOT READY - BLOCKERS PRESENT")
            return 1
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
