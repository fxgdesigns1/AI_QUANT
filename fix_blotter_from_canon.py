#!/usr/bin/env python3
"""
Blotter canonicalization utility
Reads the canonical live_trade_blotter_trades.json and rewrites per-account blotter CSVs
to ensure a single source of truth for blotter data.
"""
import os
import json
import csv
from pathlib import Path

def rewrite_blotter_from_json(data_dir: Path, json_filename: str = "live_trade_blotter_trades.json") -> None:
    json_path = data_dir / json_filename
    if not json_path.exists():
        print(f"Canon blotter JSON not found at {json_path}")
        return
    try:
        with json_path.open("r", encoding="utf-8") as f:
            all_trades = json.load(f)
    except Exception as exc:
        print(f"Failed to read JSON {json_path}: {exc}")
        return

    # Group by account
    trades_by_account = {}
    for t in all_trades:
        acc = str(t.get("account_id", "unknown"))
        trades_by_account.setdefault(acc, []).append(t)

    # Overwrite per-account blotters
    for account_id, trades in trades_by_account.items():
        csv_path = data_dir / f"blotter_{account_id}.csv"
        fieldnames = [
            "account_id", "instrument", "side", "units", "entry_ticket", "entry_timestamp",
            "entry_price", "stop_loss", "take_profit", "exit_ticket", "exit_timestamp",
            "exit_price", "close_type", "price_change", "pnl", "pnl_currency", "holding_minutes"
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
            writer.writeheader()
            for tr in trades:
                row = {k: tr.get(k, "") for k in fieldnames}
                writer.writerow(row)
        print(f"Wrote {len(trades)} trades to {csv_path}")

def main():
    # Expect data in the current working directory or a likely data folder
    # Try common locations
    possible_dirs = [
        Path.cwd(),
        Path("/opt/quant_system_clean/google-cloud-trading-system/data"),
        Path("/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/data"),
        Path("./data"),
    ]
    data_dir = None
    for d in possible_dirs:
        if d.exists():
            data_dir = d
            break
    if not data_dir:
        print("Could not locate data directory for blotters.")
        return
    rewrite_blotter_from_json(data_dir)

if __name__ == "__main__":
    main()
































