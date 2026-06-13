#!/usr/bin/env python3
"""
VM Dashboard API (Flask)
Serves trade data and stats to the VM React frontend.

TRUTH SOURCE:
- STRICTLY OANDA Authoritative Data (data/processed/trades_flat.json)
- Stats computed DYNAMICALLY per time window (no pre-computed lifetime stats)

Rules:
- ALL stats requests MUST specify start_date and end_date
- NO lifetime stats served
"""

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Logging: persist to logs/vm_dashboard_api.log
LOGS_DIR = PROJECT_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
VM_API_LOG = LOGS_DIR / 'vm_dashboard_api.log'
_fh = logging.FileHandler(VM_API_LOG, encoding='utf-8')
_fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
_logger = logging.getLogger('vm_dashboard_api')
_logger.setLevel(logging.INFO)
_logger.addHandler(_fh)
_logger.propagate = False

def _log(msg: str, level: str = "INFO"):
    getattr(_logger, level.lower())(msg)
    print(msg)

try:
    from src.analytics.stats_engine import compute_trade_stats
except ImportError as e:
    _log(f"Failed to import stats_engine: {e}", "ERROR")
    traceback.print_exc()
    sys.exit(1)

DATA_DIR = PROJECT_ROOT / 'data'
TRADES_FILE = DATA_DIR / 'processed' / 'trades_flat.json'

app = Flask(__name__)
CORS(app)

def load_vm_trades():
    """Load normalized trades from VM authoritative file."""
    if not TRADES_FILE.exists():
        return [], "LOW", "none"
        
    try:
        with open(TRADES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('trades', []), data.get('data_confidence', 'HIGH'), data.get('source', 'vm_oanda')
    except Exception as e:
        print(f"Error reading VM trades: {e}")
        return [], "LOW", "error"

def filter_trades(trades, start_date_str, end_date_str, account_id=None, instrument=None, strategy=None):
    """
    Filter trades by date range (inclusive) and other optional filters.
    Dates strings should be YYYY-MM-DD.
    """
    filtered = []
    
    # Parse dates
    try:
        start_dt = datetime.fromisoformat(start_date_str).replace(tzinfo=None)
        # End date is inclusive, so we add time 23:59:59 if it's just a date
        if 'T' in end_date_str:
             end_dt = datetime.fromisoformat(end_date_str).replace(tzinfo=None)
        else:
             end_dt = datetime.fromisoformat(end_date_str).replace(hour=23, minute=59, second=59, tzinfo=None)
    except Exception as e:
        raise ValueError(f"Invalid date format: {e}")

    for t in trades:
        # Check Account
        if account_id and t.get('account_id') != account_id:
            continue
            
        # Check Instrument
        if instrument and t.get('instrument') != instrument:
            continue

        # Check Strategy
        if strategy and t.get('strategy') != strategy:
            continue
            
        # Check Date Range (using exit_time for stats)
        # exit_time is ISO string like "2023-10-01T12:00:00.000000Z"
        exit_time_str = t.get('exit_time')
        if not exit_time_str:
            continue
            
        try:
            # Simple ISO parsing (ignoring Z for comparison if start_dt is naive)
            # Better to be robust
            exit_dt = datetime.fromisoformat(exit_time_str.replace('Z', '')).replace(tzinfo=None)
            
            if start_dt <= exit_dt <= end_dt:
                filtered.append(t)
        except:
            continue
            
    return filtered

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "service": "vm_dashboard_api"})

