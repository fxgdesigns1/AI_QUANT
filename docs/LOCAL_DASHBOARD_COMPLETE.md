# Local OANDA Trade Dashboard - Implementation Complete

## ✅ Implementation Status

All 4 stages have been implemented and are ready for use:

### Stage 1: OANDA Transaction Pull ✅
**File**: `scripts/local_oanda_trade_pull.py`

- Pulls ALL transactions from OANDA for all accounts in `ACCOUNT_SUFFIX_ALLOWLIST`
- Filters for relevant transaction types: `ORDER_FILL`, `TAKE_PROFIT_ORDER`, `STOP_LOSS_ORDER`, `TAKE_PROFIT_ORDER_FILLED`, `STOP_LOSS_ORDER_FILLED`, `TRADE_CLOSE`
- Handles pagination automatically
- Saves raw JSON to `data/raw/{account_id}_transactions.json`

### Stage 2: Trade Reconstruction ✅
**File**: `src/analytics/trade_rebuilder.py`

- Groups transactions by `tradeID`
- Identifies entry via first `ORDER_FILL`
- Identifies exit via TP/SL fill or `TRADE_CLOSE`
- Ignores open trades (only closed trades included)
- Computes realized P&L only from closed trades
- Extracts TP/SL levels when available
- Calculates risk-reward ratio
- Outputs: `data/processed/trades_flat.json` and `trades_flat.csv`

### Stage 3: Statistics Engine ✅
**File**: `src/analytics/stats_engine.py`

**Metrics Computed:**
- `trades`, `wins`, `losses`, `breakeven`
- `win_rate` (only if closed_trades > 0)
- `avg_win`, `avg_loss`
- `rr_per_trade` (only when TP/SL data available)
- `expectancy` = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
- `per_pair_breakdown` - Statistics grouped by instrument
- `per_account_breakdown` - Statistics grouped by account

**Guarantees:**
- ✅ No win rate computed if closed_trades == 0
- ✅ RR computed only when SL and TP are known
- ✅ Explicit logging when stats are undefined
- ✅ Outputs: `data/processed/stats.json`

### Stage 4: Local Dashboard ✅
**Files**: 
- `dashboard/api_local.py` - Flask API
- `frontend/fxg-dashboard/src/components/LocalTradeDashboard.jsx` - React component
- `frontend/fxg-dashboard/src/LocalDashboardApp.jsx` - Entry point

**API Endpoints:**
- `GET /api/trades` - Get all trades (filters: `account_suffix`, `instrument`, `start_date`, `end_date`)
- `GET /api/stats` - Get overall statistics
- `GET /api/stats/pair` - Get per-pair statistics
- `GET /api/stats/account` - Get per-account statistics
- `GET /api/filters` - Get available filter options
- `GET /api/health` - Health check

**Dashboard Features:**
- ✅ Trade journal table with all trade details
- ✅ Account filter dropdown
- ✅ Pair/instrument filter dropdown
- ✅ Date range filter (start_date, end_date)
- ✅ Win rate, wins, losses, RR display
- ✅ Closed vs open trade separation (only closed shown)
- ✅ Real-time filtering
- ✅ Color-coded results (green for wins, red for losses)

## 📁 Directory Structure

```
data/
├── raw/
│   └── {account_id}_transactions.json  # Stage 1 output
└── processed/
    ├── trades_flat.json                # Stage 2 output
    ├── trades_flat.csv                 # Stage 2 output
    └── stats.json                      # Stage 3 output
```

## 🚀 Quick Start

### Option 1: Use the Quick Start Script

```bash
./scripts/run_local_dashboard.sh
```

This runs Stages 1-3 automatically. Then start the dashboard:

**Terminal 1:**
```bash
python dashboard/api_local.py
```

**Terminal 2:**
```bash
cd frontend/fxg-dashboard
npm run dev
```

### Option 2: Manual Steps

