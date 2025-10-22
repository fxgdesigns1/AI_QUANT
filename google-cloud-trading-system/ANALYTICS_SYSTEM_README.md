# Trading Analytics System - Complete Documentation

## Overview

The Trading Analytics System provides comprehensive trade tracking, performance analysis, and strategy versioning for the trading platform. Since OANDA does not track detailed performance metrics, this system captures every trade, calculates comprehensive metrics, and provides powerful analytics dashboards.

## Key Features

- **✅ Persistent Trade Storage**: SQLite database with all trade details
- **✅ Comprehensive Metrics**: 30+ trading metrics including Sharpe ratio, profit factor, drawdown analysis
- **✅ Strategy Versioning**: Automatic detection and tracking of strategy configuration changes
- **✅ Dual Dashboards**: 
  - Main dashboard (Port 8080) with overview
  - Detailed analytics dashboard (Port 8081) with deep-dive analysis
- **✅ Data Retention**: 90-day detailed retention with automatic archival
- **✅ Real-time Updates**: Metrics update automatically as trades close
- **✅ Export Capabilities**: CSV export for external analysis

## Architecture

```
Trading System (Port 8080)
    ↓
Order Execution → Trade Logger (Intercepts trades)
    ↓
SQLite Database (/data/trading.db)
    ↓
Metrics Calculator → Strategy Metrics
    ↓
Analytics Dashboard (Port 8081)
```

## Components

### 1. Trade Database (`src/analytics/trade_database.py`)

SQLite database with four main tables:

- **trades**: Complete trade records (entry, exit, P&L, duration, etc.)
- **strategy_versions**: Track strategy configuration changes
- **daily_snapshots**: Daily performance summaries per strategy
- **strategy_metrics**: Rolling metrics updated in real-time

### 2. Trade Logger (`src/analytics/trade_logger.py`)

- Automatically logs every trade execution
- Monitors OANDA positions to detect exits
- Calculates realized P&L on trade close
- Updates strategy metrics immediately

### 3. Metrics Calculator (`src/analytics/metrics_calculator.py`)

Calculates comprehensive metrics:

**Standard Metrics:**
- Win Rate, Total P&L, Number of Trades
- Average Win/Loss, Max Drawdown
- Profit Factor, Sharpe Ratio

**Advanced Metrics:**
- Risk/Reward Ratio (actual vs planned)
- Consecutive Win/Loss Streaks
- Time-based analysis (hourly/daily patterns)
- Session performance (London/NY/Asian)
- Sortino Ratio, Calmar Ratio
- Recovery Factor

### 4. Strategy Version Manager (`src/analytics/strategy_version_manager.py`)

- Auto-detects configuration changes in `accounts.yaml`
- Creates version snapshots with full parameters
- Enables version comparison and performance tracking
- Historical analysis of strategy evolution

### 5. Data Archiver (`src/analytics/data_archiver.py`)

- Keeps 90 days of detailed trade data
- Archives older trades to compressed JSON files
- Maintains daily snapshots indefinitely
- Scheduled cleanup at 2 AM London time

### 6. Analytics Dashboard (`src/analytics/analytics_dashboard.py`)

Standalone Flask app on port 8081 with pages:
- **Overview**: All strategies summary
- **Strategy Detail**: Deep dive per strategy
- **Trade History**: Searchable/filterable trade log
- **Comparison**: Side-by-side strategy comparison
- **Version History**: Track strategy changes
- **Charts**: Equity curves, performance charts

## Installation

The analytics system is automatically initialized when you run `main.py`. No additional setup required!

```bash
# Test the analytics system
cd google-cloud-trading-system
python3 test_analytics_system.py

# Start the full system
python3 main.py
```

## Usage

### Accessing Dashboards

**Main Dashboard (Trading Focus):**
- URL: http://localhost:8080
- Real-time trading data
- Quick performance overview
- Link to detailed analytics

**Analytics Dashboard (Analysis Focus):**
- URL: http://localhost:8081
- Deep performance analysis
- Historical data exploration
- Strategy comparison tools

### API Endpoints

**Main Dashboard (Port 8080):**
```
GET /api/analytics/health        - Analytics system status
GET /api/analytics/summary       - Quick metrics summary
```

