# Multi-Strategy Testing Framework

## 🎯 Overview

The Multi-Strategy Testing Framework is a comprehensive system designed to test multiple trading strategies simultaneously while collecting valuable data to improve both live trading performance and backtesting accuracy. This framework builds upon the existing Google Cloud trading system without disrupting current functionality.

## 🏗️ Architecture

### Core Components

1. **Strategy Manager** (`src/core/strategy_manager.py`)
   - Central coordinator for all strategies
   - Dynamic strategy assignment to accounts
   - Performance monitoring and comparison
   - Risk management per strategy

2. **Strategy Executor** (`src/core/strategy_executor.py`)
   - Independent execution engines
   - Isolated risk management
   - Real-time signal processing
   - Order management per strategy

3. **Data Collector** (`src/core/data_collector.py`)
   - Live market data capture
   - Trade execution logging
   - Performance metrics tracking
   - Event correlation system

4. **Backtesting Integration** (`src/core/backtesting_integration.py`)
   - Live-to-Backtest bridge
   - Data export pipeline
   - Strategy optimization
   - Performance analysis

5. **Performance Monitor** (`src/core/performance_monitor.py`)
   - Real-time performance monitoring
   - Strategy comparison tools
   - Alert system
   - Comprehensive analytics

6. **Multi-Strategy Framework** (`src/core/multi_strategy_framework.py`)
   - Main integration class
   - System health monitoring
   - Component coordination
   - Framework lifecycle management

## 📊 Features

### Multi-Strategy Testing
- **Strategy Isolation**: Each strategy runs on dedicated accounts
- **Performance Comparison**: Real-time comparison of strategy performance
- **Dynamic Assignment**: Strategies can be reassigned based on performance
- **Risk Management**: Independent risk controls per strategy

### Data Collection
- **Market Data**: OHLCV, volume, spread, volatility
- **Trade Data**: Entry/exit prices, execution times, P&L
- **Signal Data**: Signal generation, confidence levels, execution rates
- **Performance Data**: Returns, drawdowns, Sharpe ratios
- **News Data**: Market sentiment and economic events

### Backtesting Integration
- **Live Data Export**: Automatic export of live trading data
- **Historical Reconstruction**: Recreate market conditions
- **Strategy Optimization**: Parameter optimization using live data
- **Performance Attribution**: Detailed performance analysis

### Performance Monitoring
- **Real-time Metrics**: Live performance tracking
- **Alert System**: Automated alerts for performance issues
- **Strategy Rankings**: Performance-based strategy ranking
- **Risk Monitoring**: Real-time risk assessment

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- OANDA API credentials
- SQLite3 (for data storage)
- Required Python packages (see requirements.txt)

### Installation
1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure OANDA credentials in environment variables:
   ```bash
   export OANDA_API_KEY="your_api_key"
   export OANDA_ACCOUNT_ID="your_account_id"
   export OANDA_ENVIRONMENT="practice"  # or "live"
   ```

3. Run the test suite to verify installation:
   ```bash
   python test_multi_strategy_framework.py
   ```

### Starting the Framework
The framework is automatically initialized when the main dashboard starts. You can also start it manually:

```python
from src.core.multi_strategy_framework import get_multi_strategy_framework

framework = get_multi_strategy_framework()
framework.start_framework()
```

## 📈 Usage

### Dashboard Integration
The framework is fully integrated into the existing dashboard with new API endpoints:

- `/api/multi-strategy/status` - Framework status
- `/api/multi-strategy/dashboard` - Comprehensive dashboard data
- `/api/multi-strategy/performance` - Strategy performance comparison
- `/api/multi-strategy/start` - Start framework
- `/api/multi-strategy/stop` - Stop framework
- `/api/multi-strategy/export` - Export framework data

### Strategy Management
```python
# Get strategy manager
strategy_manager = get_strategy_manager()

# Start multi-strategy testing
strategy_manager.start_multi_strategy_testing()

# Get performance comparison
comparison = strategy_manager.get_strategy_performance_comparison()

# Pause/Resume strategies
strategy_manager.pause_strategy('ULTRA_FOREX')
strategy_manager.resume_strategy('ULTRA_FOREX')
```

