# Performance & Roadmap Dashboard - Design Document

## Overview

This document outlines the design for a new **Performance & Roadmap Dashboard** that integrates:
1. **Strategy Performance Tracking** with filtering and sorting
2. **Weekly Roadmap Display** from Trump DNA framework
3. **Performance vs Roadmap Tracking** (real-time progress monitoring)
4. **Clean, modular UI** (separate from the clunky main dashboard)

## Current System Analysis

### Existing Components Found:

1. **Trade Database** (`src/analytics/trade_database.py`)
   - SQLite database with comprehensive trade records
   - Tables: `trades`, `strategy_metrics`, `daily_snapshots`, `strategy_versions`
   - Already tracks: P&L, win rate, profit factor, drawdown, etc.

2. **Trade Logger** (`src/analytics/trade_logger.py`)
   - Logs all trades to database automatically
   - Tracks entry/exit, P&L calculation
   - Syncs with OANDA positions

3. **Performance Tracker** (`src/core/performance_tracker.py`)
   - Historical performance snapshots
   - Daily summaries
   - Trade history tracking

4. **Analytics Dashboard** (`src/analytics/analytics_dashboard.py`)
   - Standalone dashboard on port 8081
   - Already has API endpoints for strategy metrics
   - Good foundation to extend

5. **Weekly Roadmap System** (`show_weekly_roadmaps.py`)
   - Uses Trump DNA planner
   - Generates weekly targets per strategy/pair
   - Daily breakdowns, entry zones, key events

### Current Dashboard Issues:
- Main dashboard (`advanced_dashboard.py`) is getting clunky
- Too many features in one place
- Roadmap not integrated
- Performance tracking not prominently displayed

## Proposed Solution

### Architecture: Separate Performance Dashboard

**Option 1: Extend Analytics Dashboard (Recommended)**
- Extend existing `analytics_dashboard.py` (port 8081)
- Add roadmap integration
- Add performance vs roadmap tracking
- Keep it separate from main trading dashboard

**Option 2: New Dedicated Dashboard**
- Create new dashboard on port 8082
- Focused on performance + roadmap
- Cleaner, purpose-built

### Recommended: Option 1 (Extend Analytics Dashboard)

## Dashboard Features

### 1. Strategy Performance View

**Features:**
- Filterable/sortable table of all strategies
- Filters:
  - Time period (7 days, 30 days, 90 days, all time)
  - Strategy name
  - Instrument (XAU_USD, EUR_USD, etc.)
  - Sort by: Total P&L, Win Rate, Total Trades, Profit Factor
- Metrics displayed:
  - Strategy name
  - Instrument
  - Total trades
  - Win rate (%)
  - Total P&L ($)
  - Profit factor
  - Max drawdown (%)
  - Status (On Track, Behind, Underperforming)

**Data Source:**
```python
# From trade_database.py
db.get_all_strategy_metrics()
db.get_closed_trades(strategy_id, days=period)
```

### 2. Weekly Roadmap View

**Features:**
- Display current week's roadmap from Trump DNA planner
- Show weekly target per strategy/pair
- Daily breakdown with targets
- Current actual performance vs targets
- Progress indicator (% complete)
- Status indicators (On Track, Behind, No Data)

**Data Source:**
```python
# From show_weekly_roadmaps.py
from src.core.trump_dna_framework import get_trump_dna_planner
planner = get_trump_dna_planner()
planner.weekly_plans  # Dict of WeeklyPlan objects
```

**Weekly Plan Structure:**
- `weekly_target_dollars`: Target for the week
- `daily_targets`: Dict of day -> target amount
- `key_events`: Important events this week
- `entry_zones`: Sniper entry levels
- `support_levels` / `resistance_levels`: Key levels

### 3. Performance vs Roadmap Tracking

**Features:**
- Real-time comparison of actual P&L vs weekly targets
- Daily breakdown showing:
  - Target for each day
  - Actual achieved (if any)
  - Remaining to reach weekly target
  - Daily average needed to hit target
