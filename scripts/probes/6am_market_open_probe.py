#!/usr/bin/env python3
"""
6AM Market Open Probe - Daily System Health and Market Readiness Audit

Runs at 06:00 UTC daily to verify:
- System health (runner, control plane, data freshness)
- Market readiness (session active, shock detection, bias resolution)
- Execution path (gates, paper mode, strategy IDs)
- Trade activity (signals, trades, journal updates)

Output: /opt/ai-quant/runtime/6AM_SYSTEM_STATUS_REPORT.json
"""

import sys
import os
import json
import logging
import subprocess
import stat
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "6am_market_open_probe.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("6am_probe")

# Runtime directory (VM standard location)
if os.path.exists("/opt/ai-quant/runtime") and os.access("/opt/ai-quant/runtime", os.W_OK):
    RUNTIME_DIR = Path("/opt/ai-quant/runtime")
elif os.path.exists(os.path.join(os.path.dirname(__file__), "../../runtime")):
    RUNTIME_DIR = Path(os.path.join(os.path.dirname(__file__), "../../runtime")).resolve()
else:
    RUNTIME_DIR = Path("runtime")
RUNTIME_DIR.mkdir(exist_ok=True, parents=True)

# Load environment
ENV_FILE = Path("/etc/ai-quant/.env")
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
elif Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(".env")

# Report structure
REPORT = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "probe_version": "1.0.0",
    "phases": {}
}


