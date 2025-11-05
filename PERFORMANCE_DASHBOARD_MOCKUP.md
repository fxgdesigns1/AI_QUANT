# 📊 Performance & Roadmap Dashboard - Mockup Design

## Overview
This document outlines a **dedicated Performance & Roadmap Dashboard** that separates performance tracking from the main trading dashboard, making it easier to analyze strategy performance, filter trades, and track progress against weekly roadmaps.

---

## 🎯 Dashboard Architecture

### **Option 1: Separate Dashboard (Recommended)**
**URL:** `/performance` or `/analytics`  
**Port:** 8081 (separate from main dashboard on 8080)

**Benefits:**
- Clean separation of concerns
- Faster loading (lighter than main dashboard)
- Dedicated focus on analytics
- Can run independently

### **Option 2: Integrated Tab**
**URL:** Same as main dashboard, new tab section

**Benefits:**
- Single entry point
- Shared authentication
- Unified navigation

---

## 📐 Layout Design

```
┌─────────────────────────────────────────────────────────────────────┐
│  📊 PERFORMANCE & ROADMAP DASHBOARD                    [Refresh]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  📅 WEEKLY ROADMAP & PROGRESS                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ Week: Oct 28 - Nov 3, 2025    Day 3 of 7 (Wednesday)    │ │  │
│  │  │                                                          │ │  │
│  │  │ Weekly Target: $3,500    │  Current: $1,250  │  On Track │ │  │
│  │  │ ████████░░░░░░░░░░░░░░░░ 35.7%                          │ │  │
│  │  │ Expected: $1,500          │  Gap: -$250                 │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 📊 DAILY BREAKDOWN                                       │ │  │
│  │  │                                                          │ │  │
│  │  │ Mon  │  Target: $500  │  Actual: $450  │  ✅ 90%       │ │  │
│  │  │ Tue  │  Target: $600  │  Actual: $300  │  ⚠️  50%     │ │  │
│  │  │ Wed  │  Target: $650  │  Actual: $500  │  🔄 77%       │ │  │
│  │  │ Thu  │  Target: $700  │  Actual: $0    │  ⏳ Pending   │ │  │
│  │  │ Fri  │  Target: $550  │  Actual: $0    │  ⏳ Pending   │ │  │
│  │  │ Sat  │  Target: $500  │  Actual: $0    │  ⏳ Pending   │ │  │
│  │  │ Sun  │  Target: $0    │  Actual: $0    │  ⏳ Closed    │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 🎯 STRATEGY ROADMAPS (This Week)                         │ │  │
│  │  │                                                          │ │  │
│  │  │ [EUR_USD - Ultra Strict V2]                            │ │  │
│  │  │   Target: $800  │  Progress: $420  │  ✅ 52.5%         │ │  │
│  │  │   Entry Zones: 1.0850, 1.0820, 1.0800                  │ │  │
│  │  │                                                          │ │  │
│  │  │ [XAU_USD - Gold High Return]                            │ │  │
│  │  │   Target: $1,200 │  Progress: $380  │  ⚠️  31.7%      │ │  │
│  │  │   Entry Zones: $2650, $2640, $2630                       │ │  │
│  │  │                                                          │ │  │
│  │  │ [GBP_USD - Champion 75WR]                                │ │  │
│  │  │   Target: $900  │  Progress: $450  │  ✅ 50.0%         │ │  │
│  │  │   Entry Zones: 1.2650, 1.2620, 1.2600                   │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  📈 STRATEGY PERFORMANCE TRACKER                            │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 🔍 FILTERS                                               │ │  │
│  │  │                                                          │ │  │
│  │  │ Strategy: [All ▼]  │  Date Range: [Last 7 Days ▼]       │ │  │
│  │  │ Instrument: [All ▼] │  Status: [All ▼]                  │ │  │
│  │  │                                                          │ │  │
│  │  │ Quick Filters: [Today] [This Week] [This Month] [All] │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 📊 PERFORMANCE SUMMARY (Filtered)                       │ │  │
│  │  │                                                          │ │  │
│  │  │ Total Trades: 47   │  Win Rate: 72.3%  │  Profit: $1,250 │ │  │
│  │  │ Profit Factor: 2.1 │  Max DD: -$180    │  Sharpe: 1.8     │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 📋 STRATEGY BREAKDOWN (Table)                           │ │  │
│  │  │                                                          │ │  │
│  │  │ Strategy          │ Trades │ Win% │ P&L    │ PF │ Status │ │  │
│  │  │ ────────────────────────────────────────────────────── │ │  │
│  │  │ Ultra Strict V2   │   12   │ 75%  │ $420   │ 2.3│ ✅     │ │  │
│  │  │ Gold High Return  │   8    │ 62%  │ $380   │ 1.8│ ⚠️     │ │  │
│  │  │ Champion 75WR     │   15   │ 73%  │ $450   │ 2.1│ ✅     │ │  │
│  │  │ Momentum V2       │   7    │ 71%  │ $180   │ 1.9│ ✅     │ │  │
│  │  │ All Weather 70WR  │   5    │ 60%  │ -$180  │ 0.8│ ❌     │ │  │
│  │  │                                                          │ │  │
│  │  │ [Sort by: P&L ▼]  [Export CSV]  [View Details]         │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 📈 PERFORMANCE CHARTS                                    │ │  │
│  │  │                                                          │ │  │
│  │  │ [Cumulative P&L]  [Win Rate Trend]  [Daily P&L]        │ │  │
│  │  │                                                          │ │  │
│  │  │  ┌──────────────────────────────────────────────┐       │ │  │
│  │  │  │  Cumulative P&L Over Time                     │       │ │  │
│  │  │  │  ┌────────────────────────────────────────┐ │       │ │  │
│  │  │  │  │                                        │ │       │ │  │
│  │  │  │  │    $1,500 ┤                            │ │       │ │  │
│  │  │  │  │    $1,000 ┤          ╭───╮            │ │       │ │  │
│  │  │  │  │     $500 ┤    ╭───╮  │   │  ╭───╮      │ │       │ │  │
│  │  │  │  │       $0 ┼────┴───┴──┴───┴──┴───┴─     │ │       │ │  │
│  │  │  │  │    -$500 ┤                            │ │       │ │  │
│  │  │  │  │         Mon  Tue  Wed  Thu  Fri      │ │       │ │  │
│  │  │  │  └────────────────────────────────────────┘ │       │ │  │
│  │  │  └──────────────────────────────────────────────┘       │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  📋 TRADE LOG & HISTORY                                       │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 🔍 SEARCH & FILTER                                        │ │  │
│  │  │                                                          │ │  │
│  │  │ Search: [____________]  [Filter] [Clear]                │ │  │
│  │  │                                                          │ │  │
│  │  │ Show: [All] [Open] [Closed] [Winners] [Losers]          │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ Trade ID          │ Strategy │ Instrument │ Direction │ │  │
│  │  │ Entry Time         │ Entry    │ Exit       │ P&L       │ │  │
│  │  │ ─────────────────────────────────────────────────────── │ │  │
│  │  │ ultra_v2_001      │ Ultra V2 │ EUR_USD    │ BUY       │ │  │
│  │  │ Oct 28 09:15      │ 1.0850   │ 1.0875     │ +$45.00   │ │  │
│  │  │ ─────────────────────────────────────────────────────── │ │  │
│  │  │ gold_hr_002       │ Gold HR  │ XAU_USD    │ BUY       │ │  │
│  │  │ Oct 28 10:30      │ $2650    │ $2658      │ +$80.00   │ │  │
│  │  │ ─────────────────────────────────────────────────────── │ │  │
│  │  │ champion_003      │ Champ 75 │ GBP_USD    │ SELL      │ │  │
│  │  │ Oct 28 14:20      │ 1.2650   │ 1.2620     │ +$30.00   │ │  │
│  │  │                                                          │ │  │
│  │  │ [< Prev]  Page 1 of 5  [Next >]                        │ │  │
│  │  │ [Export to CSV] [Export to PDF]                         │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Key Features

### **1. Weekly Roadmap & Progress Section**
- **Current Week Overview**: Shows current day, progress percentage
- **Weekly Target vs Actual**: Real-time tracking against roadmap
- **Daily Breakdown**: Each day's target vs actual performance
- **Strategy Roadmaps**: Individual strategy progress for the week
- **Visual Progress Bars**: Color-coded (green=on track, yellow=warning, red=off track)

### **2. Strategy Performance Tracker**
- **Advanced Filtering**:
  - By Strategy (dropdown)
  - By Date Range (custom or presets)
  - By Instrument (EUR_USD, XAU_USD, etc.)
  - By Trade Status (Open, Closed, Winners, Losers)
  - Quick filters: Today, This Week, This Month, All Time

- **Performance Summary**:
  - Total trades, win rate, profit, profit factor
  - Max drawdown, Sharpe ratio
  - Updates in real-time based on filters

- **Strategy Breakdown Table**:
  - Sortable columns (Trades, Win%, P&L, Profit Factor)
  - Status indicators (✅ Good, ⚠️ Warning, ❌ Needs Attention)
  - Click to drill down into strategy details

- **Performance Charts**:
  - Cumulative P&L over time
  - Win rate trend
  - Daily P&L breakdown
  - Interactive (hover for details, zoom, pan)

### **3. Trade Log & History**
- **Search & Filter**: Find specific trades quickly
- **Detailed Trade List**: All trade details in table format
- **Export Options**: CSV, PDF reports
- **Pagination**: Handle large datasets efficiently
- **Real-time Updates**: New trades appear automatically

---

## 🔌 API Endpoints

### **Weekly Roadmap**
```
GET /api/performance/weekly-roadmap
Response: {
  "week_info": {
    "week_start": "2025-10-28",
    "week_end": "2025-11-03",
    "current_day": "Wednesday",
    "days_passed": 3,
    "days_remaining": 4
  },
  "targets": {
    "weekly_target": 3500,
    "current_progress": 1250,
    "expected_progress": 1500,
    "weekly_progress_pct": 35.7,
    "on_track": false
  },
  "daily_breakdown": [
    {
      "day": "Monday",
      "target": 500,
      "actual": 450,
      "progress_pct": 90,
      "status": "on_track"
    },
    ...
  ],
  "strategy_roadmaps": [
    {
      "strategy_id": "ultra_strict_v2",
      "strategy_name": "Ultra Strict V2",
      "pair": "EUR_USD",
      "weekly_target": 800,
      "current_progress": 420,
      "progress_pct": 52.5,
      "entry_zones": [1.0850, 1.0820, 1.0800],
      "status": "on_track"
    },
    ...
  ]
}
```

### **Strategy Performance**
```
GET /api/performance/strategies?strategy_id=&date_from=&date_to=&instrument=
Response: {
  "summary": {
    "total_trades": 47,
    "win_rate": 72.3,
    "total_profit": 1250,
    "profit_factor": 2.1,
    "max_drawdown": -180,
    "sharpe_ratio": 1.8
  },
  "strategies": [
    {
      "strategy_id": "ultra_strict_v2",
      "strategy_name": "Ultra Strict V2",
      "total_trades": 12,
      "win_rate": 75,
      "total_profit": 420,
      "profit_factor": 2.3,
      "status": "good"
    },
    ...
  ],
  "charts": {
    "cumulative_pnl": [...],
    "win_rate_trend": [...],
    "daily_pnl": [...]
  }
}
```

### **Trade History**
```
GET /api/performance/trades?strategy_id=&status=&instrument=&date_from=&date_to=&limit=50&offset=0
Response: {
  "trades": [
    {
      "trade_id": "ultra_v2_001",
      "strategy_id": "ultra_strict_v2",
      "instrument": "EUR_USD",
      "direction": "BUY",
      "entry_price": 1.0850,
      "exit_price": 1.0875,
      "entry_time": "2025-10-28T09:15:00",
      "exit_time": "2025-10-28T10:30:00",
      "realized_pnl": 45.00,
      "pnl_pips": 25,
      "status": "closed"
    },
    ...
  ],
  "total": 47,
  "page": 1,
  "per_page": 50
}
```

### **Export**
```
GET /api/performance/export?format=csv&strategy_id=&date_from=&date_to=
Response: CSV file download
```

---

## 🗄️ Database Integration

### **Uses Existing Systems:**
1. **`trade_database.py`** - Main trade storage
   - `get_closed_trades()` - Filtered trade history
   - `get_strategy_metrics()` - Strategy performance
   - `get_daily_snapshots()` - Daily performance data

2. **`trade_logger.py`** - Trade logging
   - `get_recent_trades()` - Recent trade list
   - `get_strategy_summary()` - Strategy overview

3. **`performance_tracker.py`** - Historical tracking
   - `get_strategy_history()` - Historical performance
   - `get_daily_summary()` - Daily summaries

4. **`trump_dna_framework.py`** - Roadmap data
   - `weekly_plans` - Weekly roadmap targets
   - Daily targets, entry zones, etc.

---

## 📊 Data Flow

```
┌─────────────────┐
│  Trade Logger   │ ──> Logs trades to ──> ┌──────────────┐
│  (Live System)  │                         │ Trade DB     │
└─────────────────┘                         └──────────────┘
                                                    │
                                                    ▼