1. **Pull transactions:**
   ```bash
   python scripts/local_oanda_trade_pull.py
   ```

2. **Reconstruct trades:**
   ```bash
   python -m src.analytics.trade_rebuilder
   ```

3. **Compute statistics:**
   ```bash
   python -m src.analytics.stats_engine
   ```

4. **Start Flask API:**
   ```bash
   python dashboard/api_local.py
   ```

5. **Start React dashboard:**
   ```bash
   cd frontend/fxg-dashboard
   # Temporarily update src/main.jsx to import LocalDashboardApp instead of App
   npm run dev
   ```

## 🔍 Verification Checklist

### Data Verification
- [ ] `data/raw/` contains transaction JSON files for all accounts
- [ ] `data/processed/trades_flat.json` exists and contains closed trades
- [ ] `data/processed/stats.json` exists and contains statistics

### Statistics Verification
- [ ] Win rate matches OANDA app for same time window
- [ ] `wins + losses == closed_trades` (for overall stats)
- [ ] Account 002 shows reduced trade frequency (ultra strict discipline)
- [ ] Account 003 shows reduced duplicate entries (momentum discipline)
- [ ] Account 006 clearly shows blocking reasons if no trades (session trader)

### Dashboard Verification
- [ ] Flask API responds on http://localhost:5000
- [ ] React dashboard loads on http://localhost:5173 (or Vite port)
- [ ] Filters work correctly (account, instrument, date range)
- [ ] Trade journal displays all trades
- [ ] Statistics display correctly
- [ ] No console errors

## 🔄 Migration to VM

Once verified locally, the same code can be reused on the VM:

**Reusable (no changes needed):**
- ✅ `src/analytics/trade_rebuilder.py`
- ✅ `src/analytics/stats_engine.py`

**Needs deployment:**
- `dashboard/api_local.py` → Deploy as Flask service
- `frontend/fxg-dashboard/` → Build and serve static files

**Migration Rule:**
- No reimplementation
- No duplicate dashboards
- No parallel logic
- Single source of truth: processed trade data

## 📊 Data Flow

```
OANDA API (read-only)
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

## 🛠️ Dependencies

**Python:**
- `flask==3.0.0`
- `flask-cors==4.0.0` (added to requirements.txt)
- `python-dotenv>=1.0`
- `requests==2.31.0`

**Node.js:**
- React 19.2.0
- Vite 7.2.4
- Tailwind CSS 4.1.18

## 📝 Notes

1. **Single Source of Truth**: Dashboard only consumes processed trade data (`trades_flat.json`), never raw OANDA responses
2. **Open Trades**: Intentionally excluded from win-rate calculations
3. **Missing Data**: Statistics show `N/A` when data is unavailable (expected behavior)
4. **Account 006**: Always included in allowlist (session trader)
5. **Pagination**: Stage 1 handles OANDA API pagination automatically

## 🐛 Troubleshooting

### No transactions found
- Verify `.env` has correct `OANDA_API_KEY`
- Check `ACCOUNT_SUFFIX_ALLOWLIST` includes desired accounts
- Verify accounts exist in OANDA practice environment

### No trades reconstructed
- Check transactions include `ORDER_FILL` events
- Verify trades have exit events (TP/SL fills)
- Open trades are intentionally excluded

### Dashboard shows no data
- Ensure Flask API is running on port 5000
- Check `data/processed/trades_flat.json` exists
- Verify React app points to correct API URL (`http://localhost:5000`)

### Statistics show N/A
- **Win rate N/A**: No closed trades found (expected)
- **RR N/A**: No trades have TP/SL data (expected)
- This is correct behavior when data is missing

## ✅ Final Status

**PASS** - All stages implemented and ready for verification.

**Next Steps:**
1. Run Stage 1-3 to pull and process data
2. Verify statistics match OANDA app
3. Start dashboard and verify functionality
4. Once verified locally, migrate to VM using same code