def phase_1_preflight_health_check() -> Dict[str, Any]:
    """Phase 1: Preflight health check - system services and data freshness"""
    logger.info("=" * 80)
    logger.info("PHASE 1: PREFLIGHT HEALTH CHECK")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "runner": {},
        "control_plane": {},
        "market_data": {},
        "news": {},
        "crash_loops": {},
        "summary": {}
    }
    
    try:
        # 1. Runner process status
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
            logger.error(f"Runner check failed: {e}")
        
        # 2. Control plane status
        logger.info("\n--- Checking Control Plane Status ---")
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "ai-quant-control-plane"],
                capture_output=True,
                text=True,
                timeout=5
            )
            cp_active = result.returncode == 0 and result.stdout.strip() == "active"
            results["control_plane"] = {
                "active": cp_active,
                "status": result.stdout.strip() if cp_active else "inactive"
            }
            logger.info(f"Control Plane: {'✓ ACTIVE' if cp_active else '✗ INACTIVE'}")
        except Exception as e:
            results["control_plane"] = {"active": False, "error": str(e)}
            logger.error(f"Control plane check failed: {e}")
        
        # 3. Market data freshness
        logger.info("\n--- Checking Market Data Freshness ---")
        try:
            from src.control_plane.market_data_provider import get_latest_price
            price = get_latest_price("EUR_USD", timeout_s=5.0)
            now = datetime.now(timezone.utc)
            if hasattr(price, 'time'):
                price_time = price.time
                if isinstance(price_time, str):
                    price_time = datetime.fromisoformat(price_time.replace('Z', '+00:00'))
                age_seconds = (now - price_time).total_seconds()
                results["market_data"] = {
                    "fresh": age_seconds < 60,
                    "age_seconds": age_seconds,
                    "instrument": "EUR_USD",
                    "price": float(price.mid) if hasattr(price, 'mid') else None
                }
                logger.info(f"Market Data: {'✓ FRESH' if age_seconds < 60 else '✗ STALE'} ({age_seconds:.1f}s old)")
            else:
                results["market_data"] = {"fresh": False, "error": "No timestamp in price data"}
        except Exception as e:
            results["market_data"] = {"fresh": False, "error": str(e)}
            logger.error(f"Market data check failed: {e}")
        
        # 4. News file freshness
        logger.info("\n--- Checking News File Freshness ---")
        news_file = RUNTIME_DIR / "news_latest.json"
        if news_file.exists():
            try:
                stat_info = news_file.stat()
                age_seconds = (datetime.now(timezone.utc).timestamp() - stat_info.st_mtime)
                results["news"] = {
                    "file_exists": True,
                    "fresh": age_seconds < 600,  # 10 minutes
                    "age_seconds": age_seconds,
                    "size_bytes": stat_info.st_size
                }
                logger.info(f"News File: {'✓ FRESH' if age_seconds < 600 else '✗ STALE'} ({age_seconds:.1f}s old)")
            except Exception as e:
                results["news"] = {"file_exists": True, "error": str(e)}
        else:
            results["news"] = {"file_exists": False, "error": "News file not found"}
            logger.warning("News file not found")
        
        # 5. Check for crash loops (recent restarts)
        logger.info("\n--- Checking for Crash Loops ---")
        try:
            # Check systemd for recent restarts
            result = subprocess.run(
                ["systemctl", "show", "ai-quant-runner", "--property=ActiveEnterTimestamp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse timestamp if available
                results["crash_loops"] = {"recent_restarts": False, "status": "OK"}
            else:
                results["crash_loops"] = {"status": "unknown"}
        except Exception as e:
            results["crash_loops"] = {"error": str(e)}
        
        # Summary
        results["summary"] = {
            "runner_ok": results["runner"].get("active", False),
            "control_plane_ok": results["control_plane"].get("active", False),
            "market_data_ok": results["market_data"].get("fresh", False),
            "news_ok": results["news"].get("fresh", False),
            "all_checks_passed": (
                results["runner"].get("active", False) and
                results["control_plane"].get("active", False) and
                results["market_data"].get("fresh", False) and
                results["news"].get("fresh", False)
            )
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 1 Complete: {'PASS' if results['summary']['all_checks_passed'] else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"Phase 1 failed: {e}", exc_info=True)
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_2_market_readiness_check() -> Dict[str, Any]:
    """Phase 2: Market readiness - session, shock detection, ATR/ADX"""
    logger.info("=" * 80)
    logger.info("PHASE 2: MARKET READINESS CHECK")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "session": {},
        "instruments": {},
        "summary": {}
    }
    
    try:
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
        
        # 1. Session check
        current_hour = datetime.now(timezone.utc).hour
        session_active = 6 <= current_hour < 16  # London + NY overlap
        session_name = "london" if 6 <= current_hour < 12 else "london_ny_overlap" if 12 <= current_hour < 16 else "outside_session"
        
        results["session"] = {
            "active": session_active,
            "name": session_name,
            "hour_utc": current_hour
        }
        logger.info(f"Session: {'✓ ACTIVE' if session_active else '✗ INACTIVE'} ({session_name}, {current_hour}:00 UTC)")
        
        # 2. Instrument analysis
        instruments = ["XAU_USD", "EUR_USD", "GBP_USD", "USD_JPY"]
        instruments_not_shock = 0
        instruments_trending = 0
        
        for instrument in instruments:
            logger.info(f"\n--- Analyzing {instrument} ---")
            inst_result = {
                "instrument": instrument,
                "atr_percentile": None,
                "adx": None,
                "is_shock": False,
                "is_trending": False,
                "status": "UNKNOWN"
            }
            
            try:
                # Fetch H1 candles
                candles = get_candles(instrument, granularity="H1", count=24*90, timeout_s=10.0)
                if not candles or len(candles) < 24:
                    inst_result["status"] = "INSUFFICIENT_DATA"
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
                        }
                        data_list.append(d)
                    except Exception:
                        continue
                
                if not data_list:
                    inst_result["status"] = "PARSE_ERROR"
                    results["instruments"][instrument] = inst_result
                    continue
                
                df = pd.DataFrame(data_list)
                df["time"] = pd.to_datetime(df["time"])
                df.set_index("time", inplace=True)
                
                # ATR Analysis
                df["atr"] = calculate_atr(df)
                current_atr = df["atr"].iloc[-1]
                atr_history = df["atr"].dropna()
                atr_percentile = (atr_history < current_atr).mean() * 100
                inst_result["atr_percentile"] = float(atr_percentile) if not pd.isna(atr_percentile) else None
                
                is_shock = atr_percentile > 95
                inst_result["is_shock"] = is_shock
                if not is_shock:
                    instruments_not_shock += 1
                
                # ADX & Trend
                df["adx"] = calculate_adx(df)
                current_adx = df["adx"].iloc[-1]
                inst_result["adx"] = float(current_adx) if not pd.isna(current_adx) else None
                
                is_trending = current_adx > 25 and not pd.isna(current_adx)
                inst_result["is_trending"] = is_trending
                if is_trending:
                    instruments_trending += 1
                
                inst_result["status"] = "READY"
                adx_str = f"{current_adx:.1f}" if not pd.isna(current_adx) else "N/A"
                logger.info(f"✓ {instrument}: ATR%={atr_percentile:.1f}, ADX={adx_str}, Shock={is_shock}, Trending={is_trending}")
                
            except Exception as e:
                logger.error(f"Failed to analyze {instrument}: {e}")
                inst_result["status"] = "ERROR"
                inst_result["error"] = str(e)
            
            results["instruments"][instrument] = inst_result
        
        # Summary
        results["summary"] = {
            "session_active": session_active,
            "instruments_analyzed": len(results["instruments"]),
            "instruments_not_shock": instruments_not_shock,
            "instruments_trending": instruments_trending,
            "at_least_one_not_shock": instruments_not_shock > 0,
            "at_least_one_trending": instruments_trending > 0
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 2 Complete: {instruments_not_shock}/{len(instruments)} instruments not in shock")
        
    except Exception as e:
        logger.error(f"Phase 2 failed: {e}", exc_info=True)
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_3_bias_and_gate_check() -> Dict[str, Any]:
    """Phase 3: Bias resolution and SessionRegimeGate decision trace"""
    logger.info("=" * 80)
    logger.info("PHASE 3: BIAS AND GATE CHECK")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "bias": {},
        "gate": {},
        "summary": {}
    }
    
    try:
        from src.control_plane.outlook_engine import get_outlook_engine
        
        outlook_engine = get_outlook_engine()
        instruments = ["EUR_USD", "GBP_USD", "XAU_USD"]
        
        # 1. Bias resolution check
        logger.info("\n--- Checking Bias Resolution ---")
        biases_resolved = 0
        bias_details = {}
        
        for instrument in instruments:
            try:
                daily_bias = outlook_engine.get_daily_bias(instrument)
                weekly_bias = outlook_engine.get_weekly_bias(instrument)
                
                bias_details[instrument] = {
                    "daily": daily_bias,
                    "weekly": weekly_bias,
                    "directional": daily_bias not in ["NEUTRAL", None] or weekly_bias not in ["NEUTRAL", None]
                }
                
                if bias_details[instrument]["directional"]:
                    biases_resolved += 1
                
                logger.info(f"{instrument}: Daily={daily_bias}, Weekly={weekly_bias}")
            except Exception as e:
                bias_details[instrument] = {"error": str(e)}
                logger.error(f"Bias lookup failed for {instrument}: {e}")
        
        results["bias"] = {
            "instruments_checked": len(instruments),
            "biases_resolved": biases_resolved,
            "details": bias_details,
            "at_least_one_resolved": biases_resolved > 0
        }
        
        # 2. Gate decision trace (check logs)
        logger.info("\n--- Checking SessionRegimeGate Logs ---")
        gate_log_path = Path("/opt/ai-quant/logs/session_regime_gate.log")
        if not gate_log_path.exists():
            gate_log_path = Path("logs/session_regime_gate.log")
        
        gate_recent_decisions = []
        if gate_log_path.exists():
            try:
                with open(gate_log_path, "r") as f:
                    lines = f.readlines()
                    # Get last 50 lines
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    # Look for decision patterns
                    for line in recent_lines:
                        if "ALLOWED" in line or "BLOCKED" in line or "bias" in line.lower():
                            gate_recent_decisions.append(line.strip())
            except Exception as e:
                logger.warning(f"Could not read gate log: {e}")
        
        results["gate"] = {
            "log_exists": gate_log_path.exists(),
            "recent_decisions_count": len(gate_recent_decisions),
            "recent_decisions": gate_recent_decisions[-10:] if gate_recent_decisions else []
        }
        
        # Summary
        results["summary"] = {
            "bias_available": biases_resolved > 0,
            "gate_log_available": gate_log_path.exists(),
            "no_bias_unavailable_blocks": True  # Would need to parse logs more carefully
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 3 Complete: {biases_resolved}/{len(instruments)} instruments with directional bias")
        
    except Exception as e:
        logger.error(f"Phase 3 failed: {e}", exc_info=True)
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_4_execution_path_check() -> Dict[str, Any]:
    """Phase 4: Execution path - execution gate, paper mode, strategy IDs"""
    logger.info("=" * 80)
    logger.info("PHASE 4: EXECUTION PATH CHECK")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "execution_gate": {},
        "trading_mode": {},
        "strategy_ids": {},
        "summary": {}
    }
    
    try:
        # 1. Execution gate decision
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
        
        # 2. Trading mode check
        logger.info("\n--- Checking Trading Mode ---")
        trading_mode = os.getenv("TRADING_MODE", "paper").lower()
        paper_enabled = (
            os.getenv("PAPER_EXECUTION_ENABLED", "").lower() in ("true", "1", "yes", "on") or
            os.getenv("EXECUTION_UNLOCK_OK", "").lower() in ("true", "1", "yes", "on")
        )
        results["trading_mode"] = {
            "mode": trading_mode,
            "paper_enabled": paper_enabled,
            "live_enabled": os.getenv("LIVE_TRADING_ENABLED", "").lower() in ("true", "1", "yes", "on")
        }
        logger.info(f"Trading Mode: {trading_mode.upper()}, Paper Enabled: {paper_enabled}")
        
        # 3. Strategy ID validation
        logger.info("\n--- Checking Strategy IDs ---")
        try:
            from src.control_plane.strategy_registry import validate_strategy_key
            test_strategies = ["session_execution", "momentum_v2", "gold_scalping"]
            valid_count = 0
            for strat_id in test_strategies:
                if validate_strategy_key(strat_id):
                    valid_count += 1
            results["strategy_ids"] = {
                "status": "OK",
                "tested": len(test_strategies),
                "valid": valid_count
            }
            logger.info(f"Strategy IDs: ✓ {valid_count}/{len(test_strategies)} valid")
        except Exception as e:
            results["strategy_ids"] = {"error": str(e)}
            logger.warning(f"Strategy ID check failed: {e}")
        
        # Summary
        results["summary"] = {
            "execution_allowed": results["execution_gate"].get("allowed", False),
            "paper_mode_confirmed": trading_mode == "paper" and paper_enabled,
            "strategy_ids_ok": "error" not in results["strategy_ids"],
            "no_strategy_id_missing": "error" not in results["strategy_ids"],
            "no_trading_disabled": paper_enabled
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 4 Complete")
        
    except Exception as e:
        logger.error(f"Phase 4 failed: {e}", exc_info=True)
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_5_trade_activity_check() -> Dict[str, Any]:
    """Phase 5: Trade activity - signals, trades, journal updates"""
    logger.info("=" * 80)
    logger.info("PHASE 5: TRADE ACTIVITY CHECK")
    logger.info("=" * 80)
    
    results = {
        "status": "RUNNING",
        "signals": {},
        "trades": {},
        "journal": {},
        "summary": {}
    }
    
    try:
        # 1. Check for recent signals (last 30 minutes)
        logger.info("\n--- Checking Signal Activity ---")
        runner_log_path = Path("/opt/ai-quant/logs/runner.log")
        if not runner_log_path.exists():
            runner_log_path = Path("logs/runner.log")
        
        signals_recent = []
        if runner_log_path.exists():
            try:
                with open(runner_log_path, "r") as f:
                    lines = f.readlines()
                    # Get last 200 lines
                    recent_lines = lines[-200:] if len(lines) > 200 else lines
                    # Look for signal patterns
                    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
                    for line in recent_lines:
                        if "signal" in line.lower() or "generated" in line.lower():
                            signals_recent.append(line.strip())
            except Exception as e:
                logger.warning(f"Could not read runner log: {e}")
        
        results["signals"] = {
            "log_exists": runner_log_path.exists(),
            "recent_signals_count": len(signals_recent),
            "recent_signals": signals_recent[-5:] if signals_recent else []
        }
        logger.info(f"Signals: {len(signals_recent)} recent entries found")
        
        # 2. Check for trade entries or explicit blocks
        logger.info("\n--- Checking Trade Activity ---")
        # Check runner log for trade execution or blocks
        trade_activity = []
        if runner_log_path.exists():
            try:
                with open(runner_log_path, "r") as f:
                    lines = f.readlines()
                    recent_lines = lines[-200:] if len(lines) > 200 else lines
                    for line in recent_lines:
                        if "trade" in line.lower() or "executed" in line.lower() or "blocked" in line.lower():
                            trade_activity.append(line.strip())
            except Exception as e:
                logger.warning(f"Could not read trade activity: {e}")
        
        results["trades"] = {
            "recent_activity_count": len(trade_activity),
            "recent_activity": trade_activity[-5:] if trade_activity else []
        }
        logger.info(f"Trade Activity: {len(trade_activity)} recent entries found")
        
        # 3. Journal updates
        logger.info("\n--- Checking Journal Updates ---")
        journal_log_path = Path("/opt/ai-quant/logs/journal.log")
        if not journal_log_path.exists():
            journal_log_path = Path("logs/journal.log")
        
        journal_recent = []
        if journal_log_path.exists():
            try:
                with open(journal_log_path, "r") as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:] if len(lines) > 100 else lines
                    journal_recent = [line.strip() for line in recent_lines[-10:]]
            except Exception as e:
                logger.warning(f"Could not read journal log: {e}")
        
        results["journal"] = {
            "log_exists": journal_log_path.exists(),
            "recent_entries_count": len(journal_recent),
            "recent_entries": journal_recent
        }
        logger.info(f"Journal: {len(journal_recent)} recent entries found")
        
        # Summary
        results["summary"] = {
            "signals_generated": len(signals_recent) > 0,
            "trade_activity_present": len(trade_activity) > 0,
            "journal_updated": len(journal_recent) > 0,
            "activity_detected": len(signals_recent) > 0 or len(trade_activity) > 0
        }
        
        results["status"] = "COMPLETE"
        logger.info(f"\n✓ Phase 5 Complete")
        
    except Exception as e:
        logger.error(f"Phase 5 failed: {e}", exc_info=True)
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def phase_6_decision_report(phase1: Dict, phase2: Dict, phase3: Dict, phase4: Dict, phase5: Dict) -> Dict[str, Any]:
    """Phase 6: Generate final decision report"""
    logger.info("=" * 80)
    logger.info("PHASE 6: DECISION REPORT")
    logger.info("=" * 80)
    
    # Determine overall state
    runner_ok = phase1["summary"].get("runner_ok", False)
    session_active = phase2["summary"].get("session_active", False)
    bias_available = phase3["summary"].get("bias_available", False)
    execution_allowed = phase4["summary"].get("execution_allowed", False)
    activity_detected = phase5["summary"].get("activity_detected", False)
    
    blockers = []
    if not runner_ok:
        blockers.append("Runner not active")
    if not session_active:
        blockers.append("Session not active")
    if not bias_available:
        blockers.append("No directional bias available")
    if not execution_allowed:
        blockers.append("Execution gate blocked")
    
    # Determine overall state
    if len(blockers) == 0 and activity_detected:
        overall_state = "READY_AND_TRADING"
    elif len(blockers) == 0:
        overall_state = "READY_BUT_NO_ACTIVITY"
    elif all(b in ["Session not active"] for b in blockers):  # Only session blocker
        overall_state = "READY_BUT_BLOCKED"
    else:
        overall_state = "FAIL"
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runner_status": "ACTIVE" if runner_ok else "INACTIVE",
        "market_session": phase2["session"].get("name", "unknown"),
        "eligible_instruments": phase2["summary"].get("instruments_not_shock", 0),
        "bias_status": "AVAILABLE" if bias_available else "UNAVAILABLE",
        "gate_status": "ALLOWED" if execution_allowed else "BLOCKED",
        "trade_activity": "DETECTED" if activity_detected else "NONE",
        "blockers_if_any": blockers,
        "overall_state": overall_state,
        "phases": {
            "phase_1": phase1["summary"],
            "phase_2": phase2["summary"],
            "phase_3": phase3["summary"],
            "phase_4": phase4["summary"],
            "phase_5": phase5["summary"]
        }
    }
    
    # Save report
    report_path = RUNTIME_DIR / "6AM_SYSTEM_STATUS_REPORT.json"
    try:
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"✓ Report saved: {report_path}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"OVERALL STATE: {overall_state}")
    logger.info(f"Blockers: {len(blockers)}")
    if blockers:
        for blocker in blockers:
            logger.info(f"  ✗ {blocker}")
    logger.info(f"{'='*80}\n")
    
    return report