┌─────────────────┐                         ┌──────────────┐
│ Trump DNA       │ ──> Generates ──>       │ Roadmap Data │
│ Framework       │     weekly plans        │ (In Memory)  │
└─────────────────┘                         └──────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Performance Dashboard (Port 8081)                          │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Weekly Roadmap   │  │ Strategy Metrics │               │
│  │ Component        │  │ Component        │               │
│  └──────────────────┘  └──────────────────┘               │
│         │                      │                            │
│         └──────────┬───────────┘                            │
│                    ▼                                        │
│         ┌─────────────────────┐                             │
│         │ API Endpoints       │                             │
│         │ - /api/performance/* │                             │
│         └─────────────────────┘                             │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                             │
│         │ Query Trade DB      │                             │
│         │ + Roadmap Data       │                             │
│         └─────────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Implementation Steps

### **Phase 1: Backend API (Week 1)**
1. Create new Flask app (`performance_dashboard.py`)
2. Implement roadmap API endpoints
3. Implement strategy performance endpoints
4. Implement trade history endpoints
5. Add filtering logic
6. Connect to existing databases

### **Phase 2: Frontend (Week 2)**
1. Create HTML template (`performance_dashboard.html`)
2. Build weekly roadmap component
3. Build strategy performance table
4. Build trade log table
5. Add filtering UI
6. Add charts (Chart.js or similar)

### **Phase 3: Integration (Week 3)**
1. Connect frontend to backend APIs
2. Add real-time updates (WebSocket or polling)
3. Add export functionality
4. Add navigation between main dashboard and performance dashboard
5. Testing and optimization

---

## 💡 Additional Features (Future)

1. **Alerts & Notifications**
   - Email when strategy falls behind roadmap
   - Telegram alerts for key milestones

2. **Comparison Views**
   - Compare strategies side-by-side
   - Compare this week vs last week
   - Compare this month vs last month

3. **Advanced Analytics**
   - Best/worst trading times
   - Best/worst instruments
   - Correlation analysis

4. **Reports**
   - Weekly performance reports (PDF)
   - Monthly summaries
   - Strategy performance reports

5. **Custom Dashboards**
   - User-configurable widgets
   - Save filter presets
   - Personal dashboard layouts

---

## 🚀 Quick Start

Once implemented, access at:
- **URL:** `http://localhost:8081/performance`
- **Main Dashboard:** `http://localhost:8080/` (existing)
- **Link:** Add "Performance" button in main dashboard header

---

## 📝 Notes

- **Separate dashboard** keeps main dashboard focused on live trading
- **Real-time updates** via WebSocket or 5-second polling
- **Mobile responsive** design for viewing on phone/tablet
- **Export functionality** for sharing reports
- **Performance optimized** - uses caching, pagination, indexed queries
