-- Performance Analytics Database Schema
-- Created: 2025-09-30
-- Purpose: Track trading performance without interfering with live system

-- ============================================================================
-- TRADES TABLE - Core trade data
-- ============================================================================
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    instrument TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    strategy_version TEXT DEFAULT '1.0',
    
    -- Entry data
    entry_time TIMESTAMP NOT NULL,
    entry_price REAL NOT NULL,
    units INTEGER NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
    entry_reason TEXT,
    
    -- Exit data
    exit_time TIMESTAMP,
    exit_price REAL,
    exit_reason TEXT,
    
    -- Performance metrics
    realized_pl REAL,
    realized_pl_pct REAL,
    commission REAL DEFAULT 0.0,
    net_pl REAL,
    
    -- Risk metrics
    risk_amount REAL,
    risk_pct REAL,
    r_multiple REAL,  -- Reward/Risk ratio
    
    -- Market context
    market_regime TEXT CHECK(market_regime IN ('trending', 'ranging', 'volatile', 'unknown')),
    volatility_score REAL,
    spread_at_entry REAL,
    news_sentiment REAL,
    
    -- Duration metrics
    duration_seconds INTEGER,
    bars_held INTEGER,
    
    -- Status
    status TEXT DEFAULT 'open' CHECK(status IN ('open', 'closed', 'cancelled')),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trades_account_time ON trades(account_id, entry_time);
CREATE INDEX IF NOT EXISTS idx_trades_strategy_time ON trades(strategy_name, entry_time);
CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time);