- Visual progress bars
- Status indicators:
  - 🟢 On Track (at or above target pace)
  - 🟡 Behind (below target but recoverable)
  - 🔴 Behind (significantly below target)
  - ⚪ No Data (no trades yet)

**Calculation Logic:**
```python
# For each strategy in weekly roadmap:
weekly_target = planner.weekly_plans[strategy_key].weekly_target_dollars
daily_targets = planner.weekly_plans[strategy_key].daily_targets

# Get actual P&L from trade database
from datetime import datetime, timedelta
week_start = get_week_start()  # Monday of current week
actual_pnl = sum([
    trade['realized_pnl'] 
    for trade in db.get_closed_trades(strategy_id, days=7)
    if trade['entry_time'] >= week_start
])

# Calculate daily actuals
daily_actuals = {}
for day in ['Monday', 'Tuesday', ...]:
    day_start = get_day_start(day)
    day_end = get_day_end(day)
    daily_actuals[day] = sum([
        trade['realized_pnl']
        for trade in trades
        if day_start <= trade['entry_time'] < day_end
    ])

# Calculate progress
progress_pct = (actual_pnl / weekly_target) * 100
remaining = weekly_target - actual_pnl
days_remaining = get_days_remaining_in_week()
daily_avg_needed = remaining / days_remaining if days_remaining > 0 else 0
```

### 4. Quick Stats Bar

**Top-level metrics:**
- Total Weekly Target (sum of all strategies)
- Current Progress (sum of actual P&L)
- Completion % (overall)
- Active Strategies count

### 5. Charts & Visualizations

**Performance Chart:**
- Line chart showing Target vs Actual over the week
- Target line (dashed, blue)
- Actual line (solid, green/red)
- Daily markers
- Hover for details

**Data Source:**
```python
# Daily snapshots from trade_database
snapshots = db.get_daily_snapshots(strategy_id, days=7)
# Or calculate from trades
daily_breakdown = metrics_calc.calculate_daily_breakdown(trades, days=7)
```

## Implementation Plan

### Phase 1: Backend API Endpoints

**New endpoints in `analytics_dashboard.py`:**

1. **`/api/performance/strategies`** (Enhanced)
   - Add filtering parameters
   - Add sorting options
   - Return formatted data for table

2. **`/api/roadmap/current-week`** (New)
   - Get current week's roadmap from Trump DNA planner
   - Format for dashboard display

3. **`/api/roadmap/performance-vs-target`** (New)
   - Get weekly targets
   - Get actual P&L from trade database
   - Calculate progress metrics
   - Return comparison data

4. **`/api/roadmap/daily-breakdown`** (New)
   - Get daily targets vs actuals
   - Calculate remaining needs
   - Return daily breakdown array

### Phase 2: Frontend Template

**New template:** `src/templates/analytics/performance_roadmap.html`

**Structure:**
- Sidebar navigation
- Quick stats bar
- Tabs: Performance | Roadmap | Performance vs Roadmap | Trade History
- Strategy performance table with filters
- Weekly roadmap section
- Performance charts

**JavaScript:**
- Fetch data from API endpoints
- Render charts (Chart.js or similar)
- Real-time updates (polling or WebSocket)
- Filter/sort functionality

### Phase 3: Integration

**Connect to existing systems:**
1. Trade database (already connected)
2. Trump DNA planner (import and use)
3. Performance tracker (optional enhancement)

**Data Flow:**
```
Trump DNA Planner → Weekly Targets
     ↓
Trade Database → Actual P&L
     ↓
Performance Calculator → Metrics
     ↓
Dashboard API → Formatted Data
     ↓
Frontend → Display
```

## API Endpoints Specification

### 1. Get Strategy Performance (with filters)

**Endpoint:** `GET /api/performance/strategies`

**Query Parameters:**
- `period` (optional): 7, 30, 90, or 'all' (default: 30)
- `strategy_id` (optional): Filter by strategy
- `instrument` (optional): Filter by instrument
- `sort_by` (optional): 'pnl', 'win_rate', 'trades', 'profit_factor' (default: 'pnl')
- `sort_order` (optional): 'asc' or 'desc' (default: 'desc')

