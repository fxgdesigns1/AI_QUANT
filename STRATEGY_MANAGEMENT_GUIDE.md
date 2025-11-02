# Strategy Management Guide

## Overview

Your trading system can now manage strategies across all 10 accounts programmatically. Load, stop, restart, and switch strategies without editing configuration files or restarting the system.

---

## Current Architecture

### Account-Strategy Mapping

You have **10 trading accounts** managed in `accounts.yaml`:

| Account ID | Name | Strategy | Active |
|------------|------|----------|--------|
| 101-004-30719775-008 | Primary Trading Account | momentum_trading | ✅ Yes |
| 101-004-30719775-007 | Gold Scalping Account | gold_scalping | ✅ Yes |
| 101-004-30719775-006 | Strategy Alpha Account | momentum_trading | ✅ Yes |
| 101-004-30719775-005 | Strategy Beta Account | mean_reversion | ❌ No |
| 101-004-30719775-004 | Strategy Gamma Account | breakout | ✅ Yes |
| 101-004-30719775-003 | Strategy Delta Account | scalping | ✅ Yes |
| 101-004-30719775-002 | Strategy Epsilon Account | trend_following | ❌ No |
| 101-004-30719775-001 | Strategy Zeta (SWING) | swing_trading | ✅ Yes |
| 101-004-30719775-009 | Champion Strategy | champion_75wr | ✅ Yes |
| 101-004-30719775-010 | Gold Strategy | adaptive_trump_gold | ✅ Yes |

**Note:** Account 008 is your AI agent (runs momentum_trading by default)

---

## Available Strategies

### Currently Implemented

| Strategy | Description | Best For |
|----------|-------------|----------|
| **momentum_trading** | Follows strong trends with MA crossover | EUR/USD, GBP/USD, USD/JPY |
| **gold_scalping** | High-frequency Gold trading | XAU/USD |
| **ultra_strict_forex** | Very selective entries | Major forex pairs |
| **breakout** | Trades breakout patterns | EUR/USD, GBP/USD, USD/JPY |
| **scalping** | Quick in-and-out trades | All major pairs |
| **swing_trading** | Medium-term holds | EUR/USD, GBP/USD, XAU/USD |
| **mean_reversion** | Fades extreme moves | Range-bound markets |
| **trend_following** | Follows trends with stops | Strong trending pairs |
| **adaptive_trump_gold** | Trump-inspired Gold strategy | XAU/USD |
| **champion_75wr** | High win-rate strategy | EUR/USD, GBP/USD, USD/JPY |

---

## Basic Operations

### 1. View Current Strategies

**Python Code:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Get all active strategies
active = mgr.get_active_strategies()
for account_id, info in active.items():
    print(f"{info['account_name']}: {info['strategy']}")
```

**Expected Output:**
```
Primary Trading Account: momentum_trading
Gold Scalping Account: gold_scalping
Strategy Alpha Account: momentum_trading
Strategy Gamma Account: breakout
Strategy Delta Account: scalping
Strategy Zeta (SWING): swing_trading
Champion Strategy: champion_75wr
Gold Strategy: adaptive_trump_gold
```

---

### 2. List Available Strategies

**Python Code:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Get all available strategies
strategies = mgr.get_available_strategies()
for strategy in strategies:
    print(f"{strategy['display_name']}: {strategy['description']}")
    print(f"  Best for: {strategy['best_for']}")
    print()
```

---

### 3. Load a Strategy on an Account

**Python Code:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Load momentum_trading on account 008
result = mgr.load_strategy(
    account_id='101-004-30719775-008',
    strategy_name='momentum_trading',
    validate=True
)

if result['success']:
    print(f"✅ {result['message']}")
else:
    print(f"❌ Error: {result['error']}")
```

**What Happens:**
1. Validates strategy compatibility with account instruments
2. Updates `accounts.yaml` with new strategy
3. Attempts to instantiate strategy instance
4. Returns success/failure with details

---

### 4. Stop a Strategy

**Python Code:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Stop strategy on account 005
result = mgr.stop_strategy('101-004-30719775-005')

if result['success']:
    print(f"✅ {result['message']}")
    print("Account is now inactive - will not trade")
```