-- ============================================================================
-- STRATEGY CHANGES TABLE - Track parameter modifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_changes (
    change_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_name TEXT NOT NULL,
    account_id TEXT,
    
    -- Change details
    parameter_changed TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_reason TEXT,
    changed_by TEXT DEFAULT 'system',
    
    -- Performance snapshots (before change)
    trades_before INTEGER DEFAULT 0,
    win_rate_before REAL DEFAULT 0.0,
    avg_pl_before REAL DEFAULT 0.0,
    sharpe_before REAL DEFAULT 0.0,
    
    -- Performance after change (updated later)
    trades_after INTEGER DEFAULT 0,
    win_rate_after REAL DEFAULT 0.0,
    avg_pl_after REAL DEFAULT 0.0,
    sharpe_after REAL DEFAULT 0.0,
    
    -- Impact assessment
    impact_analyzed BOOLEAN DEFAULT FALSE,
    impact_score REAL,
    recommendation TEXT,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_changes_strategy_time ON strategy_changes(strategy_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_changes_parameter ON strategy_changes(parameter_changed);
CREATE INDEX IF NOT EXISTS idx_changes_account ON strategy_changes(account_id);

-- ============================================================================
-- ACCOUNT SNAPSHOTS TABLE - Regular account state captures
-- ============================================================================
CREATE TABLE IF NOT EXISTS account_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    
    -- Balance metrics
    balance REAL NOT NULL,
    equity REAL NOT NULL,
    margin_used REAL DEFAULT 0.0,
    margin_available REAL DEFAULT 0.0,
    unrealized_pl REAL DEFAULT 0.0,
    
    -- Position metrics
    open_positions INTEGER DEFAULT 0,
    open_trades INTEGER DEFAULT 0,
    pending_orders INTEGER DEFAULT 0,
    
    -- Daily metrics
    daily_pl REAL DEFAULT 0.0,
    daily_trades INTEGER DEFAULT 0,
    daily_wins INTEGER DEFAULT 0,
    daily_losses INTEGER DEFAULT 0,
    
    -- Cumulative metrics
    total_trades INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_losses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    avg_win REAL DEFAULT 0.0,
    avg_loss REAL DEFAULT 0.0,
    profit_factor REAL DEFAULT 0.0,
    
    -- Risk metrics
    max_drawdown REAL DEFAULT 0.0,
    max_drawdown_pct REAL DEFAULT 0.0,
    current_drawdown REAL DEFAULT 0.0,
    sharpe_ratio REAL DEFAULT 0.0,
    sortino_ratio REAL DEFAULT 0.0,
    calmar_ratio REAL DEFAULT 0.0,
    
    -- Time-based returns
    daily_return REAL DEFAULT 0.0,
    weekly_return REAL DEFAULT 0.0,
    monthly_return REAL DEFAULT 0.0,
    ytd_return REAL DEFAULT 0.0,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshots_account_time ON account_snapshots(account_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON account_snapshots(timestamp);

-- ============================================================================
-- STRATEGY METRICS TABLE - Aggregated strategy performance
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_metrics (
    metric_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_name TEXT NOT NULL,
    account_id TEXT,
    time_period TEXT NOT NULL CHECK(time_period IN ('daily', 'weekly', 'monthly', 'all_time')),
    
    -- Trade statistics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    break_even_trades INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    
    -- P&L metrics
    gross_profit REAL DEFAULT 0.0,
    gross_loss REAL DEFAULT 0.0,
    net_profit REAL DEFAULT 0.0,
    profit_factor REAL DEFAULT 0.0,
    avg_trade_pl REAL DEFAULT 0.0,
    avg_win REAL DEFAULT 0.0,
    avg_loss REAL DEFAULT 0.0,
    largest_win REAL DEFAULT 0.0,
    largest_loss REAL DEFAULT 0.0,
    
    -- Risk metrics
    max_drawdown REAL DEFAULT 0.0,
    avg_drawdown REAL DEFAULT 0.0,
    recovery_factor REAL DEFAULT 0.0,
    sharpe_ratio REAL DEFAULT 0.0,
    sortino_ratio REAL DEFAULT 0.0,
    calmar_ratio REAL DEFAULT 0.0,
    
    -- Efficiency metrics
    avg_trade_duration REAL DEFAULT 0.0,
    avg_bars_held REAL DEFAULT 0.0,
    trades_per_day REAL DEFAULT 0.0,
    avg_r_multiple REAL DEFAULT 0.0,
    
    -- Consistency metrics
    consecutive_wins INTEGER DEFAULT 0,
    consecutive_losses INTEGER DEFAULT 0,
    max_consecutive_wins INTEGER DEFAULT 0,
    max_consecutive_losses INTEGER DEFAULT 0,
    
    -- Market condition performance
    trending_win_rate REAL DEFAULT 0.0,
    ranging_win_rate REAL DEFAULT 0.0,
    volatile_win_rate REAL DEFAULT 0.0,
    
    -- Time-based performance
    best_day REAL DEFAULT 0.0,
    worst_day REAL DEFAULT 0.0,
    avg_daily_return REAL DEFAULT 0.0,
    volatility REAL DEFAULT 0.0,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metrics_strategy_period ON strategy_metrics(strategy_name, time_period, timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_account_period ON strategy_metrics(account_id, time_period, timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON strategy_metrics(timestamp);

-- ============================================================================
-- STRATEGY COMPARISONS TABLE - A/B testing results
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_comparisons (
    comparison_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_a TEXT NOT NULL,
    strategy_b TEXT NOT NULL,
    time_period TEXT NOT NULL,
    
    -- Performance deltas
    pl_difference REAL DEFAULT 0.0,
    win_rate_difference REAL DEFAULT 0.0,
    sharpe_difference REAL DEFAULT 0.0,
    drawdown_difference REAL DEFAULT 0.0,
    
    -- Statistical tests
    t_statistic REAL,
    p_value REAL,
    confidence_level REAL,
    statistically_significant BOOLEAN DEFAULT FALSE,
    
    -- Recommendation
    better_strategy TEXT,
    confidence_score REAL DEFAULT 0.0,
    recommendation TEXT,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comparisons_strategies ON strategy_comparisons(strategy_a, strategy_b, timestamp);
CREATE INDEX IF NOT EXISTS idx_comparisons_timestamp ON strategy_comparisons(timestamp);

-- ============================================================================
-- OPTIMIZATION HISTORY TABLE - Track optimization attempts
-- ============================================================================
CREATE TABLE IF NOT EXISTS optimization_history (
    optimization_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_name TEXT NOT NULL,
    account_id TEXT,
    
    -- Optimization details
    optimization_method TEXT,  -- 'grid_search', 'bayesian', 'genetic', etc.
    parameters_tested TEXT,  -- JSON array of parameter sets
    test_results TEXT,  -- JSON array of results
    
    -- Best configuration found
    best_parameters TEXT,  -- JSON
    expected_performance REAL,
    expected_sharpe REAL,
    expected_drawdown REAL,
    
    -- Implementation status
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP,
    actual_performance REAL,
    actual_sharpe REAL,
    actual_drawdown REAL,
    
    -- Validation
    meets_expectations BOOLEAN,
    performance_difference REAL,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_optimization_strategy ON optimization_history(strategy_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_optimization_applied ON optimization_history(applied);

-- ============================================================================
-- DAILY SUMMARIES TABLE - End-of-day rollups
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_summaries (
    summary_id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    account_id TEXT NOT NULL,
    
    -- Daily performance
    starting_balance REAL NOT NULL,
    ending_balance REAL NOT NULL,
    daily_pl REAL DEFAULT 0.0,
    daily_return_pct REAL DEFAULT 0.0,
    
    -- Trade statistics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    
    -- P&L breakdown
    gross_profit REAL DEFAULT 0.0,
    gross_loss REAL DEFAULT 0.0,
    commissions REAL DEFAULT 0.0,
    net_profit REAL DEFAULT 0.0,
    
    -- Strategy breakdown (JSON)
    strategy_performance TEXT,
    
    -- Best/worst trades
    best_trade_pl REAL,
    worst_trade_pl REAL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_account_date ON daily_summaries(account_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_summaries(date);

-- ============================================================================
-- DATA QUALITY TABLE - Track data collection health
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_quality (
    quality_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    
    -- Collection metrics
    trades_collected INTEGER DEFAULT 0,
    snapshots_collected INTEGER DEFAULT 0,
    errors_encountered INTEGER DEFAULT 0,
    
    -- Data freshness
    oldest_trade_age_seconds INTEGER,
    newest_trade_timestamp TIMESTAMP,
    
    -- OANDA API health
    api_response_time_ms REAL,
    api_success_rate REAL,
    
    -- System health
    collector_status TEXT,
    database_size_mb REAL,
    
    -- Metadata
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quality_timestamp ON data_quality(timestamp);

-- ============================================================================
-- VIEWS - Convenient data access
-- ============================================================================

-- Active trades view
CREATE VIEW IF NOT EXISTS v_active_trades AS
SELECT 
    t.*,
    (julianday('now') - julianday(entry_time)) * 86400 AS seconds_open,
    (entry_price - exit_price) * units AS current_pl
FROM trades t
WHERE status = 'open';

-- Daily performance view
CREATE VIEW IF NOT EXISTS v_daily_performance AS
SELECT 
    date(entry_time) AS trade_date,
    account_id,
    account_name,
    strategy_name,
    COUNT(*) AS trades,
    SUM(CASE WHEN net_pl > 0 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN net_pl < 0 THEN 1 ELSE 0 END) AS losses,
    ROUND(AVG(CASE WHEN net_pl > 0 THEN 1.0 ELSE 0.0 END) * 100, 2) AS win_rate,
    ROUND(SUM(net_pl), 2) AS daily_pl,
    ROUND(AVG(net_pl), 2) AS avg_pl
FROM trades
WHERE status = 'closed' AND exit_time IS NOT NULL
GROUP BY date(entry_time), account_id, strategy_name
ORDER BY trade_date DESC;

-- Strategy leaderboard view
CREATE VIEW IF NOT EXISTS v_strategy_leaderboard AS
SELECT 
    strategy_name,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN net_pl > 0 THEN 1 ELSE 0 END) AS wins,
    ROUND(AVG(CASE WHEN net_pl > 0 THEN 1.0 ELSE 0.0 END) * 100, 2) AS win_rate,
    ROUND(SUM(net_pl), 2) AS total_pl,
    ROUND(AVG(net_pl), 2) AS avg_pl,
    ROUND(MAX(net_pl), 2) AS best_trade,
    ROUND(MIN(net_pl), 2) AS worst_trade,
    ROUND(SUM(CASE WHEN net_pl > 0 THEN net_pl ELSE 0 END) / 
          NULLIF(ABS(SUM(CASE WHEN net_pl < 0 THEN net_pl ELSE 0 END)), 0), 2) AS profit_factor
FROM trades
WHERE status = 'closed' AND exit_time IS NOT NULL
GROUP BY strategy_name
ORDER BY total_pl DESC;

-- Recent changes with impact
CREATE VIEW IF NOT EXISTS v_recent_changes_with_impact AS
SELECT 
    sc.*,
    (win_rate_after - win_rate_before) AS win_rate_delta,
    (avg_pl_after - avg_pl_before) AS avg_pl_delta,
    (sharpe_after - sharpe_before) AS sharpe_delta
FROM strategy_changes sc
WHERE impact_analyzed = TRUE
ORDER BY timestamp DESC
LIMIT 50;


