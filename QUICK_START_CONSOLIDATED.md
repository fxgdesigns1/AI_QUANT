# Quick Start Guide - Consolidated Trading System

## Overview

Your trading system now has centralized configuration management, organized navigation, and programmatic strategy control. This guide helps you get started quickly.

---

## Getting Started

### 1. Start the Dashboard

**Local:**
```bash
cd /Users/mac/quant_system_clean/dashboard
python advanced_dashboard.py
```

**Access:** `http://localhost:8080`

**Cloud:**
```
https://ai-quant-trading.uc.r.appspot.com/dashboard
```

---

### 2. Navigate to Features

**New Organization:**
- **🎯 Trading Operations:** Dashboard, Accounts, Positions, Signals, Trade Manager
- **🤖 AI & Intelligence:** AI Copilot, AI Insights, News, Strategy Switcher
- **📊 Analytics & Reports:** Performance, Reports, Strategy Performance
- **⚙️ System & Configuration:** System Status, Configuration

---

### 3. Manage API Keys

**Via Dashboard:**
1. Click **Configuration** (System & Configuration section)
2. Click **API Configuration** panel
3. Click **Edit** on any API key
4. Enter new key
5. Click **Test** to verify
6. Key saves automatically

**Via API:**
```bash
# List all credentials
curl http://localhost:8080/api/config/credentials

# Update OANDA key
curl -X PUT http://localhost:8080/api/config/credentials/OANDA_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"value":"your_key"}'

# Test connection
curl -X POST http://localhost:8080/api/config/test/oanda
```

---

### 4. Manage Strategies

**Via Python:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# List all strategies
strategies = mgr.get_available_strategies()
for s in strategies:
    print(f"{s['name']}: {s['description']}")

# Load a strategy
result = mgr.load_strategy('101-004-30719775-008', 'momentum_trading')
print(result)

# Stop a strategy
result = mgr.stop_strategy('101-004-30719775-005')
print(result)

# Restart
result = mgr.restart_strategy('101-004-30719775-005')
print(result)

# List active
active = mgr.get_active_strategies()
for acc_id, info in active.items():
    print(f"{info['account_name']}: {info['strategy']}")
```

---

### 5. View Account Status

**Via Dashboard:**
1. Click **Accounts** (Trading Operations section)
2. View all 10 accounts
3. See balances, P&L, positions

**Via API:**
```bash
curl http://localhost:8080/api/accounts | jq
```

---

## Common Tasks

### Update OANDA API Key

**Dashboard Method:**
1. Configuration → API Configuration
2. Click Edit on OANDA API Key
3. Paste new key
4. Click Test
5. Verify connection successful

**API Method:**
```bash
curl -X PUT http://localhost:8080/api/config/credentials/OANDA_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"value":"your_new_key"}'
```

---

### Switch Strategy on Account

**Python Method:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()
result = mgr.load_strategy('101-004-30719775-008', 'gold_scalping')
print("Success" if result['success'] else "Failed")
```

**Manual Method:**
1. Edit `accounts.yaml`
2. Find account ID
3. Update strategy name
4. Save file
5. System reloads on next scan (5 min)

---

### Stop Trading on Specific Account

**Python Method:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()
mgr.stop_strategy('101-004-30719775-005')
```

**Manual Method:**
1. Edit `accounts.yaml`
2. Find account
3. Set `active: false`
4. Save file

---

### Check API Usage

**Dashboard:**
1. Configuration → API Configuration
2. Scroll to API Usage Statistics
3. View usage bars and remaining calls

**API:**
```bash
curl http://localhost:8080/api/config/usage | jq
```

---

### Monitor System Health

**Dashboard:**
1. Click System Status (System & Configuration)
2. View component status
3. Check for warnings/errors

**API:**
```bash
curl http://localhost:8080/api/health | jq
```

---

## Troubleshooting

### Dashboard Won't Start

**Solution:**
```bash
# Check if port in use
lsof -i :8080

# Kill process if needed
kill -9 <PID>

# Restart
python dashboard/advanced_dashboard.py
```

---

### Configuration API Not Working

**Solution:**
```bash
# Check if ConfigAPI registered
curl http://localhost:8080/api/config/credentials

# Check logs
tail -f dashboard/logs/*.log

# Verify imports
python -c "from google_cloud_trading_system.src.core.config_api_manager import register_config_api; print('OK')"
```

---

### Strategy Won't Load

**Solution:**
```python
# Check if strategy exists
from google_cloud_trading_system.src.core.strategy_factory import get_strategy_factory

factory = get_strategy_factory()
strategies = factory.list_all_strategies()
print(strategies)

# Check errors
errors = factory.get_load_errors()
print(errors)

# Validate account
from google_cloud_trading_system.src.core.yaml_manager import get_yaml_manager

yaml_mgr = get_yaml_manager()
accounts = yaml_mgr.get_all_accounts()
print([a['id'] for a in accounts])
```

---

## File Locations

### Configuration Files
- `google-cloud-trading-system/accounts.yaml` - Account/strategy mapping
- `google-cloud-trading-system/oanda_config.env` - OANDA credentials
- `google-cloud-trading-system/news_api_config.env` - News APIs
- `google-cloud-trading-system/app.yaml` - Cloud deployment config

### Code Files
- `dashboard/advanced_dashboard.py` - Main dashboard
- `google-cloud-trading-system/main.py` - Cloud system
- `google-cloud-trading-system/src/core/` - Core modules

### Documentation
- `SYSTEM_ARCHITECTURE.md` - Architecture overview
- `API_CONFIGURATION_GUIDE.md` - API management
- `STRATEGY_MANAGEMENT_GUIDE.md` - Strategy operations
- `DEPLOYMENT_CHECKLIST.md` - Deployment procedures

---

## Next Steps

1. **Test Everything:** Run through this quick start
2. **Read Docs:** Check detailed guides
3. **Customize:** Adjust to your needs
4. **Deploy:** Follow deployment checklist
5. **Monitor:** Watch system health

---

**Questions?** Check the documentation files or review code comments.

**Last Updated:** December 2024

