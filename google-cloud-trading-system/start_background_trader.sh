#!/bin/bash
# Start the aggressive trader in background on cloud

cd "$(dirname "$0")"
nohup python3 continuous_aggressive_trader.py > trader.log 2>&1 &
echo $! > trader.pid
echo "Trader started with PID: $(cat trader.pid)"
