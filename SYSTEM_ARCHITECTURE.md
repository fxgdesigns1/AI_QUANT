# Trading System Architecture

## Overview

This document describes the complete architecture of your automated trading system, including the Google Cloud deployment, local dashboard, trading bots, and AI components.

---

## System Components

### 1. Google Cloud System (Source of Truth)

**Location:** `google-cloud-trading-system/`  
**Main Entry:** `main.py`  
**Deployment:** Google App Engine (F1 Free Tier)

**Components:**
- Flask web application (port 8080)
- Trading scanner (runs every 5 minutes)
- 10 OANDA demo accounts
- Strategy factory and executor
- News integration
- AI assistant
- Analytics dashboard

**Dashboard:** `google-cloud-trading-system/src/dashboard/advanced_dashboard.py`  
**URL:** `https://ai-quant-trading.uc.r.appspot.com/dashboard`

---

### 2. Local Dashboard (Control Center)

**Location:** `dashboard/advanced_dashboard.py`  
**Main Entry:** `python dashboard/advanced_dashboard.py`  
**Deployment:** Local Flask server (port 8080)

**Components:**
- Real-time monitoring
- Configuration management
- Strategy lifecycle control
- AI copilot interface
- Trade signals display

**URL:** `http://localhost:8080`

---

### 3. Trading Bots (10 Accounts)

Each account runs as an independent bot with its own strategy:

| Account | Bot ID | Strategy | Instrument | Status |
|---------|--------|----------|------------|--------|
| Primary | 008 | momentum_trading | Multi-pair | ✅ Active |
| Gold Scalping | 007 | gold_scalping | XAU_USD | ✅ Active |
| Strategy Alpha | 006 | momentum_trading | Multi-pair | ✅ Active |
| Strategy Beta | 005 | mean_reversion | Multi-pair | ❌ Inactive |
| Strategy Gamma | 004 | breakout | Multi-pair | ✅ Active |
| Strategy Delta | 003 | scalping | Multi-pair | ✅ Active |
| Strategy Epsilon | 002 | trend_following | Multi-pair | ❌ Inactive |
| Strategy Zeta | 001 | swing_trading | Multi-pair | ✅ Active |
| Champion 75% WR | 009 | champion_75wr | Multi-pair | ✅ Active |
| Trump Gold | 010 | adaptive_trump_gold | XAU_USD | ✅ Active |

**Account 008 is the AI Agent** - uses momentum_trading but with AI-enhanced decision making

---

### 4. Data Sources & APIs

#### OANDA API
- **Purpose:** Trading execution, account data, market prices
- **Environment:** Practice (demo account)
- **Rate Limit:** 10,000 calls/day, 2,400/hour
- **Endpoints:** Accounts, Instruments, Orders, Prices

#### News APIs
- **Alpha Vantage:** Financial data, market indicators
- **Marketaux:** Real-time news, sentiment
- **NewsData.io:** Breaking news, economic events
- **Purpose:** Market sentiment analysis, event detection