### Data Collection
```python
# Get data collector
data_collector = get_data_collector()

# Start data collection
data_collector.start_collection()

# Export data for backtesting
filename = data_collector.export_data_for_backtesting(
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now(),
    output_format="json"
)
```

### Performance Monitoring
```python
# Get performance monitor
performance_monitor = get_performance_monitor()

# Start monitoring
performance_monitor.start_monitoring()

# Get dashboard data
dashboard_data = performance_monitor.get_performance_dashboard_data()

# Export performance report
report = performance_monitor.export_performance_report(days=7)
```

## 🔧 Configuration

### Strategy Configuration
Strategies are configured in the Strategy Manager with the following parameters:

```python
StrategyConfig(
    strategy_id='ULTRA_FOREX',
    strategy_name='Ultra Strict Forex',
    account_id='account_123',
    instruments=['EUR_USD', 'GBP_USD', 'USD_JPY'],
    max_positions=5,
    max_daily_trades=50,
    risk_per_trade=0.002,  # 0.2%
    stop_loss_pct=0.002,
    take_profit_pct=0.003,
    performance_threshold=0.02  # 2% monthly return
)
```

### Risk Management
Each strategy has independent risk controls:

- **Position Size Limits**: Maximum position size per trade
- **Daily Loss Limits**: Maximum daily loss per strategy
- **Margin Usage Limits**: Maximum margin utilization
- **Trade Frequency Limits**: Maximum trades per hour/day
- **Confidence Thresholds**: Minimum signal confidence for execution

### Alert Configuration
Performance alerts can be configured for various metrics:

```python
PerformanceAlert(
    metric=PerformanceMetric.DRAWDOWN,
    threshold=5.0,  # 5% drawdown
    comparison='above',
    alert_level=AlertLevel.WARNING,
    message="Strategy drawdown exceeds 5%"
)
```

## 📊 Data Storage

### Database Schema
The framework uses SQLite3 for data storage with the following tables:

- `market_data` - OHLCV and market information
- `trade_data` - Trade execution records
- `signal_data` - Signal generation and execution
- `performance_data` - Performance metrics over time
- `news_data` - Market news and sentiment

### Export Formats
Data can be exported in multiple formats:

- **JSON**: Comprehensive data export with metadata
- **CSV**: Tabular data for analysis tools
- **Parquet**: Efficient storage for large datasets
- **Pickle**: Python-native serialization

## 🔍 Monitoring and Alerts

### Real-time Monitoring
The framework provides comprehensive monitoring:

- **System Health**: Component status and connectivity
- **Performance Metrics**: Returns, drawdowns, Sharpe ratios
- **Risk Metrics**: Margin usage, position exposure
- **Execution Metrics**: Signal generation and execution rates

### Alert System
Automated alerts for:

- **Performance Issues**: High drawdowns, poor returns
- **Risk Violations**: Margin limits, position limits
- **System Issues**: Component failures, connectivity problems
- **Opportunities**: High-performing strategies, optimization opportunities

### Telegram Integration
All alerts are sent via Telegram (when configured):

```
🚨 Performance Alert

📊 Metric: Drawdown
📈 Current Value: 6.2%
🎯 Threshold: 5.0%
📝 Strategy drawdown exceeds 5%
⏰ Time: 14:30:25
```

## 🧪 Testing

### Test Suite
Run the comprehensive test suite:

```bash
python test_multi_strategy_framework.py
```

The test suite validates:
- Framework initialization
- Component integration
- Data collection functionality
- Performance monitoring
- Backtesting integration
- API endpoints

### Manual Testing
Individual components can be tested:

```python
# Test strategy manager
strategy_manager = get_strategy_manager()
status = strategy_manager.get_system_status()

# Test data collector
data_collector = get_data_collector()
collection_status = data_collector.get_collection_status()

# Test performance monitor
performance_monitor = get_performance_monitor()
dashboard_data = performance_monitor.get_performance_dashboard_data()
```

## 📈 Performance Optimization

### Strategy Optimization
The framework includes built-in optimization capabilities:

```python
# Optimize strategy parameters
optimization_result = backtesting_integration.optimize_strategy_parameters(
    strategy_id='ULTRA_FOREX',
    parameter_ranges={
        'stop_loss_pct': (0.001, 0.005),
        'take_profit_pct': (0.002, 0.008),
        'risk_per_trade': (0.001, 0.005)
    },
    optimization_method='grid_search'
)
```