**What Happens:**
1. Sets account's `active: false` in YAML
2. Removes from active strategies cache
3. Next scan cycle will skip this account

---

### 5. Restart a Stopped Strategy

**Python Code:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Restart account 002
result = mgr.restart_strategy('101-004-30719775-002')

if result['success']:
    print(f"✅ {result['message']}")
    print("Account will trade on next scan")
```

---

### 6. Hot-Reload Strategy Configuration

**Python Code:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Reload strategy without stopping
result = mgr.reload_strategy('101-004-30719775-008', 'momentum_trading')

if result['success']:
    print(f"✅ {result['message']}")
    print("New configuration loaded immediately")
```

**Use Cases:**
- Update risk parameters
- Adjust entry/exit logic
- Change indicator settings
- Tune performance parameters

---

## Advanced Operations

### Strategy Validation

**Check Compatibility:**
```python
from google_cloud_trading_system.src.core.yaml_manager import get_yaml_manager

yaml_mgr = get_yaml_manager()

# Validate if momentum_trading works on account 007
valid = yaml_mgr.validate_strategy_instruments(
    account_id='101-004-30719775-007',
    strategy_name='momentum_trading'
)

print("Compatible" if valid else "Incompatible")
```

---

### Batch Operations

**Load Same Strategy on Multiple Accounts:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Load momentum on all active accounts
accounts = ['101-004-30719775-008', '101-004-30719775-006']

for account_id in accounts:
    result = mgr.load_strategy(account_id, 'momentum_trading')
    status = "✅" if result['success'] else "❌"
    print(f"{status} {account_id}: {result.get('message', result.get('error'))}")
```

---

### Strategy Switching

**Switch from One Strategy to Another:**
```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# Switch account 004 from breakout to scalping
result = mgr.load_strategy(
    account_id='101-004-30719775-004',
    strategy_name='scalping',
    validate=True
)

if result['success']:
    print("✅ Strategy switched successfully")
else:
    print(f"❌ Switch failed: {result['error']}")
```

---

## Important Notes

### Automatic Backups

**Before Every Change:**
- YAML file is automatically backed up
- Timestamp included: `accounts_backup_20241216_143022.yaml`
- Last 10 backups kept automatically
- Located in `config_backups/` directory

**Recovery:**
```python
from google_cloud_trading_system.src.core.yaml_manager import get_yaml_manager

yaml_mgr = get_yaml_manager()

# Read backup
import yaml
with open('config_backups/accounts_backup_20241216_143022.yaml') as f:
    backup = yaml.safe_load(f)

# Restore
yaml_mgr.write_config(backup)
```

---

### Hot Reloading

**What Happens Automatically:**

1. **Immediate:**
   - YAML file updated
   - Strategy instance reloaded
   - Configuration cached

2. **Next Scan Cycle (5 minutes):**
   - Trading scanner picks up new config
   - New signals generated with updated parameters
   - Old positions continue running

3. **Risk:**
   - Strategy changes don't affect open trades
   - Only new trades use new configuration
   - Gradual transition, not instant

---

## API Endpoints (Future)

Once dashboard UI is implemented:

```
POST /api/strategies/load
{
  "account_id": "101-004-30719775-008",
  "strategy_name": "momentum_trading"
}

POST /api/strategies/stop
{
  "account_id": "101-004-30719775-005"
}

POST /api/strategies/reload
{
  "account_id": "101-004-30719775-008"
}

GET /api/strategies/available
→ Returns list of all strategies

