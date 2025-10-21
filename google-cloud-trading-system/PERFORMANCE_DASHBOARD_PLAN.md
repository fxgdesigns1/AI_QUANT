# Performance Tracking Dashboard - Comprehensive Plan
Created: 2025-09-30
Status: Planning Phase

## 🎯 Objectives

Create a **separate, read-only analytics dashboard** that:
1. Tracks real trading performance across all accounts
2. Monitors strategy changes and evolution over time
3. Provides deep analytics without interfering with live trading
4. Uses 100% real data (no simulated/dummy data)
5. Enables data-driven strategy optimization

---

## 📊 Architecture Overview

### System Design
```
┌─────────────────────────────────────────────────────────────┐
│                    LIVE TRADING SYSTEM                      │
│  (Current system - google-cloud-trading-system)             │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │ Account  │  │ Strategy │  │  Order   │                │
│  │ Manager  │  │ Executor │  │ Manager  │                │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                │
│       │             │              │                       │
│       └─────────────┼──────────────┘                       │
│                     │                                       │
│              ┌──────▼──────┐                               │
│              │   Events    │ (Read-only)                   │
│              │  Publisher  │                               │
│              └──────┬──────┘                               │
└─────────────────────┼────────────────────────────────────┘
                      │
              ┌───────▼────────┐
              │  Event Stream  │ (Non-blocking)
              └───────┬────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│          PERFORMANCE TRACKING DASHBOARD                   │
│              (Separate application)                       │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Data    │  │ Analytics│  │  Visual  │              │
│  │Collector │  │  Engine  │  │ Dashboard│              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │             │              │                     │
│  ┌────▼─────────────▼──────────────▼─────┐              │
│  │     Performance Database (SQLite)      │              │
│  └────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

### Key Principles
1. **Read-Only Access**: Dashboard only reads data, never writes to trading system
2. **Non-Blocking**: No impact on trading system performance
3. **Real Data Only**: Direct from OANDA API and trading logs
4. **Separate Database**: Own database for analytics (no shared state)
5. **Independent Deployment**: Can run locally or on separate port

---

## 📈 Data Collection Strategy

### 1. Trade Data Collection
**Source**: OANDA API (direct read-only queries)

**Data Points to Track**:
```python
{
    "trade_id": str,
    "account_id": str,
    "account_name": str,
    "instrument": str,
    "strategy_name": str,
    "strategy_version": str,
    
    # Entry data
    "entry_time": datetime,
    "entry_price": float,
    "units": int,
    "side": "BUY/SELL",
    "entry_reason": str,  # Signal details
    
    # Exit data
    "exit_time": datetime,
    "exit_price": float,
    "exit_reason": str,  # "TP/SL/Manual/News"
    
    # Performance
    "realized_pl": float,
    "realized_pl_pct": float,
    "commission": float,
    "net_pl": float,
    
    # Risk metrics
    "risk_amount": float,
    "risk_pct": float,
    "r_multiple": float,  # Reward/Risk ratio
    
    # Market context
    "market_regime": str,  # "trending/ranging/volatile"
    "volatility_score": float,
    "spread_at_entry": float,
    "news_sentiment": float,
    
    # Duration
    "duration_seconds": int,
    "bars_held": int,
    
    # Metadata
    "created_at": datetime,
    "updated_at": datetime
}
```

### 2. Strategy Change Tracking
**Source**: Configuration files + strategy parameters

**Data Points**:
```python
{
    "change_id": str,
    "timestamp": datetime,
    "strategy_name": str,
    "account_id": str,
    
    # Changed parameters
    "parameter_changed": str,
    "old_value": Any,
    "new_value": Any,
    
    # Context
    "change_reason": str,
    "changed_by": str,  # "system/manual/optimization"
    
    # Performance before change
    "trades_before": int,
    "win_rate_before": float,
    "avg_pl_before": float,
    "sharpe_before": float,
    
    # Track results after change
    "trades_after": int,
    "win_rate_after": float,
    "avg_pl_after": float,
    "sharpe_after": float,
    
    "metadata": dict
}
```

### 3. Account Performance Tracking
**Source**: OANDA API + Internal calculations

**Data Points**:
```python
{
    "snapshot_id": str,
    "timestamp": datetime,
    "account_id": str,
    "account_name": str,
    
    # Balance metrics
    "balance": float,
    "equity": float,
    "margin_used": float,
    "margin_available": float,
    "unrealized_pl": float,
    
    # Position metrics
    "open_positions": int,
    "open_trades": int,
    "pending_orders": int,
    
    # Daily metrics
    "daily_pl": float,
    "daily_trades": int,
    "daily_wins": int,
    "daily_losses": int,
    
    # Cumulative metrics
    "total_trades": int,
    "total_wins": int,
    "total_losses": int,
    "win_rate": float,
    "avg_win": float,
    "avg_loss": float,
    "profit_factor": float,
    
    # Risk metrics
    "max_drawdown": float,
    "max_drawdown_pct": float,
    "current_drawdown": float,
    "sharpe_ratio": float,
    "sortino_ratio": float,
    "calmar_ratio": float,
    
    # Time-based returns
    "daily_return": float,
    "weekly_return": float,
    "monthly_return": float,
    "ytd_return": float,
    
    "metadata": dict
}
```

### 4. Strategy Performance Metrics
**Source**: Aggregated trade data

**Data Points**:
```python
{
    "metric_id": str,
    "timestamp": datetime,
    "strategy_name": str,
    "account_id": str,
    "time_period": str,  # "daily/weekly/monthly/all-time"
    
    # Trade statistics
    "total_trades": int,
    "winning_trades": int,
    "losing_trades": int,
    "break_even_trades": int,
    "win_rate": float,
    
    # P&L metrics
    "gross_profit": float,
    "gross_loss": float,
    "net_profit": float,
    "profit_factor": float,
    "avg_trade_pl": float,
    "avg_win": float,
    "avg_loss": float,
    "largest_win": float,
    "largest_loss": float,
    
    # Risk metrics
    "max_drawdown": float,
    "avg_drawdown": float,
    "recovery_factor": float,
    "sharpe_ratio": float,
    "sortino_ratio": float,
    "calmar_ratio": float,
    
    # Efficiency metrics
    "avg_trade_duration": float,
    "avg_bars_held": float,
    "trades_per_day": float,
    "avg_r_multiple": float,
    
    # Consistency metrics
    "consecutive_wins": int,
    "consecutive_losses": int,
    "max_consecutive_wins": int,
    "max_consecutive_losses": int,
    
    # Market condition performance
    "trending_win_rate": float,
    "ranging_win_rate": float,
    "volatile_win_rate": float,
    
    # Time-based performance
    "best_day": float,
    "worst_day": float,
    "avg_daily_return": float,
    "volatility": float,
    
    "metadata": dict
}
```

---

## 🗄️ Database Schema

### Tables Structure

```sql
-- Core Tables
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    instrument TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    strategy_version TEXT,
    
    -- Entry
    entry_time TIMESTAMP NOT NULL,
    entry_price REAL NOT NULL,
    units INTEGER NOT NULL,
    side TEXT NOT NULL,
    entry_reason TEXT,
    
    -- Exit
    exit_time TIMESTAMP,
    exit_price REAL,
    exit_reason TEXT,
    
    -- Performance
    realized_pl REAL,
    realized_pl_pct REAL,
    commission REAL,
    net_pl REAL,
    
    -- Risk
    risk_amount REAL,
    risk_pct REAL,
    r_multiple REAL,
    
    -- Context
    market_regime TEXT,
    volatility_score REAL,
    spread_at_entry REAL,
    news_sentiment REAL,
    
    -- Duration
    duration_seconds INTEGER,
    bars_held INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_account_time (account_id, entry_time),
    INDEX idx_strategy_time (strategy_name, entry_time),
    INDEX idx_instrument (instrument)
);

