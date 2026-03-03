#!/usr/bin/env python3
"""
Generate a test signal for the MT5 Bridge.
Supports --fanout (write to all enabled fanout targets) and --signal-file override.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from observability.bridge_signal_router import emit_signal


def generate_test_signal(bridge_account, symbol, side, machine=False, fanout=False, signal_file=None):
    if not machine:
        mode = "fanout" if fanout else f"single ({bridge_account})"
        print(f"Generating test signal ({mode})...")

    signal_id = emit_signal(
        strategy="TEST_STRATEGY",
        symbol=symbol,
        side=side,
        units=1000,
        confidence=0.99,
        execution_allowed=True,
        bridge_account=bridge_account or "prop_02",
        signal_file_override=signal_file,
        fanout=fanout,
        meta={"note": "Manual test signal for bridge verification"},
    )

    if signal_id:
        if machine:
            print(signal_id)
        else:
            print(f"Successfully emitted signal: {signal_id}")
            if fanout:
                print("Check logs/signals_prop_02.jsonl, logs/signals_citytraders.jsonl (and MT5 terminals).")
            else:
                print("Check logs/signals.jsonl and your MT5 terminal.")
        return signal_id
    else:
        if not machine:
            print("Failed to emit signal.")
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a test signal for the MT5 Bridge.")
    parser.add_argument(
        "--bridge-account",
        type=str,
        default="prop_02",
        help="Target bridge account ID (used when not --fanout)",
    )
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Symbol to trade")
    parser.add_argument("--side", type=str, default="BUY", choices=["BUY", "SELL"], help="Trade side")
    parser.add_argument("--machine", action="store_true", help="Print only signal_id on success (for scripting)")
    parser.add_argument(
        "--fanout",
        action="store_true",
        help="Write to all enabled fanout targets' signal files",
    )
    parser.add_argument(
        "--signal-file",
        type=str,
        default=None,
        help="Override: write only to this file path (for testing)",
    )

    args = parser.parse_args()

    generate_test_signal(
        args.bridge_account,
        args.symbol,
        args.side,
        machine=args.machine,
        fanout=args.fanout,
        signal_file=args.signal_file,
    )