@app.route('/api/health/deep')
def deep_health():
    """
    Deep health check for VM readiness.
    Asserts:
    - trades_flat.json exists
    - trade_count > 0
    - timestamp of trades_flat.json < 24h old
    - /api/vm/journal/trades returns HTTP 200 (simulated)
    - route /api/vm/journal/trades is registered
    """
    checks = {
        "trades_file_exists": False,
        "trade_count_positive": False,
        "data_freshness_pass": False,
        "journal_route_registered": False,
        "journal_route_reachable": False
    }
    
    # 1. trades_flat.json exists
    if TRADES_FILE.exists():
        checks["trades_file_exists"] = True
        
        try:
            # 2. trade_count > 0
            stat = TRADES_FILE.stat()
            with open(TRADES_FILE, 'r') as f:
                data = json.load(f)
            trades = data.get('trades', [])
            if len(trades) > 0:
                checks["trade_count_positive"] = True
                
            # 3. timestamp < 24h old
            # Check file modification time
            mtime = stat.st_mtime
            if (datetime.now().timestamp() - mtime) < 86400:
                checks["data_freshness_pass"] = True
        except Exception as e:
            _log(f"Deep health check error reading file: {e}", "ERROR")

    # 4. route /api/vm/journal/trades is registered
    for rule in app.url_map.iter_rules():
        if rule.rule == '/api/vm/journal/trades':
            checks["journal_route_registered"] = True
            break
            
    # 5. /api/vm/journal/trades returns HTTP 200
    try:
        with app.test_client() as client:
            # Use a wide range to ensure we don't fail on empty results (though filtered might be empty, 200 is expected)
            # The endpoint returns 200 even if empty, as long as params are valid.
            resp = client.get('/api/vm/journal/trades?start_date=2020-01-01&end_date=2099-12-31')
            if resp.status_code == 200:
                checks["journal_route_reachable"] = True
            else:
                _log(f"Deep health probe failed status: {resp.status_code}, body: {resp.get_data(as_text=True)}", "ERROR")
    except Exception as e:
         _log(f"Deep health probe exception: {e}", "ERROR")

    all_passed = all(checks.values())
    status_code = 200 if all_passed else 500
    
    return jsonify({
        "success": all_passed,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), status_code


@app.route('/api/vm/journal/trades', methods=['GET'])
def get_journal_trades():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_id = request.args.get('account_id')
    instrument = request.args.get('instrument')
    strategy = request.args.get('strategy')
    
    if not start_date or not end_date:
        return jsonify({
            "error": "Date range required (start_date, end_date)",
            "code": "MISSING_DATE_RANGE"
        }), 400
        
    all_trades, confidence, source = load_vm_trades()
    
    try:
        filtered = filter_trades(all_trades, start_date, end_date, account_id, instrument, strategy)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    # Compute stats dynamically on filtered data
    stats = compute_trade_stats(filtered)
    
    return jsonify({
        "success": True,
        "count": len(filtered),
        "trades": filtered,
        "stats": stats,
        "meta": {
            "source": source,
            "confidence": confidence,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "account_id": account_id,
                "instrument": instrument,
                "strategy": strategy
            }
        }
    })

@app.route('/api/vm/trades', methods=['GET'])
def get_vm_trades():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_id = request.args.get('account_id')
    instrument = request.args.get('instrument')
    strategy = request.args.get('strategy')
    
    if not start_date or not end_date:
        return jsonify({
            "error": "Date range required (start_date, end_date)",
            "code": "MISSING_DATE_RANGE"
        }), 400
        
    all_trades, confidence, source = load_vm_trades()
    
    try:
        filtered = filter_trades(all_trades, start_date, end_date, account_id, instrument, strategy)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    return jsonify({
        "success": True,
        "count": len(filtered),
        "trades": filtered,
        "meta": {
            "source": source,
            "confidence": confidence,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "account_id": account_id,
                "instrument": instrument,
                "strategy": strategy
            }
        }
    })

@app.route('/api/vm/stats', methods=['GET'])
def get_vm_stats():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_id = request.args.get('account_id')
    instrument = request.args.get('instrument')
    strategy = request.args.get('strategy')
    
    if not start_date or not end_date:
        return jsonify({
            "error": "Date range required (start_date, end_date)",
            "code": "MISSING_DATE_RANGE"
        }), 400
        
    all_trades, confidence, source = load_vm_trades()
    
    try:
        filtered = filter_trades(all_trades, start_date, end_date, account_id, instrument, strategy)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    # Compute stats dynamically
    stats = compute_trade_stats(filtered)
    
    return jsonify({
        "success": True,
        "stats": stats,
        "meta": {
            "source": source,
            "confidence": confidence,
            "trade_count_in_window": len(filtered),
            "filters": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    })

# --- Startup: verify trades_flat.json, log routes, abort if no data ---
def _vm_api_startup():
    _log("VM API BOOT STARTED")
    _log(f"TRADES_FILE={TRADES_FILE}")
    for r in sorted(r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/')):
        _log(f"Registered route {r}")
    if not TRADES_FILE.exists():
        _log(f"trades_flat.json NOT FOUND at {TRADES_FILE}", "ERROR")
        sys.exit(1)
    try:
        stat = TRADES_FILE.stat()
        with open(TRADES_FILE, 'r') as f:
            data = json.load(f)
        trades_list = data.get('trades', [])
        trade_count = len(trades_list)
        ts = data.get('timestamp', 'unknown')
        _log(f"trades_flat.json exists, mtime={datetime.fromtimestamp(stat.st_mtime).isoformat()}, timestamp={ts}, trade_count={trade_count}")
        if trade_count == 0:
            _log("ABORT: trade_count == 0 (expected ~10017)", "ERROR")
            sys.exit(1)
        _log(f"Loaded trades_flat.json with trade_count={trade_count}")
    except Exception as e:
        _log(f"Error loading trades_flat.json: {e}", "ERROR")
        traceback.print_exc()
        sys.exit(1)

_vm_api_startup()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