**Analytics Dashboard (Port 8081):**
```
GET /api/strategies              - List all strategies with metrics
GET /api/strategy/<id>/metrics   - Comprehensive strategy metrics
GET /api/strategy/<id>/trades    - Trade list for strategy
GET /api/strategy/<id>/performance-chart - Time-series data
GET /api/strategy/<id>/versions  - Version history
GET /api/compare?strategies=...  - Compare multiple strategies
GET /api/trades/search           - Search trades with filters
GET /api/export/trades           - Export trades to CSV
GET /api/database/stats          - Database statistics
```

### Trade Logging

Trades are automatically logged when executed through the order manager. No manual intervention required!

```python
# This happens automatically:
# 1. Order executed via multi_account_order_manager
# 2. Trade logger intercepts and logs entry
# 3. System monitors OANDA for exit
# 4. On close: calculates P&L, updates metrics
```

### Viewing Strategy Metrics

```python
from src.analytics.trade_logger import get_trade_logger

# Get strategy summary
logger = get_trade_logger()
summary = logger.get_strategy_summary('momentum_trading')

print(f"Win Rate: {summary['metrics']['win_rate']:.1f}%")
print(f"Total P&L: ${summary['metrics']['total_pnl']:.2f}")
print(f"Profit Factor: {summary['metrics']['profit_factor']:.2f}")
```

### Manual Trade Entry (Historical Import)

```python
from src.analytics.trade_logger import get_trade_logger

logger = get_trade_logger()

# Import historical trades from OANDA
imported = logger.import_historical_trades_from_oanda(
    account_id='101-004-30719775-009',
    strategy_id='gold_scalping',
    oanda_client=client,
    days=7
)
```

## Strategy Versioning

The system automatically detects when you update strategy configurations:

1. **Edit accounts.yaml** or strategy parameters
2. **System auto-detects** changes on next startup
3. **Creates new version** with full config snapshot
4. **New trades** link to new version
5. **Old trades** remain tagged to old version

This enables you to:
- Compare performance before/after changes
- Track strategy evolution over time
- Rollback to previous configurations

## Data Retention

### 90-Day Retention Policy

- **Detailed trades**: Kept for 90 days
- **After 90 days**: Archived to compressed JSON
- **Daily snapshots**: Kept forever
- **Strategy metrics**: Kept forever

### Archival Process

Runs automatically at 2 AM London time:
```
1. Identify trades > 90 days old
2. Group by month (e.g., 2025-09)
3. Compress to /data/archives/trades_2025-09.json.gz
4. Delete from database
5. Vacuum database to reclaim space
```

### Archive Management

```python
from src.analytics.data_archiver import get_data_archiver

archiver = get_data_archiver()

# List archives
archives = archiver.list_archives()

# Restore from archive
result = archiver.restore_trades_from_archive('2025-09')

# Export archive to CSV
csv_path = archiver.export_archive_to_csv('2025-09')

# Get stats
stats = archiver.get_archive_stats()
```

## Database Management

### Backup Database

```bash
# Simple file copy (database is single file)
cp /Users/mac/quant_system_clean/google-cloud-trading-system/data/trading.db \
   /backup/location/trading_backup_$(date +%Y%m%d).db
```

### Database Statistics

```python
from src.analytics.trade_database import get_trade_database

db = get_trade_database()
stats = db.get_database_stats()

print(f"Total trades: {stats['total_trades']}")
print(f"Open trades: {stats['open_trades']}")
print(f"Database size: {stats['db_size_mb']:.2f} MB")
print(f"Earliest trade: {stats['earliest_trade']}")
print(f"Latest trade: {stats['latest_trade']}")
```

### Optimize Database

```python
# Reclaim space after archival
db.vacuum_database()
```

## Metrics Reference

### Win Rate Metrics
- `win_rate`: Percentage of winning trades
- `wins`: Number of winning trades
- `losses`: Number of losing trades

### P&L Metrics
- `total_pnl`: Total realized profit/loss
- `avg_win`: Average winning trade amount
- `avg_loss`: Average losing trade amount
- `largest_win`: Single largest win
- `largest_loss`: Single largest loss

### Risk Metrics
- `max_drawdown`: Maximum equity drawdown
- `current_drawdown`: Current drawdown from peak
- `avg_drawdown`: Average drawdown amount
- `risk_reward_ratio`: Average RR ratio

### Performance Ratios
- `profit_factor`: Total wins / Total losses
- `sharpe_ratio`: Risk-adjusted returns
- `sortino_ratio`: Downside risk-adjusted returns
- `calmar_ratio`: Return / Max drawdown
- `recovery_factor`: Net profit / Max drawdown

### Streak Metrics
- `consecutive_wins`: Current win streak
- `consecutive_losses`: Current loss streak
- `max_consecutive_wins`: Longest win streak
- `max_consecutive_losses`: Longest loss streak