CREATE TABLE strategy_changes (
    change_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_name TEXT NOT NULL,
    account_id TEXT,
    
    -- Change details
    parameter_changed TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_reason TEXT,
    changed_by TEXT,
    
    -- Performance snapshots
    trades_before INTEGER,
    win_rate_before REAL,
    avg_pl_before REAL,
    sharpe_before REAL,
    
    trades_after INTEGER,
    win_rate_after REAL,
    avg_pl_after REAL,
    sharpe_after REAL,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_strategy_time (strategy_name, timestamp),
    INDEX idx_parameter (parameter_changed)
);

CREATE TABLE account_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    
    -- Balance
    balance REAL NOT NULL,
    equity REAL NOT NULL,
    margin_used REAL,
    margin_available REAL,
    unrealized_pl REAL,
    
    -- Positions
    open_positions INTEGER,
    open_trades INTEGER,
    pending_orders INTEGER,
    
    -- Daily metrics
    daily_pl REAL,
    daily_trades INTEGER,
    daily_wins INTEGER,
    daily_losses INTEGER,
    
    -- Cumulative metrics
    total_trades INTEGER,
    total_wins INTEGER,
    total_losses INTEGER,
    win_rate REAL,
    avg_win REAL,
    avg_loss REAL,
    profit_factor REAL,
    
    -- Risk metrics
    max_drawdown REAL,
    max_drawdown_pct REAL,
    current_drawdown REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    calmar_ratio REAL,
    
    -- Returns
    daily_return REAL,
    weekly_return REAL,
    monthly_return REAL,
    ytd_return REAL,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_account_time (account_id, timestamp)
);

