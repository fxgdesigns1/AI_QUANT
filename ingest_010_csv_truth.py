#!/usr/bin/env python3
"""
Ingest the full truth for account 010 from an external CSV dump and
overwrite the canonical JSON blotter and per-account blotters to enforce
one truth and remove duplicate/conflicting data sources.
Usage:
  python3 ingest_010_csv_truth.py --csv "/path/to/transactions_101-004-30719775-010 (2).csv"
"""
import csv
import json
import os
from pathlib import Path
from typing import List, Dict

CANON_JSON = "live_trade_blotter_trades.json"
ACCOUNT_ID = "101-004-30719775-010"

def read_external_truth(csv_path: str) -> List[Dict]:
    trades: List[Dict] = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Normalize header keys (strip surrounding quotes if present)
        for row in reader:
            ttype = (row.get("TRANSACTION TYPE") or row.get("TRANSACTION_TYPE") or "").strip()
            if not ttype:
                continue
            if ttype.upper() != "ORDER_FILL":
                # Only consider fills as a conservative entry; other types can be handled later
                continue

            instrument = (row.get("INSTRUMENT") or "").strip()
            direction = (row.get("DIRECTION") or row.get("DIRECCION") or "").strip()
            side = "BUY" if direction.lower() == "buy" else "SELL"
            units_raw = row.get("UNITS") or "0"
            try:
                units = float(units_raw)
            except:
                units = 0.0
            entry_timestamp = (row.get("TRANSACTION DATE") or row.get("TRANSACTION_DATE") or "")
            entry_ticket = row.get("TICKET") or ""
            price_str = (row.get("PRICE") or "")
            try:
                entry_price = float(price_str) if price_str != "" else 0.0
            except:
                entry_price = 0.0
            stop_loss = row.get("STOP LOSS") or ""
            take_profit = row.get("TAKE PROFIT") or ""

            trade = {
                "account_id": ACCOUNT_ID,
                "instrument": instrument,
                "side": side,
                "units": units,
                "entry_ticket": entry_ticket,
                "entry_timestamp": entry_timestamp,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "exit_ticket": "",
                "exit_timestamp": "",
                "exit_price": "",
                "close_type": "",
                "price_change": "",
                "pnl": 0.0,
                "pnl_currency": "USD",
                "holding_minutes": ""
            }
            trades.append(trade)
    return trades

def write_blotter_csv_for_account(data_dir: Path, account_id: str, trades: List[Dict]) -> None:
    fieldnames = [
        "account_id","instrument","side","units","entry_ticket","entry_timestamp","entry_price",
        "stop_loss","take_profit","exit_ticket","exit_timestamp","exit_price","close_type",
        "price_change","pnl","pnl_currency","holding_minutes"
    ]
    csv_path = data_dir / f"blotter_{account_id}.csv"
    os.makedirs(data_dir, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in trades:
            row = {k: t.get(k, "") for k in fieldnames}
            writer.writerow(row)
    print(f"Wrote {len(trades)} trades to {csv_path}")

def read_existing_canon(json_path: Path) -> List[Dict]:
    if not json_path.exists():
        return []
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("trades", [])
    except Exception:
        return []

def write_canon_json(json_path: Path, trades: List[Dict]) -> None:
    payload = {"trades": trades}
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(trades)} trades to canonical blotter JSON: {json_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to external 010 CSV dump")
    parser.add_argument("--data-dir", default="google-cloud-trading-system/data", help="Directory to write blotter CSVs and JSON")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    data_dir = Path(args.data_dir)

    external_trades = read_external_truth(str(csv_path))
    if not external_trades:
        print("No ORDER_FILL entries found in external CSV.")
        return

    # Update per-account blotter for 010
    write_blotter_csv_for_account(data_dir, ACCOUNT_ID, external_trades)

    # Update canonical JSON blotter by replacing trades for account 010
    canon_path = data_dir / CANON_JSON
    existing = read_existing_canon(canon_path)
    # Remove any existing trades for this account
    remaining = [t for t in existing if str(t.get("account_id")) != ACCOUNT_ID]
    new_entries = [
        {
            "account_id": t["account_id"],
            "instrument": t["instrument"],
            "side": t["side"],
            "units": t["units"],
            "entry_ticket": t["entry_ticket"],
            "entry_timestamp": t["entry_timestamp"],
            "entry_price": t["entry_price"],
            "stop_loss": t["stop_loss"],
            "take_profit": t["take_profit"],
            "exit_ticket": t["exit_ticket"],
            "exit_timestamp": t["exit_timestamp"],
            "exit_price": t["exit_price"],
            "close_type": t["close_type"],
            "price_change": t["price_change"],
            "pnl": t.get("pnl", 0.0),
            "pnl_currency": t.get("pnl_currency", "USD"),
            "holding_minutes": t.get("holding_minutes", "")
        }
        for t in external_trades
    ]
    all_trades = remaining + new_entries
    write_canon_json(canon_path, {"trades": all_trades})

if __name__ == "__main__":
    main()
