GET /api/strategies/active
→ Returns active strategies per account
```

---

## Best Practices

### DO ✅

- ✅ Validate strategies before loading
- ✅ Test on one account first
- ✅ Monitor performance after changes
- ✅ Keep backups before major switches
- ✅ Document why changes were made

### DON'T ❌

- ❌ Switch all accounts at once
- ❌ Load untested strategies
- ❌ Ignore validation warnings
- ❌ Delete backups manually
- ❌ Change during active trading hours

---

## Troubleshooting

### Issue: "Strategy validation failed"

**Cause:** Strategy incompatible with account instruments

**Solution:**
1. Check account's instruments in accounts.yaml
2. Verify strategy works with those instruments
3. Consider switching strategy type

**Example:**
```
Account 007 has: XAU_USD
Strategy: momentum_trading (best for EUR/USD, GBP/USD)
→ Consider: gold_scalping or adaptive_trump_gold
```

---

### Issue: "Strategy instantiation failed"

**Cause:** Code error in strategy module

**Solution:**
1. Check logs for specific error
2. Verify strategy module exists
3. Check imports are correct
4. Test strategy isolation

**Debug:**
```python
from google_cloud_trading_system.src.core.strategy_factory import get_strategy_factory

factory = get_strategy_factory()
errors = factory.get_load_errors()
print(errors)  # Shows what went wrong
```

---

### Issue: "Account not found"

**Cause:** Invalid account ID

**Solution:**
1. List all accounts to get valid IDs
2. Verify ID format: `101-004-30719775-XXX`
3. Check accounts.yaml structure

**Verify:**
```python
from google_cloud_trading_system.src.core.yaml_manager import get_yaml_manager

yaml_mgr = get_yaml_manager()
accounts = yaml_mgr.get_all_accounts()

for acc in accounts:
    print(f"ID: {acc['id']}, Name: {acc.get('name')}")
```

---

## Strategy Selection Guide

### Choosing the Right Strategy

**For Trending Markets:**
- `momentum_trading`
- `trend_following`
- `breakout`

**For Range-Bound Markets:**
- `mean_reversion`
- `scalping`

**For Gold Trading:**
- `gold_scalping`
- `adaptive_trump_gold`

**For Conservative Trading:**
- `ultra_strict_forex`
- `swing_trading`

**For Aggressive Trading:**
- `scalping`
- `breakout`

---

## Performance Monitoring

**Track Strategy Performance:**

```python
# Get active strategies
active = mgr.get_active_strategies()

# For each account, check:
# 1. Win rate
# 2. Avg profit per trade
# 3. Drawdown
# 4. Daily P&L

# Compare strategies over time
# Switch underperformers
# Double down on winners
```

**Dashboard Integration:**
- View in Performance Monitoring section
- Strategy comparison charts
- Historical analysis
- Recommendations

---

## Migration Example

**Switching All Accounts to New Strategy:**

```python
from google_cloud_trading_system.src.core.strategy_lifecycle_manager import get_strategy_lifecycle_manager

mgr = get_strategy_lifecycle_manager()

# 1. Back up current state
current = mgr.get_active_strategies()

# 2. Load new strategy on test account first
result = mgr.load_strategy('101-004-30719775-008', 'momentum_trading')
assert result['success'], "Test failed"

# 3. Monitor for 24-48 hours

# 4. If successful, roll out to other accounts
if test_successful:
    for account_id in other_accounts:
        mgr.load_strategy(account_id, 'momentum_trading')
```

---

## Support

**Resources:**
- Check `SYSTEM_CONSOLIDATION_STATUS.md` for status
- Review `accounts.yaml` for current configuration
- Check logs: `tail -f logs/*.log`
- Test individual components before production

**Common Questions:**

**Q: Can I run different strategies on the same pair?**  
A: Yes, each account can have different strategy for same instrument.

**Q: How long before changes take effect?**  
A: YAML updates immediately, trading changes on next scan (5 min).

**Q: Will existing trades be affected?**  
A: No, only new trades use new strategy configuration.

**Q: Can I test strategies without deploying?**  
A: Yes, use demo accounts. Account 001-005 are good for testing.

**Q: What if a strategy fails to load?**  
A: Check logs, verify module exists, test in isolation.

---

**Last Updated:** December 2024  
**Version:** 1.0  
**Status:** Production Ready