### Performance Analysis
Comprehensive performance analysis tools:

- **Return Analysis**: Monthly, annual, and total returns
- **Risk Analysis**: Drawdowns, volatility, Sharpe ratios
- **Trade Analysis**: Win rates, profit factors, trade duration
- **Correlation Analysis**: Strategy correlation and diversification

## 🔒 Security and Risk Management

### Account Isolation
- Each strategy runs on dedicated accounts
- Independent risk controls per account
- No cross-contamination between strategies

### Risk Controls
- **Position Limits**: Maximum positions per strategy
- **Loss Limits**: Daily and total loss limits
- **Margin Limits**: Maximum margin utilization
- **Emergency Stops**: Immediate halt capabilities

### Data Security
- **Local Storage**: All data stored locally
- **Encryption**: Sensitive data encrypted at rest
- **Access Control**: Role-based access to framework components

## 🚀 Deployment

### Google Cloud Deployment
The framework is designed for Google Cloud deployment:

1. **App Engine**: Main dashboard and API
2. **Cloud SQL**: Database storage (optional upgrade)
3. **Cloud Storage**: Data export and backup
4. **Cloud Functions**: Automated tasks and alerts

### Environment Variables
Required environment variables:

```bash
# OANDA Configuration
OANDA_API_KEY=your_api_key
OANDA_ACCOUNT_ID=your_account_id
OANDA_ENVIRONMENT=practice

# Telegram Configuration (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Framework Configuration
FRAMEWORK_AUTO_START=true
FRAMEWORK_EXPORT_INTERVAL=24
FRAMEWORK_MONITORING_INTERVAL=30
```

## 📚 API Reference

### Strategy Manager API
- `start_multi_strategy_testing()` - Start framework
- `stop_multi_strategy_testing()` - Stop framework
- `get_strategy_performance_comparison()` - Get performance data
- `pause_strategy(strategy_id)` - Pause strategy
- `resume_strategy(strategy_id)` - Resume strategy

### Data Collector API
- `start_collection()` - Start data collection
- `stop_collection()` - Stop data collection
- `export_data_for_backtesting()` - Export data
- `get_collection_status()` - Get collection status

### Performance Monitor API
- `start_monitoring()` - Start performance monitoring
- `stop_monitoring()` - Stop monitoring
- `get_performance_dashboard_data()` - Get dashboard data
- `export_performance_report()` - Export performance report

### Backtesting Integration API
- `export_live_data_for_backtesting()` - Export live data
- `run_strategy_backtest()` - Run backtest
- `optimize_strategy_parameters()` - Optimize parameters
- `compare_strategy_performance()` - Compare strategies

## 🐛 Troubleshooting

### Common Issues

1. **Framework Not Starting**
   - Check OANDA credentials
   - Verify account access
   - Check system health status

2. **Data Collection Issues**
   - Verify database permissions
   - Check disk space
   - Review collection logs

3. **Performance Monitoring Issues**
   - Check component connectivity
   - Verify alert configuration
   - Review monitoring logs

### Debug Mode
Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks
Monitor system health:

```python
framework = get_multi_strategy_framework()
status = framework.get_framework_status()
health = status['system_health']
```

## 📝 Changelog

### Version 1.0.0 (2024-12-21)
- Initial release of Multi-Strategy Testing Framework
- Strategy Manager with dynamic assignment
- Independent Strategy Executors
- Comprehensive Data Collector
- Backtesting Integration
- Performance Monitor with alerts
- Complete framework integration
- Dashboard API integration
- Comprehensive test suite

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Run test suite
5. Submit pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document all functions
- Include unit tests

### Testing Requirements
- All new code must include tests
- Test coverage should be >90%
- Integration tests required for new components

## 📄 License

This project is part of the Google Cloud Trading System and follows the same licensing terms.

## 🆘 Support

For support and questions:

1. Check the troubleshooting section
2. Review the API documentation
3. Run the test suite for diagnostics
4. Check system logs for error details

---

**Note**: This framework is designed to work alongside the existing Google Cloud trading system without disrupting current functionality. All existing features remain fully functional while providing enhanced multi-strategy testing capabilities.