### Time-based Metrics
- `avg_trade_duration_seconds`: Average trade duration
- `best_hour`: Most profitable hour of day
- `worst_hour`: Least profitable hour of day
- `london_session_pnl`: P&L during London session
- `ny_session_pnl`: P&L during NY session
- `asian_session_pnl`: P&L during Asian session

## Troubleshooting

### Analytics Not Appearing

1. Check if analytics enabled:
```python
# In main.py
print(f"Analytics enabled: {ANALYTICS_ENABLED}")
```

2. Check database:
```bash
ls -lh /Users/mac/quant_system_clean/google-cloud-trading-system/data/trading.db
```

3. Check analytics dashboard:
```bash
curl http://localhost:8081/api/health
```

### Trades Not Being Logged

1. Verify order manager integration:
```python
# Check in multi_account_order_manager.py
print(f"Trade logging enabled: {TRADE_LOGGING_ENABLED}")
```

2. Check trade logger status:
```python
from src.analytics.trade_logger import get_trade_logger
logger = get_trade_logger()
print(f"Open positions tracked: {len(logger._open_positions)}")
```

### Database Growing Too Large

1. Check current size:
```python
stats = db.get_database_stats()
print(f"DB size: {stats['db_size_mb']:.2f} MB")
```

2. Manually trigger archival:
```python
from src.analytics.data_archiver import get_data_archiver
archiver = get_data_archiver()
result = archiver.archive_old_trades(days=90)
```

3. Vacuum database:
```python
db.vacuum_database()
```

## Performance Considerations

- **Database queries**: Optimized with indexes
- **Metrics caching**: 60-second cache for calculated metrics
- **Background processing**: Analytics run in separate thread
- **Memory usage**: ~50-100 MB for analytics components
- **Disk usage**: ~1 MB per 1000 trades

## Maintenance Schedule

**Daily (2 AM London):**
- Archive trades > 90 days
- Generate daily snapshots
- Cleanup and reporting

**Weekly (Recommended):**
- Backup trading.db file
- Review database size
- Check archive integrity

**Monthly (Recommended):**
- Review archive stats
- Vacuum database
- Verify metrics accuracy

## Security Notes

- Database file permissions: 644 (read/write owner only)
- No external network access required
- Analytics dashboard: localhost only by default
- Archive files encrypted at rest (OS level)

## Integration with Existing Code

The analytics system is designed to be **non-invasive**:

- ✅ Doesn't modify existing trade logic
- ✅ Doesn't affect trading performance
- ✅ Fails gracefully if disabled
- ✅ Can be disabled with flag: `ANALYTICS_ENABLED = False`

## Future Enhancements

Potential additions:
- Real-time WebSocket updates to analytics dashboard
- Machine learning performance predictions
- Automated strategy optimization suggestions
- Cloud database sync for multi-instance deployments
- Mobile app for analytics viewing
- Slack/Discord integration for alerts

## Support

For issues or questions:
1. Check logs: `/Users/mac/quant_system_clean/google-cloud-trading-system/logs/`
2. Run test: `python3 test_analytics_system.py`
3. Check database: Review trading.db with SQLite browser

## Files Created by Analytics System

```
google-cloud-trading-system/
├── data/
│   ├── trading.db                    # Main SQLite database
│   └── archives/                     # Archived trades
│       └── trades_YYYY-MM.json.gz    # Monthly archives
├── src/
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── trade_database.py         # Database layer
│   │   ├── trade_logger.py           # Trade interceptor
│   │   ├── metrics_calculator.py     # Metrics engine
│   │   ├── strategy_version_manager.py # Version tracking
│   │   ├── data_archiver.py          # Retention management
│   │   └── analytics_dashboard.py    # Dashboard app
│   └── templates/
│       └── analytics/                # Dashboard HTML templates
│           ├── overview.html
│           ├── strategy_detail.html
│           ├── trade_history.html
│           ├── comparison.html
│           ├── charts.html
│           └── version_history.html
├── test_analytics_system.py          # Test script
└── ANALYTICS_SYSTEM_README.md        # This file
```

## Conclusion

The Trading Analytics System provides enterprise-grade tracking and analysis capabilities, filling the gap left by OANDA's limited metrics. With automatic trade logging, comprehensive metrics calculation, and powerful visualization tools, you can now make data-driven decisions about strategy performance and optimization.

**System Status:** ✅ Fully Operational and Production-Ready