CREATE TABLE strategy_metrics (
    metric_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_name TEXT NOT NULL,
    account_id TEXT,
    time_period TEXT NOT NULL,
    
    -- Trade stats
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    break_even_trades INTEGER,
    win_rate REAL,
    
    -- P&L
    gross_profit REAL,
    gross_loss REAL,
    net_profit REAL,
    profit_factor REAL,
    avg_trade_pl REAL,
    avg_win REAL,
    avg_loss REAL,
    largest_win REAL,
    largest_loss REAL,
    
    -- Risk metrics
    max_drawdown REAL,
    avg_drawdown REAL,
    recovery_factor REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    calmar_ratio REAL,
    
    -- Efficiency
    avg_trade_duration REAL,
    avg_bars_held REAL,
    trades_per_day REAL,
    avg_r_multiple REAL,
    
    -- Consistency
    consecutive_wins INTEGER,
    consecutive_losses INTEGER,
    max_consecutive_wins INTEGER,
    max_consecutive_losses INTEGER,
    
    -- Market conditions
    trending_win_rate REAL,
    ranging_win_rate REAL,
    volatile_win_rate REAL,
    
    -- Time-based
    best_day REAL,
    worst_day REAL,
    avg_daily_return REAL,
    volatility REAL,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_strategy_period (strategy_name, time_period, timestamp),
    INDEX idx_account_period (account_id, time_period, timestamp)
);

