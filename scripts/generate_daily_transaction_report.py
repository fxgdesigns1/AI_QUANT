#!/usr/bin/env python3
"""
Daily Transaction-Based Performance Report
Generates and stores a daily transaction-based performance report at 23:59 UTC.

TRUTH SOURCE: OANDA transactions endpoint - single source of truth.
Only includes ORDER_FILL transactions with PL field.
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.settings import settings

def fetch_oanda_transactions(account_id: str, since: str) -> List[Dict[str, Any]]:
    """Fetch transactions from OANDA API for a specific account"""
    oanda_api_key = settings.oanda_api_key
    if not oanda_api_key:
        return []
    
    oanda_base_url = os.getenv("OANDA_BASE_URL", "")
    if not oanda_base_url:
        env = settings.oanda_env
        if env == "live":
            oanda_base_url = "https://api-fxtrade.oanda.com"
        else:
            oanda_base_url = "https://api-fxpractice.oanda.com"
    
    headers = {
        "Authorization": f"Bearer {oanda_api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{oanda_base_url}/v3/accounts/{account_id}/transactions"
    params = {
        "count": 5000,
        "since": since
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            print(f"⚠️ Failed to fetch transactions for {account_id}: {response.status_code}")
            return []
        data = response.json()
        transactions = data.get("transactions", [])
        # Filter only ORDER_FILL transactions (these contain PL)
        return [tx for tx in transactions if tx.get("type") == "ORDER_FILL"]
    except Exception as e:
        print(f"⚠️ Error fetching transactions for {account_id}: {e}")
        return []

def generate_daily_report() -> Dict[str, Any]:
    """Generate daily transaction-based performance report for last 24 hours"""
    
    # Calculate 24-hour window (UTC)
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    since = yesterday.isoformat().replace("+00:00", "Z")
    
    account_suffixes = settings.account_suffix_allowlist
    if not account_suffixes:
        return {
            "ok": False,
            "error": "ACCOUNT_SUFFIX_ALLOWLIST not configured",
            "report_date": now.strftime("%Y%m%d"),
            "accounts": []
        }
    
    # Collect data for all accounts
    per_account_data = {}
    per_instrument_data = defaultdict(lambda: {
        "realized_pnl": 0.0,
        "trade_count": 0,
        "win_count": 0,
        "loss_count": 0
    })
    all_stop_sizes = []
    
    for suffix in account_suffixes:
        account_id = f"{settings.account_id_prefix}{suffix}"
        transactions = fetch_oanda_transactions(account_id, since=since)
        
        # Aggregate per account
        account_realized_pnl = 0.0
        account_trade_count = 0
        account_win_count = 0
        account_loss_count = 0
        account_stop_sizes = []
        
        for tx in transactions:
            pl = float(tx.get("pl", 0))
            if pl == 0:
                continue  # Skip unrealized trades
            
            account_realized_pnl += pl
            account_trade_count += 1
            if pl > 0:
                account_win_count += 1
            else:
                account_loss_count += 1
            
            # Per instrument aggregation
            instrument = tx.get("instrument", "UNKNOWN")
            per_instrument_data[instrument]["realized_pnl"] += pl
            per_instrument_data[instrument]["trade_count"] += 1
            if pl > 0:
                per_instrument_data[instrument]["win_count"] += 1
            else:
                per_instrument_data[instrument]["loss_count"] += 1
            
            # Stop size analysis
            entry_price = float(tx.get("price", 0))
            if entry_price > 0:
                stop_loss_on_fill = tx.get("stopLossOnFill", {})
                stop_loss_price = None
                if stop_loss_on_fill:
                    stop_loss_price = float(stop_loss_on_fill.get("price", 0))
                
                if stop_loss_price and stop_loss_price > 0:
                    # Calculate pip size
                    pip_size = 0.0001
                    if "JPY" in instrument:
                        pip_size = 0.01
                    elif "XAU_USD" in instrument or "GOLD" in instrument:
                        pip_size = 0.1
                    
                    stop_size_pips = abs(entry_price - stop_loss_price) / pip_size
                    account_stop_sizes.append(stop_size_pips)
                    all_stop_sizes.append(stop_size_pips)
        
        per_account_data[suffix] = {
            "account_id": account_id,
            "account_suffix": suffix,
            "realized_pnl": round(account_realized_pnl, 2),
            "trade_count": account_trade_count,
            "win_count": account_win_count,
            "loss_count": account_loss_count,
            "win_rate": round(account_win_count / account_trade_count, 4) if account_trade_count > 0 else 0.0,
            "avg_stop_size_pips": round(sum(account_stop_sizes) / len(account_stop_sizes), 1) if account_stop_sizes else 0.0
        }
    
    # Format per-instrument data
    instrument_breakdown = []
    for instrument, data in sorted(per_instrument_data.items()):
        avg_pnl = data["realized_pnl"] / data["trade_count"] if data["trade_count"] > 0 else 0.0
        win_rate = data["win_count"] / data["trade_count"] if data["trade_count"] > 0 else 0.0
        instrument_breakdown.append({
            "instrument": instrument,
            "realized_pnl": round(data["realized_pnl"], 2),
            "trade_count": data["trade_count"],
            "win_count": data["win_count"],
            "loss_count": data["loss_count"],
            "win_rate": round(win_rate, 4),
            "avg_pnl_per_trade": round(avg_pnl, 2)
        })
    
    # Sort by realized_pnl descending
    instrument_breakdown.sort(key=lambda x: x["realized_pnl"], reverse=True)
    
    # Calculate overall stats
    total_realized_pnl = sum(acc["realized_pnl"] for acc in per_account_data.values())
    total_trade_count = sum(acc["trade_count"] for acc in per_account_data.values())
    total_win_count = sum(acc["win_count"] for acc in per_account_data.values())
    total_loss_count = sum(acc["loss_count"] for acc in per_account_data.values())
    avg_stop_size = round(sum(all_stop_sizes) / len(all_stop_sizes), 1) if all_stop_sizes else 0.0
    
    report = {
        "ok": True,
        "report_date": now.strftime("%Y%m%d"),
        "report_timestamp_utc": now.isoformat().replace("+00:00", "Z"),
        "period_start_utc": since,
        "period_end_utc": now.isoformat().replace("+00:00", "Z"),
        "summary": {
            "total_realized_pnl": round(total_realized_pnl, 2),
            "total_trade_count": total_trade_count,
            "total_win_count": total_win_count,
            "total_loss_count": total_loss_count,
            "overall_win_rate": round(total_win_count / total_trade_count, 4) if total_trade_count > 0 else 0.0,
            "avg_stop_size_pips": avg_stop_size
        },
        "per_account": list(per_account_data.values()),
        "per_instrument": instrument_breakdown,
        "verification": {
            "pnl_source": "oanda_transactions_order_fill",
            "pnl_verification": f"Sum of transaction PL fields = {round(total_realized_pnl, 2)}",
            "accounts_analyzed": len(per_account_data),
            "instruments_analyzed": len(instrument_breakdown)
        }
    }
    
    return report

def main():
    """Generate and save daily report"""
    print("=" * 60)
    print("DAILY TRANSACTION PERFORMANCE REPORT")
    print("=" * 60)
    print()
    
    report = generate_daily_report()
    
    if not report.get("ok"):
        print(f"❌ Error generating report: {report.get('error')}")
        sys.exit(1)
    
    # Save report
    report_date = report["report_date"]
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"daily_transaction_performance_{report_date}.json"
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"Report Date: {report_date}")
    print(f"Period: {report['period_start_utc']} to {report['period_end_utc']}")
    print()
    print("Summary:")
    print(f"  Total Realized PnL: ${report['summary']['total_realized_pnl']}")
    print(f"  Total Trades: {report['summary']['total_trade_count']}")
    print(f"  Win Rate: {report['summary']['overall_win_rate'] * 100:.2f}%")
    print(f"  Avg Stop Size: {report['summary']['avg_stop_size_pips']} pips")
    print()
    print("Per Account:")
    for acc in report["per_account"]:
        print(f"  Account {acc['account_suffix']}: ${acc['realized_pnl']} ({acc['trade_count']} trades, {acc['win_rate'] * 100:.2f}% win rate)")
    print()
    print("Top Instruments:")
    for inst in report["per_instrument"][:5]:
        print(f"  {inst['instrument']}: ${inst['realized_pnl']} ({inst['trade_count']} trades)")
    print()
    print(f"✅ Report saved to: {output_file}")
    print()
    print("Verification:")
    print(f"  PnL Source: {report['verification']['pnl_source']}")
    print(f"  PnL Verification: {report['verification']['pnl_verification']}")
    
    return report

if __name__ == "__main__":
    main()