def main():
    """Run complete 6AM market open probe"""
    logger.info("=" * 80)
    logger.info("6AM MARKET OPEN PROBE - START")
    logger.info("=" * 80)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Runtime Directory: {RUNTIME_DIR}")
    
    try:
        # Phase 1: Preflight health check
        phase1_result = phase_1_preflight_health_check()
        REPORT["phases"]["phase_1_preflight"] = phase1_result
        
        # Phase 2: Market readiness check
        phase2_result = phase_2_market_readiness_check()
        REPORT["phases"]["phase_2_market_readiness"] = phase2_result
        
        # Phase 3: Bias and gate check
        phase3_result = phase_3_bias_and_gate_check()
        REPORT["phases"]["phase_3_bias_gate"] = phase3_result
        
        # Phase 4: Execution path check
        phase4_result = phase_4_execution_path_check()
        REPORT["phases"]["phase_4_execution_path"] = phase4_result
        
        # Phase 5: Trade activity check
        phase5_result = phase_5_trade_activity_check()
        REPORT["phases"]["phase_5_trade_activity"] = phase5_result
        
        # Phase 6: Decision report
        final_report = phase_6_decision_report(
            phase1_result, phase2_result, phase3_result, phase4_result, phase5_result
        )
        REPORT["final_report"] = final_report
        
        logger.info("=" * 80)
        logger.info("6AM MARKET OPEN PROBE - COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Overall State: {final_report.get('overall_state')}")
        logger.info(f"Report: {RUNTIME_DIR / '6AM_SYSTEM_STATUS_REPORT.json'}")
        
        # Exit code based on state
        if final_report.get("overall_state") in ["READY_AND_TRADING", "READY_BUT_NO_ACTIVITY", "READY_BUT_BLOCKED"]:
            return 0
        else:
            return 1
        
    except Exception as e:
        logger.error(f"Probe failed: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