-- Comparison/Analysis Tables
CREATE TABLE strategy_comparisons (
    comparison_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_a TEXT NOT NULL,
    strategy_b TEXT NOT NULL,
    time_period TEXT NOT NULL,
    
    -- Performance deltas
    pl_difference REAL,
    win_rate_difference REAL,
    sharpe_difference REAL,
    drawdown_difference REAL,
    
    -- Statistical significance
    p_value REAL,
    confidence_level REAL,
    
    -- Recommendation
    better_strategy TEXT,
    confidence_score REAL,
    
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE optimization_history (
    optimization_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_name TEXT NOT NULL,
    account_id TEXT,
    
    -- Parameters tested
    parameters_tested TEXT,  -- JSON
    test_results TEXT,  -- JSON
    
    -- Best configuration
    best_parameters TEXT,  -- JSON
    expected_performance REAL,
    
    -- Applied?
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP,
    actual_performance REAL,
    
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 Data Collection Methods

### Method 1: Direct OANDA API Polling (Read-Only)
**Frequency**: Every 5 minutes
**Non-Intrusive**: Uses separate API client

```python
class PerformanceDataCollector:
    """Read-only data collector from OANDA API"""
    
    def __init__(self):
        # Separate OANDA client (read-only)
        self.oanda_client = OandaClient(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=None  # Will query all accounts
        )
        self.db = PerformanceDatabase()
    
    def collect_trades(self, account_id: str):
        """Fetch completed trades from OANDA"""
        # Get trades from last collection time
        trades = self.oanda_client.get_closed_trades(
            account_id=account_id,
            since=self.last_collection_time
        )
        
        for trade in trades:
            # Parse and store trade data
            self.db.store_trade({
                'trade_id': trade.id,
                'account_id': account_id,
                'instrument': trade.instrument,
                'entry_time': trade.openTime,
                'entry_price': trade.price,
                'exit_time': trade.closeTime,
                'exit_price': trade.closePrice,
                'realized_pl': trade.realizedPL,
                # ... more fields
            })
    
    def collect_account_snapshot(self, account_id: str):
        """Collect current account state"""
        account = self.oanda_client.get_account_summary(account_id)
        
        self.db.store_snapshot({
            'account_id': account_id,
            'balance': account.balance,
            'equity': account.NAV,
            'margin_used': account.marginUsed,
            'unrealized_pl': account.unrealizedPL,
            # ... calculate metrics
        })
```

### Method 2: Log File Parsing
**Frequency**: Continuous (non-blocking)
**Source**: Trading system logs

```python
class LogFileCollector:
    """Parse trading system logs for events"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.last_position = 0
    
    def collect_strategy_changes(self):
        """Detect strategy parameter changes from logs"""
        with open(self.log_file, 'r') as f:
            f.seek(self.last_position)
            
            for line in f:
                if 'STRATEGY_CHANGE' in line:
                    # Parse change event
                    change = self.parse_strategy_change(line)
                    self.db.store_strategy_change(change)
            
            self.last_position = f.tell()
```

### Method 3: Database Replication (if needed)
**Only if trading system uses database**
**Method**: Read replica or periodic snapshot

---

## 📊 Analytics Engine

### Key Metrics to Calculate

#### 1. Performance Metrics
```python
class PerformanceAnalytics:
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0.0
        
        excess_returns = [r - risk_free_rate for r in returns]
        avg_return = np.mean(excess_returns)
        std_return = np.std(excess_returns)
        
        return (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio (downside deviation only)"""
        excess_returns = [r - risk_free_rate for r in returns]
        avg_return = np.mean(excess_returns)
        
        # Only negative returns for downside deviation
        downside_returns = [r for r in excess_returns if r < 0]
        downside_std = np.std(downside_returns) if downside_returns else 0.0
        
        return (avg_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Tuple[float, float]:
        """Calculate maximum drawdown and current drawdown"""
        peak = equity_curve[0]
        max_dd = 0.0
        current_dd = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
            current_dd = dd
        
        return max_dd, current_dd
    
    def calculate_profit_factor(self, trades: List[dict]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(t['net_pl'] for t in trades if t['net_pl'] > 0)
        gross_loss = abs(sum(t['net_pl'] for t in trades if t['net_pl'] < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else 0.0
```

#### 2. Strategy Comparison Analytics
```python
class StrategyComparison:
    
    def compare_strategies(self, strategy_a: str, strategy_b: str, period: str = '30d') -> dict:
        """Statistical comparison of two strategies"""
        
        # Get metrics for both strategies
        metrics_a = self.db.get_strategy_metrics(strategy_a, period)
        metrics_b = self.db.get_strategy_metrics(strategy_b, period)
        
        # Statistical tests
        returns_a = self.db.get_daily_returns(strategy_a, period)
        returns_b = self.db.get_daily_returns(strategy_b, period)
        
        # T-test for mean difference
        t_stat, p_value = stats.ttest_ind(returns_a, returns_b)
        
        return {
            'strategy_a': strategy_a,
            'strategy_b': strategy_b,
            'pl_difference': metrics_a['net_profit'] - metrics_b['net_profit'],
            'win_rate_diff': metrics_a['win_rate'] - metrics_b['win_rate'],
            'sharpe_diff': metrics_a['sharpe_ratio'] - metrics_b['sharpe_ratio'],
            'p_value': p_value,
            'statistically_significant': p_value < 0.05,
            'better_strategy': strategy_a if metrics_a['sharpe_ratio'] > metrics_b['sharpe_ratio'] else strategy_b
        }
```

#### 3. Change Impact Analysis
```python
class ChangeImpactAnalyzer:
    
    def analyze_strategy_change_impact(self, change_id: str, lookback_days: int = 30) -> dict:
        """Analyze the impact of a strategy change"""
        
        change = self.db.get_strategy_change(change_id)
        
        # Get performance before and after
        before_trades = self.db.get_trades_before_change(change_id, lookback_days)
        after_trades = self.db.get_trades_after_change(change_id, lookback_days)
        
        # Calculate metrics
        before_metrics = self.calculate_metrics(before_trades)
        after_metrics = self.calculate_metrics(after_trades)
        
        # Improvement analysis
        improvement = {
            'win_rate': after_metrics['win_rate'] - before_metrics['win_rate'],
            'avg_pl': after_metrics['avg_pl'] - before_metrics['avg_pl'],
            'sharpe': after_metrics['sharpe'] - before_metrics['sharpe'],
            'profit_factor': after_metrics['profit_factor'] - before_metrics['profit_factor']
        }
        
        # Determine if change was beneficial
        improvement_score = sum([
            1 if improvement['win_rate'] > 0 else -1,
            1 if improvement['avg_pl'] > 0 else -1,
            1 if improvement['sharpe'] > 0 else -1,
            1 if improvement['profit_factor'] > 0 else -1
        ])
        
        return {
            'change_id': change_id,
            'parameter_changed': change['parameter_changed'],
            'before_metrics': before_metrics,
            'after_metrics': after_metrics,
            'improvement': improvement,
            'improvement_score': improvement_score,
            'recommendation': 'Keep' if improvement_score > 0 else 'Revert',
            'confidence': abs(improvement_score) / 4  # 0 to 1
        }
```

---

## 🎨 Dashboard UI Components

### 1. Overview Dashboard
**URL**: `/analytics/overview`

**Widgets**:
- Total P&L (all accounts)
- Win rate trend (last 30 days)
- Sharpe ratio by account
- Daily returns chart
- Max drawdown indicator
- Active positions count
- Today's trades summary

### 2. Account Performance Dashboard
**URL**: `/analytics/account/<account_id>`

**Sections**:
- Account summary card
- Equity curve (with drawdown overlay)
- Daily/Weekly/Monthly returns
- Win rate by instrument
- Trade distribution (wins/losses histogram)
- Risk metrics table
- Recent trades list

### 3. Strategy Performance Dashboard
**URL**: `/analytics/strategy/<strategy_name>`

**Sections**:
- Strategy overview card
- Performance metrics table
- Trade frequency chart
- Win rate by market condition
- R-multiple distribution
- Parameter history timeline
- Change impact analysis

### 4. Strategy Comparison Dashboard
**URL**: `/analytics/compare`

**Features**:
- Side-by-side strategy comparison
- Performance metrics diff table
- Statistical significance tests
- Equity curve comparison
- Risk-adjusted returns comparison
- Recommendation engine

### 5. Change Tracking Dashboard
**URL**: `/analytics/changes`

**Features**:
- Timeline of all strategy changes
- Before/after performance comparison
- Impact analysis for each change
- Rollback recommendations
- Optimization suggestions

### 6. Real-Time Monitoring
**URL**: `/analytics/live`

**Features**:
- Live trade feed
- Account balance updates
- Current positions
- Open P&L
- Risk exposure
- News feed integration

---

## 🔄 Data Collection Schedule

```yaml
collectors:
  # High-frequency collectors (minimal load)
  - name: live_prices
    frequency: 5s
    source: OANDA_API
    method: streaming
    
  - name: account_snapshots
    frequency: 1m
    source: OANDA_API
    method: polling
  
  # Medium-frequency collectors
  - name: closed_trades
    frequency: 5m
    source: OANDA_API
    method: polling
    
  - name: open_positions
    frequency: 1m
    source: OANDA_API
    method: polling
  
  # Low-frequency collectors
  - name: strategy_metrics
    frequency: 15m
    source: database_calculation
    method: batch
    
  - name: performance_analysis
    frequency: 1h
    source: database_calculation
    method: batch
  
  # Daily collectors
  - name: daily_summary
    frequency: daily
    time: "00:05:00"
    source: database_calculation
    method: batch
```

---

## 🚀 Implementation Plan

### Phase 1: Foundation (Week 1)
**Goal**: Basic data collection and storage

**Tasks**:
1. Create separate database schema
2. Implement OANDA data collector
3. Build trade storage system
4. Create account snapshot collector
5. Set up basic data validation

**Deliverables**:
- `performance_database.py` - Database layer
- `data_collector.py` - OANDA collector
- `performance_schema.sql` - Database schema
- Basic tests

### Phase 2: Analytics Engine (Week 2)
**Goal**: Calculate performance metrics

**Tasks**:
1. Implement performance calculators
2. Build strategy comparison engine
3. Create change impact analyzer
4. Develop statistical tests
5. Add time-series analysis

**Deliverables**:
- `performance_analytics.py` - Analytics engine
- `strategy_comparison.py` - Comparison tools
- `change_analyzer.py` - Impact analysis
- Unit tests for all calculators

### Phase 3: Dashboard UI (Week 3)
**Goal**: Visualization and interface

**Tasks**:
1. Create Flask app (separate from trading system)
2. Build overview dashboard
3. Implement account performance view
4. Create strategy comparison view
5. Add real-time monitoring

**Deliverables**:
- `analytics_app.py` - Flask application
- `templates/` - HTML templates
- `static/` - CSS/JS assets
- Interactive charts (Chart.js/Plotly)

### Phase 4: Advanced Features (Week 4)
**Goal**: Deep insights and recommendations

**Tasks**:
1. Change tracking dashboard
2. Optimization suggestions
3. Alert system for anomalies
4. Export/report generation
5. Historical backtesting integration

**Deliverables**:
- `change_tracking.py` - Change monitor
- `optimization_suggester.py` - ML-based suggestions
- `alert_engine.py` - Anomaly detection
- PDF report generator

### Phase 5: Testing & Deployment (Week 5)
**Goal**: Production-ready system

**Tasks**:
1. Comprehensive testing
2. Performance optimization
3. Documentation
4. Deployment scripts
5. Monitoring setup

**Deliverables**:
- Full test suite
- Deployment guide
- User documentation
- Monitoring dashboard

---

## 📦 File Structure

```
google-cloud-trading-system/
└── analytics/
    ├── __init__.py
    ├── app.py                      # Flask app (port 8081)
    ├── config.py                   # Analytics config
    │
    ├── collectors/
    │   ├── __init__.py
    │   ├── oanda_collector.py      # Read-only OANDA queries
    │   ├── log_collector.py        # Parse trading logs
    │   └── scheduler.py            # Collection scheduling
    │
    ├── database/
    │   ├── __init__.py
    │   ├── schema.sql              # Database schema
    │   ├── models.py               # SQLAlchemy models
    │   └── connection.py           # DB connection
    │
    ├── analytics/
    │   ├── __init__.py
    │   ├── performance.py          # Performance calculators
    │   ├── strategy_comparison.py  # Strategy comparison
    │   ├── change_analysis.py      # Change impact analysis
    │   └── statistical_tests.py    # Statistical methods
    │
    ├── dashboards/
    │   ├── __init__.py
    │   ├── overview.py             # Overview dashboard
    │   ├── account.py              # Account dashboard
    │   ├── strategy.py             # Strategy dashboard
    │   ├── comparison.py           # Comparison dashboard
    │   └── changes.py              # Change tracking
    │
    ├── templates/
    │   ├── base.html
    │   ├── overview.html
    │   ├── account.html
    │   ├── strategy.html
    │   ├── comparison.html
    │   └── changes.html
    │
    ├── static/
    │   ├── css/
    │   │   └── analytics.css
    │   └── js/
    │       ├── charts.js
    │       └── analytics.js
    │
    ├── tests/
    │   ├── test_collectors.py
    │   ├── test_analytics.py
    │   └── test_dashboards.py
    │
    ├── utils/
    │   ├── __init__.py
    │   ├── metrics.py              # Metric calculations
    │   └── validators.py           # Data validation
    │
    ├── requirements-analytics.txt  # Separate requirements
    ├── analytics.db                # SQLite database
    └── README.md                   # Analytics documentation
```

---

## 🔐 Security & Isolation

### Read-Only Access
```python
# Separate OANDA client with read-only operations
class ReadOnlyOandaClient:
    """OANDA client that only reads data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = os.getenv('OANDA_BASE_URL')
    
    # Only implement GET methods
    def get_account_summary(self, account_id: str) -> dict:
        """Read-only account query"""
        pass
    
    def get_closed_trades(self, account_id: str, since: datetime) -> List[dict]:
        """Read-only trade history"""
        pass
    
    # NO POST/PUT/DELETE methods - prevent any trading actions
```

### Separate Deployment
```yaml
# analytics_app.yaml (separate App Engine service)
service: analytics
runtime: python39
instance_class: F1  # Smaller instance

manual_scaling:
  instances: 1  # Single instance for analytics

env_variables:
  # Read-only access
  OANDA_API_KEY: "..."
  TRADING_SYSTEM_URL: "https://ai-quant-trading.uc.r.appspot.com"
  ANALYTICS_PORT: "8081"
  READ_ONLY_MODE: "true"
```

---

## 📊 Key Performance Indicators (KPIs)

### Account-Level KPIs
1. **Total Return**: Cumulative % return
2. **Sharpe Ratio**: Risk-adjusted returns
3. **Max Drawdown**: Largest peak-to-trough decline
4. **Win Rate**: % of profitable trades
5. **Profit Factor**: Gross profit / gross loss
6. **Average R-Multiple**: Average reward/risk ratio

### Strategy-Level KPIs
1. **Strategy Return**: Strategy-specific returns
2. **Trade Frequency**: Trades per day
3. **Average Duration**: Time in market
4. **Market Condition Performance**: Win rate by regime
5. **Consistency**: Consecutive wins/losses
6. **Efficiency**: Return per unit time

### System-Level KPIs
1. **Portfolio Correlation**: Cross-strategy correlation
2. **Risk Utilization**: % of capacity used
3. **Daily Volatility**: Portfolio volatility
4. **Recovery Time**: Time to recover from drawdowns
5. **System Health**: Uptime and error rates

---

## 🎯 Success Criteria

### Must-Have Features
- ✅ Real-time data collection (no dummy data)
- ✅ Zero interference with trading system
- ✅ All 3 accounts tracked separately
- ✅ Strategy-level performance tracking
- ✅ Change impact analysis
- ✅ Historical performance visualization

### Performance Requirements
- ✅ Data collection latency < 1 minute
- ✅ Dashboard load time < 2 seconds
- ✅ Real-time updates every 5 seconds
- ✅ 30+ days of historical data
- ✅ < 1% CPU impact on trading system

### Quality Requirements
- ✅ 100% real data (verified against OANDA)
- ✅ Data integrity checks
- ✅ Audit trail for all changes
- ✅ Comprehensive test coverage
- ✅ Clear documentation

---

## 🚦 Next Steps

1. **Review this plan** - Confirm approach and requirements
2. **Phase 1 kick-off** - Start with database schema
3. **Iterative development** - Build and test incrementally
4. **User feedback** - Adjust based on real usage
5. **Continuous improvement** - Add features as needed

---

*This plan ensures accurate performance tracking without disrupting your live trading system.*