**Response:**
```json
{
  "success": true,
  "strategies": [
    {
      "strategy_id": "champion_75wr",
      "strategy_name": "Champion 75WR",
      "instrument": "XAU_USD",
      "total_trades": 42,
      "win_rate": 76.2,
      "total_pnl": 2450.0,
      "profit_factor": 2.34,
      "max_drawdown": -2.1,
      "status": "on_track"
    }
  ],
  "total_count": 8,
  "period_days": 30
}
```

### 2. Get Current Week Roadmap

**Endpoint:** `GET /api/roadmap/current-week`

**Response:**
```json
{
  "success": true,
  "week_start": "2025-10-21",
  "week_end": "2025-10-27",
  "strategies": [
    {
      "strategy_id": "champion_75wr",
      "pair": "XAU_USD",
      "strategy_name": "Champion 75WR",
      "weekly_target": 3000.0,
      "daily_targets": {
        "Monday": 600,
        "Tuesday": 500,
        ...
      },
      "key_events": [...],
      "entry_zones": [...],
      "support_levels": [...],
      "resistance_levels": [...]
    }
  ],
  "total_weekly_target": 15000.0
}
```

### 3. Get Performance vs Roadmap

**Endpoint:** `GET /api/roadmap/performance-vs-target`

**Query Parameters:**
- `strategy_id` (optional): Filter by strategy

**Response:**
```json
{
  "success": true,
  "week_start": "2025-10-21",
  "week_end": "2025-10-27",
  "strategies": [
    {
      "strategy_id": "champion_75wr",
      "pair": "XAU_USD",
      "weekly_target": 3000.0,
      "actual_pnl": 2450.0,
      "progress_pct": 81.7,
      "remaining": 550.0,
      "days_remaining": 2,
      "daily_avg_needed": 275.0,
      "status": "on_track",
      "daily_breakdown": [
        {
          "day": "Monday",
          "target": 600,
          "actual": 520,
          "status": "below"
        },
        ...
      ]
    }
  ],
  "overall": {
    "total_target": 15000.0,
    "total_actual": 8450.0,
    "progress_pct": 56.3,
    "remaining": 6550.0
  }
}
```

## File Structure

```
google-cloud-trading-system/
├── src/
│   ├── analytics/
│   │   ├── analytics_dashboard.py  # Extend this
│   │   ├── trade_database.py       # Already exists
│   │   ├── trade_logger.py         # Already exists
│   │   └── ...
│   ├── core/
│   │   ├── trump_dna_framework.py # Roadmap source
│   │   └── ...
│   └── templates/
│       └── analytics/
│           ├── performance_roadmap.html  # New template
│           └── ...
└── dashboard_mockup_performance_roadmap.html  # Design mockup
```

## Benefits

1. **Separation of Concerns**
   - Main dashboard stays for live trading
   - Performance dashboard for analysis
   - Less clunky, more focused

2. **Real-time Tracking**
   - See progress against roadmap in real-time
   - Identify underperforming strategies early
   - Adjust daily targets dynamically

3. **Better Decision Making**
   - Filter and sort strategies by performance
   - Compare actual vs planned
   - Historical context with daily snapshots

4. **Extensible**
   - Easy to add new metrics
   - Can integrate with other analytics
   - Modular design

## Next Steps

1. **Review mockup** (`dashboard_mockup_performance_roadmap.html`)
2. **Approve design** and any modifications
3. **Implement backend APIs** (extend analytics_dashboard.py)
4. **Create frontend template** (performance_roadmap.html)
5. **Test integration** with existing systems
6. **Deploy** to port 8081 (analytics dashboard)

## Notes

- The analytics dashboard already exists on port 8081
- Trade database is already logging all trades
- Trump DNA planner generates weekly roadmaps
- Need to connect them together
- Performance vs roadmap calculation needs to match week boundaries correctly
