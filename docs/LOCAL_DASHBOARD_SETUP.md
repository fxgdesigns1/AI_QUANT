# Local OANDA Trade Dashboard - Setup Guide

This guide explains how to set up and run the local-only OANDA trade dashboard that correctly reconstructs trades and computes accurate statistics.

## Overview

The system consists of 4 stages:

1. **Stage 1**: Pull all transactions from OANDA
2. **Stage 2**: Reconstruct trades from transactions
3. **Stage 3**: Compute statistics (win rate, RR, etc.)
4. **Stage 4**: Display in local dashboard

## Prerequisites

- Python 3.8+ with dependencies installed (`pip install -r requirements.txt`)
- Node.js and npm (for React dashboard)
- `.env` file with OANDA credentials configured

## Quick Start

### Step 1: Pull Fresh OANDA Data

```bash
python scripts/local_oanda_trade_pull.py
```

This will:
- Pull ALL transactions for all accounts in `ACCOUNT_SUFFIX_ALLOWLIST`
- Filter for relevant transaction types (ORDER_FILL, TAKE_PROFIT_ORDER, STOP_LOSS_ORDER, etc.)
- Save raw JSON to `data/raw/{account_id}_transactions.json`

### Step 2: Reconstruct Trades

```bash
python -m src.analytics.trade_rebuilder
```

This will:
- Group transactions by tradeID
- Identify entry (first ORDER_FILL) and exit (TP/SL fill)
- Ignore open trades
- Save to `data/processed/trades_flat.json` and `trades_flat.csv`

### Step 3: Compute Statistics

```bash
python -m src.analytics.stats_engine
```

This will:
- Compute overall stats (wins, losses, win rate, RR, expectancy)
- Compute per-pair and per-account breakdowns
- Save to `data/processed/stats.json`

### Step 4: Start Dashboard

**Terminal 1 - Flask API:**
```bash
python dashboard/api_local.py
```

**Terminal 2 - React Frontend:**
```bash
cd frontend/fxg-dashboard
npm run dev
```

Then open http://localhost:5173 (or the port Vite shows) in your browser.

## Verification

### Verify Win Rate Matches OANDA App

1. Run all stages above
2. Compare win rate in dashboard with OANDA app for the same time window
3. Verify: `wins + losses == closed_trades`

### Verify Strategy Discipline Impact

- **Account 002**: Should show reduced trade frequency (ultra strict)
- **Account 003**: Should show reduced duplicate entries (momentum)
- **Account 006**: Should clearly log blocking reasons if no trades (session trader)

## Data Flow

```
OANDA API
    ↓
Stage 1: local_oanda_trade_pull.py
    ↓
data/raw/{account_id}_transactions.json
    ↓
Stage 2: trade_rebuilder.py
    ↓
data/processed/trades_flat.json
    ↓
Stage 3: stats_engine.py
    ↓
data/processed/stats.json
    ↓
Stage 4: Flask API + React Dashboard
    ↓
Browser Display
```

## API Endpoints

- `GET /api/trades` - Get all trades (with optional filters: `account_suffix`, `instrument`, `start_date`, `end_date`)
- `GET /api/stats` - Get overall statistics
- `GET /api/stats/pair` - Get per-pair statistics
- `GET /api/stats/account` - Get per-account statistics
- `GET /api/filters` - Get available filter options
- `GET /api/health` - Health check

## Migration to VM

Once verified locally, the same `trade_rebuilder.py` and `stats_engine.py` can be reused on the VM unchanged. Only the API and dashboard need to be deployed.

## Troubleshooting

### No transactions found
- Check `.env` has correct `OANDA_API_KEY` and `ACCOUNT_SUFFIX_ALLOWLIST`
- Verify accounts exist in OANDA practice environment
- Check network connectivity

### No trades reconstructed
- Verify transactions include ORDER_FILL events
- Check that trades have exit events (TP/SL fills)
- Open trades are intentionally excluded

### Dashboard shows no data
- Ensure Flask API is running on port 5000
- Check that `data/processed/trades_flat.json` exists
- Verify React app is pointing to correct API URL

### Statistics show N/A
- Win rate: No closed trades found
- RR: No trades have TP/SL data
- This is expected behavior when data is missing
