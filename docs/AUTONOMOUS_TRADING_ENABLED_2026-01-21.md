# Autonomous Trading Enabled - 2026-01-21

## ✅ Status: READY FOR AUTONOMOUS TRADING

### Control Verified
- ✅ **All 6 accounts tested** - Trades executed successfully on all accounts
- ✅ **API credentials working** - Direct OANDA API access confirmed
- ✅ **Execution capability proven** - Manual trades placed successfully

### Configuration Status

**Environment Variables (from `/etc/ai-quant/.env`):**
- ✅ `TRADING_MODE=paper` (safe mode)
- ✅ `PAPER_EXECUTION_ENABLED=true` (paper trading enabled)
- ✅ `EXECUTION_ENABLED=true` (execution enabled)
- ✅ `EXECUTION_UNLOCK_OK=true` (legacy compatibility)
- ✅ `KILL_SWITCH=false` (not blocking)

**Execution Guard:**
- Mode: `paper`
- Status: Ready (requires runner to be active)

### What's Needed for Autonomous Trading

**1. Control Plane (API/Dashboard):**
- ✅ Running via `ai-quant-control-plane.service`
- ✅ Environment variables loaded correctly

**2. Runner (Trading Engine):**
- ⚠️ **Runner must be started** - This is what executes trades autonomously
- Service: `ai-quant-runner.service` (if configured)
- Entrypoint: `python -m runner_src.runner.main`

**How Runner Works:**
- Loads accounts from OANDA
- Polls market prices every 30 seconds (configurable)
- Scans for trading signals using active strategies
- **Automatically executes trades** when:
  - Execution guard allows (`PAPER_EXECUTION_ENABLED=true` ✅)
  - All safety gates pass:
    - ✅ Session active (London/NY/Asia)
    - ✅ Market regime = TRENDING (or policy allows)
    - ✅ No news embargo active
    - ✅ Daily/Weekly bias aligned (roadmap aligned)

### Safety Gates

The system will **only trade** when all conditions are met:
1. **Execution Enabled** ✅ (already set)
2. **Market Session Active** - London/NY/Asia hours
3. **Market Regime** - TRENDING (or policy configured to allow RANGING/CHOPPY)
4. **News Check** - No high-impact news embargo (60min before/after)
5. **Roadmap Alignment** - Daily and Weekly bias must agree
6. **Strategy Signals** - Must generate valid trading signals
7. **Risk Limits** - Within daily trade limits per account

### To Enable Autonomous Trading NOW:

**Option 1: Start Runner Service (if configured)**
```bash
sudo systemctl start ai-quant-runner.service
sudo systemctl enable ai-quant-runner.service  # Auto-start on boot
```

**Option 2: Start Runner Manually**
```bash
cd /opt/ai-quant
source .venv/bin/activate
python -m runner_src.runner.main
```

**Option 3: Background Runner**
```bash
cd /opt/ai-quant
RUNNER_BG=1 bash scripts/start_runner_clean.sh
```

### Monitoring Autonomous Trades

**Check Runner Status:**
```bash
# Via API
curl http://127.0.0.1:8787/api/status

# Check logs
sudo journalctl -u ai-quant-runner.service -f

# Or if running manually
tail -f logs/runner.log
```

**What to Watch:**
- `last_scan_at` - Last signal scan timestamp
- `last_signals_generated` - Number of signals found
- `last_executed_count` - Number of trades executed
- `execution_guard.allowed` - Should be `true` in paper mode

### Current Trades

**Manual Test Trades (Proof of Control):**
1. Account 001: Trade 12439 (GBP_USD) - OPEN
2. Account 002: Trade 2024 (GBP_USD) - OPEN
3. Account 003: Trade 2556 (GBP_USD) - OPEN
4. Account 004: Trade 903 (XAU_USD) - OPEN
5. Account 005: Trade 2245 (XAU_USD) - OPEN
6. Account 006: Trade 14864 (EUR_USD) - OPEN

These will be managed by the autonomous system once the runner is started.

---

**Next Step:** Start the runner service to begin autonomous trading.

**Safety Note:** System is in **PAPER MODE** - all trades execute against OANDA practice accounts only. No real money at risk.