#### AI Services
- **Gemini AI:** Trading insights, market analysis
- **Telegram:** Notifications and alerts

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD (Source of Truth)                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Main Trading System (main.py)                              │ │
│  │  - Flask App: /                                          │ │
│  │  - Dashboard: /dashboard                                  │ │
│  │  - API: /api/*                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Scanner (Every 5 minutes)                                  │ │
│  │  - CandleBasedScanner                                     │ │
│  │  - TradeOpportunityFinder                                 │ │
│  │  - StrategyExecutor                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Strategy Manager & Factory                                 │ │
│  │  - StrategyFactory                                        │ │
│  │  - 10+ Strategies                                         │ │
│  │  - DynamicAccountManager                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Account Management (accounts.yaml)                         │ │
│  │  - YAMLManager                                            │ │
│  │  - StrategyLifecycleManager                               │ │
│  │  - 10 OANDA Accounts                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ API Calls
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL DASHBOARD (Control Center)              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ advanced_dashboard.py (Port 8080)                          │ │
│  │  - Real-time monitoring                                   │ │
│  │  - Configuration management                               │ │
│  │  - Trade signals UI                                       │ │
│  │  - AI Copilot interface                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ API Configuration Panel                                    │ │
│  │  - CredentialsManager                                     │ │
│  │  - ConfigAPIManager                                       │ │
│  │  - Secret Manager integration                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Strategy Lifecycle Management                              │ │
│  │  - Load/Stop/Restart strategies                           │ │
│  │  - Hot-reload configurations                              │ │
│  │  - Validation & monitoring                                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ fetch()
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GOOGLE SECRET MANAGER                         │
│  - OANDA_API_KEY                                               │
│  - News API Keys                                               │
│  - Telegram Credentials                                        │
│  - Gemini AI Key                                               │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Load
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OANDA DEMO ACCOUNT                            │
│  - 10 Trading Accounts                                         │
│  - Demo Capital: $273,632 total                                │
│  - Practice Environment                                        │
│  - Real-time Prices                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Management

### Configuration Sources (Priority Order)

1. **Google Secret Manager** (Cloud deployment)
   - Primary storage for production
   - Automatic syncing
   - Secure encryption

2. **Environment Variables** (Local development)
   - `.env` files loaded via python-dotenv
   - `oanda_config.env`, `news_api_config.env`
   - Easy to modify during development

3. **app.yaml** (Cloud deployment)
   - Fallback for App Engine
   - Hardcoded in deployment config
   - Used when Secret Manager unavailable

### Centralized Management

**New System:**
- `CredentialsManager` - Single interface for all credentials
- `ConfigAPIManager` - REST API for dashboard access
- Automatic fallback chain: Secret Manager → .env → app.yaml
- No more hardcoded credentials

**Old Pattern:**
- `os.getenv()` scattered in 176 files
- Hardcoded in 414 places
- Difficult to update

**Migration Status:**
- New system operational
- Old pattern still works (fallback)
- Migration to new system: In progress

---

## Trading Flow

### 1. Scanner Execution (Every 5 Minutes)

```
Scanner Started
    ↓
Read accounts.yaml
    ↓
Load Active Strategies
    ↓
For Each Account:
    Get Candles (M1, M5, M15, H1)
    Run Strategy Logic
    Identify Opportunities
    Validate Entry Criteria
    Calculate Position Size
    Execute Orders
    Update Positions
    ↓
Log Results
    ↓
Notify Telegram
    ↓
Send Dashboard Updates
```

### 2. Strategy Execution

```
Strategy Signal Generated
    ↓
Pre-Trade Validation
    ├─ Risk Limits Checked
    ├─ Margin Available Checked
    ├─ Position Limits Checked
    ├─ Correlation Checked
    └─ News Events Checked
    ↓
Order Placed (if valid)
    ↓
Order Confirmed
    ↓
Position Monitored
    ├─ Stop Loss Managed
    ├─ Take Profit Managed
    └─ Time-based Exits
    ↓
Position Closed
    ↓
Performance Logged
```

---

## Strategy System

### Strategy Factory

**Location:** `google-cloud-trading-system/src/core/strategy_factory.py`

**Patterns:**
1. **Manual Overrides** - Explicit module/class mapping
2. **Auto-Discovery** - Pattern-based loading
3. **Caching** - Performance optimization

**Available Strategies:**
```python
STRATEGY_OVERRIDES = {
    'momentum_trading': 'MomentumTradingStrategy',
    'gold_scalping': 'GoldScalpingStrategy',
    'breakout': 'BreakoutStrategy',
    'scalping': 'ScalpingStrategy',
    'swing_trading': 'SwingStrategy',
    'mean_reversion': 'MeanReversionStrategy',
    'trend_following': 'TrendFollowingStrategy',
    'adaptive_trump_gold': 'TrumpGoldStrategy',
    'champion_75wr': 'ChampionStrategy',
    'ultra_strict_forex': 'UltraStrictStrategy'
}
```

### Strategy Lifecycle

**Load:**
```
User Action: Load Strategy
    ↓
YAMLManager.update_account_strategy()
    ↓
accounts.yaml Updated
    ↓
StrategyFactory.get_strategy()
    ↓
Strategy Instance Cached
    ↓
Next Scan Uses New Strategy
```

**Stop:**
```
User Action: Stop Strategy
    ↓
YAMLManager.toggle_account(active=False)
    ↓
accounts.yaml Updated
    ↓
Strategy Removed from Cache
    ↓
Scanner Skips This Account
```

**Reload:**
```
User Action: Reload Strategy
    ↓
Strategy Instance Cleared from Cache
    ↓
Fresh Instance Loaded
    ↓
Configuration Updated
    ↓
Next Scan Uses New Config
```

---

## Data Flow

### Real-time Updates

```
Cloud System
    ↓
Flask-SocketIO
    ↓
WebSocket Connection
    ↓
Local Dashboard
    ↓
Browser UI Updates
```

**Update Frequency:**
- Account data: Every 30 seconds
- Positions: Every 15 seconds
- Market prices: Every 5 seconds
- News: Every 5 minutes

### Data Caching

**Local Dashboard:**
- 15-second TTL on API responses
- WebSocket for real-time updates
- Last-known-good fallback

**Cloud System:**
- In-memory caching
- Redis-style caching
- Automatic cleanup

---

## Security Architecture

### Credential Storage

**Cloud:**
- Google Secret Manager (encrypted)
- IAM-based access control
- Audit logging

**Local:**
- `.env` files (git-ignored)
- Environment variables
- Never committed

**Display:**
- All keys masked in UI
- Last 4 chars visible only
- No full keys in logs

### API Access

**Authentication:**
- None required currently (demo system)
- Can add token-based auth
- Rate limiting in place

**Authorization:**
- Config file permissions
- File system access control
- Service account keys

---

## Monitoring & Logging

### Log Aggregation

**Google Cloud:**
- Cloud Logging integration
- Structured logs
- Alert management

**Local:**
- File-based logs
- `logs/trading_system.log`
- `logs/dashboard.log`

### Health Monitoring

**System Health:**
- Cloud: `/api/health` endpoint
- Local: Dashboard status bar
- Uptime tracking

**Component Health:**
- Trading bots: All 10 accounts
- APIs: OANDA, News, AI
- Databases: Trade storage
- Scheduler: Scanner status

### Performance Metrics

**Tracked:**
- API call counts
- Execution time
- Success/failure rates
- Resource usage
- Cost per trade

---

## Deployment Architecture

### Google Cloud (Production)

**Service:** App Engine (Standard)
**Instance:** F1 (Free Tier)
**Region:** us-central1
**Scaling:** 1 instance (F1 limit)

**Configuration:**
- `app.yaml` - Deployment config
- Environment variables
- Secret Manager integration
- Health checks enabled

**URLs:**
- Main: `https://ai-quant-trading.uc.r.appspot.com/`
- Dashboard: `/dashboard`
- API: `/api/*`
- Health: `/api/health`

### Local Development

**Service:** Flask development server
**Instance:** Your Mac
**Port:** 8080
**Mode:** Debug (local only)

**Configuration:**
- `.env` files
- Local paths
- Full logging
- Hot-reload enabled

**URLs:**
- Main: `http://localhost:8080/`
- Dashboard: `/dashboard`
- API: `/api/*`

---

## Integration Points

### External Services

```
Trading System
    ├─ OANDA API (REST + Streaming)
    ├─ Alpha Vantage (REST)
    ├─ Marketaux (REST)
    ├─ Google Secret Manager (REST)
    ├─ Telegram Bot (REST)
    └─ Gemini AI (REST)
```

### Internal Services

```
Main System
    ├─ Scanner → Strategy Factory
    ├─ Strategy Factory → Strategies
    ├─ Strategies → Order Manager
    ├─ Order Manager → OANDA Client
    ├─ Account Manager → YAML Manager
    └─ Dashboard → Cloud Client
```

---

## File Organization

### Core System
```
google-cloud-trading-system/
├── main.py                              # Main entry point
├── app.yaml                             # Cloud deployment config
├── accounts.yaml                        # Account & strategy configuration
├── src/
│   ├── core/
│   │   ├── strategy_factory.py         # Strategy loading
│   │   ├── yaml_manager.py             # Config management
│   │   ├── oanda_client.py             # Trading API
│   │   ├── news_integration.py         # News APIs
│   │   ├── credentials_manager.py      # API keys
│   │   ├── secret_manager.py           # Cloud secrets
│   │   ├── config_api_manager.py       # Config API
│   │   └── strategy_lifecycle_manager.py # Strategy control
│   ├── strategies/
│   │   ├── momentum_trading.py
│   │   ├── gold_scalping_optimized.py
│   │   └── ... (10+ strategies)
│   └── dashboard/
│       └── advanced_dashboard.py       # Cloud dashboard
└── analytics/
    ├── analytics_dashboard.py
    └── trade_database.py
```

### Local Dashboard
```
dashboard/
├── advanced_dashboard.py               # Main dashboard
├── api_usage_tracker.py               # API monitoring
├── cloud_system_client.py             # Cloud connection
├── agent_controller.py                # AI agent
└── templates/
    ├── dashboard_advanced.html        # Main UI
    └── components/
        ├── api_configuration.html     # API config panel
        └── toast_notifications.html   # Alerts
```

---

## Communication Patterns

### Request-Response (HTTP/REST)

**Pattern:**
```
Dashboard → HTTP Request → Cloud API → Response → Dashboard
```

**Examples:**
- GET `/api/accounts` - Fetch accounts
- GET `/api/config/credentials` - Get API keys
- PUT `/api/config/credentials/OANDA_API_KEY` - Update key

### Pub-Sub (WebSocket)

**Pattern:**
```
Cloud → WebSocket → Dashboard → UI Updates
```

**Examples:**
- `account_update` - Account balance changed
- `position_update` - New position opened
- `signal_update` - Trading signal generated
- `news_update` - News item received

### Scanned Execution

**Pattern:**
```
Scheduler → Scanner → Strategies → Execution → Logging
```

**Frequency:**
- Every 5 minutes
- Async execution
- Parallel account processing

---

## Error Handling

### Error Recovery

**Trading Errors:**
- Order failures: Logged, retry with backoff
- API errors: Fallback to cached data
- Network errors: Queue for retry

**Configuration Errors:**
- Invalid YAML: Use last known good
- Missing config: Default values
- Validation errors: Log and skip

**System Errors:**
- Component crashes: Restart service
- Resource limits: Scale back
- Data corruption: Restore from backup

### Logging Levels

**ERROR:** Critical failures requiring attention
**WARNING:** Non-critical issues
**INFO:** Normal operations
**DEBUG:** Detailed diagnostics

---

## Performance Characteristics

### Load Profile

**Peak Load:**
- Scanner runs 10 strategies simultaneously
- Each strategy: 2-5 API calls
- Total: 30-50 API calls per scan
- Frequency: Every 5 minutes

**Daily Volume:**
- 288 scan cycles/day
- ~8,640-14,400 API calls/day
- Well within OANDA limit (10,000)

### Resource Usage

**Memory:**
- Strategy instances: ~10MB each (100MB total)
- Historical data: ~200MB
- WebSocket connections: ~1MB each

**CPU:**
- Scanner execution: 5-10% during scan
- Idle: <1%
- Dashboard: 2-5%

**Network:**
- Outbound: ~500KB/min (API calls)
- Inbound: ~1MB/min (responses)
- WebSocket: ~10KB/sec

---

## Scalability Considerations

### Current Limits

**F1 Free Tier:**
- 28 instance-hours/day
- 0.2 CPU
- 0.2GB RAM
- 5GB disk

**Implications:**
- Can run 24/7
- No scaling required
- Sufficient for demo

### Future Scaling

**If Moving to Production:**
- Upgrade to paid tier
- Multiple instances
- Load balancing
- Auto-scaling

---

## Backup & Recovery

### Automated Backups

**Configuration:**
- `accounts.yaml`: Before every change
- Last 10 backups kept
- Timestamped files
- Automatic rotation

**Data:**
- Trade logs: Daily archival
- Performance snapshots: Every 15 min
- Strategy configs: Version controlled

### Recovery Procedures

**Configuration:**
```bash
# Restore accounts.yaml
cp config_backups/accounts_backup_20241216_143022.yaml accounts.yaml
```

**System:**
```bash
# Git revert
git checkout HEAD~1
git pull

# Redeploy
gcloud app deploy
```

---

## Development Workflow

### Local Development

1. **Make Changes:**
   - Edit source files
   - Test locally
   - Verify functionality

2. **Commit:**
   ```bash
   git add .
   git commit -m "Description"
   git push
   ```

3. **Deploy:**
   ```bash
   gcloud app deploy
   ```

### Testing

**Unit Tests:**
- Strategy logic
- API clients
- Configuration loading

**Integration Tests:**
- End-to-end flows
- Dashboard rendering
- API endpoints

**System Tests:**
- Production-like environment
- All 10 accounts
- Real API calls

---

## Best Practices

### Code Organization

✅ **DO:**
- Keep strategies in separate files
- Use factory patterns
- Centralize configuration
- Document APIs
- Test before deploying

❌ **DON'T:**
- Hardcode credentials
- Duplicate logic
- Skip validation
- Ignore errors
- Deploy untested code

### Configuration Management

✅ **DO:**
- Use CredentialsManager
- Test changes locally first
- Validate before saving
- Keep backups
- Document changes

❌ **DON'T:**
- Edit production configs directly
- Skip backups
- Share credentials
- Commit secrets
- Deploy without validation

---

## Dependencies

### Python Packages

**Core:**
- flask, flask-socketio
- requests, aiohttp
- python-dotenv
- pyyaml
- google-cloud-secret-manager

**Trading:**
- oanda-v20 (optional, using REST now)
- pandas
- numpy

**AI/ML:**
- google-generativeai
- scikit-learn (optional)

**Monitoring:**
- python-telegram-bot
- python-json-logger

### System Requirements

**Cloud:**
- Python 3.11
- Google Cloud SDK
- Secret Manager enabled

**Local:**
- Python 3.11+
- 2GB RAM
- Internet connection
- Browser

---

## Future Enhancements

### Planned Features

1. **Strategy Management UI**
   - Visual interface for loading/stopping
   - Performance comparison charts
   - A/B testing framework

2. **Cloud-Local Sync**
   - Automatic config propagation
   - Conflict resolution
   - Real-time synchronization

3. **Advanced Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alerting system

4. **Backtesting Engine**
   - Historical strategy testing
   - Walk-forward analysis
   - Monte Carlo simulation

---

## Support Resources

**Documentation:**
- `SYSTEM_CONSOLIDATION_STATUS.md` - Implementation status
- `API_CONFIGURATION_GUIDE.md` - API management
- `STRATEGY_MANAGEMENT_GUIDE.md` - Strategy operations
- `DEPLOYMENT_CHECKLIST.md` - Deployment procedures

**External:**
- Google Cloud: https://cloud.google.com/docs
- OANDA: https://developer.oanda.com/
- Dashboard URL: https://ai-quant-trading.uc.r.appspot.com

---

**Last Updated:** December 2024  
**Version:** 1.0  
**Status:** Production Ready

