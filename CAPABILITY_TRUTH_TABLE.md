# Trading System Capability Truth Table
## Forensic Audit - Evidence-Based Assessment

**Audit Date:** December 31, 2025  
**Methodology:** Force-truth with proof - No assumptions, no intent-based inference  
**Standard:** If code does not execute in runtime, capability is ABSENT

---

## Executive Summary

**VERDICT: REAL AUTOMATED DEMO TRADING SYSTEM**

This system is **NOT** a mock or simulation. It executes **REAL ORDERS** on OANDA's demo broker environment. However, it uses **VIRTUAL MONEY ONLY** (demo accounts), making it a fully functional prototype without financial risk.

**Key Finding:** The "AI" branding is misleading - no machine learning exists. System uses traditional technical analysis only.

---

## Capability Matrix

| Capability | Status | Evidence | Execution Type | Notes |
|------------|--------|----------|----------------|-------|
| **MARKET DATA INGESTION** |
| Real-time Price Feed | ✅ PRESENT | `ai_trading_system.py:1147-1167`<br/>`src/core/oanda_client.py:79-100` | LIVE API CALL | HTTP GET to `api-fxpractice.oanda.com/v3/accounts/{id}/pricing` every 60s |
| News Feed Integration | ✅ PRESENT | `src/core/news_integration.py:28-89`<br/>MarketAuxClient with 5 API keys | LIVE API CALL | Fetches real news from MarketAux API with rate limiting |
| Historical Candle Data | ✅ PRESENT | `src/core/oanda_client.py` | LIVE API CALL | Can fetch OHLCV candles from OANDA |
| Economic Calendar | ⚠️ PARTIAL | `src/core/news_integration.py` mentions economic indicators | UNCLEAR | Code references exist but integration unclear |
| **STRATEGY EVALUATION** |
| Technical Analysis Strategies | ✅ PRESENT | 13 functional strategies in `src/strategies/` | RUNTIME | EMA, ATR, momentum, breakouts, volatility filters |
| Machine Learning Models | ❌ ABSENT | No ML libraries in `requirements.txt`<br/>No model files found | N/A | **"AI Trading" name is misleading** |
| Strategy Registry | ✅ PRESENT | `src/strategies/registry.py` | RUNTIME | Loads strategies dynamically by name |
| Multi-Strategy Support | ✅ PRESENT | 8 accounts with different strategies | RUNTIME | Each account runs independent strategy |
| Signal Generation | ⚠️ PARTIAL | 13 working, 3 placeholders | RUNTIME | Some strategies return empty signals |
| **TRADE EXECUTION** |
| Order Submission to Broker | ✅ PRESENT | `ai_trading_system.py:1980-1983`<br/>`requests.post()` to OANDA orders API | LIVE HTTP POST | **Real orders submitted to demo broker** |
| Market Orders | ✅ PRESENT | `execute_trade()` function | RUNTIME | Immediate execution at market price |
| Limit Orders | ✅ PRESENT | `execute_trade()` function | RUNTIME | Pending orders at specified price |
| Stop Loss / Take Profit | ✅ PRESENT | Bracket orders attached | RUNTIME | SL/TP sent with every order |
| Position Monitoring | ✅ PRESENT | `monitor_trades()` function | RUNTIME | Checks open positions via API |
| Live Broker Connection | ❌ ABSENT | `OANDA_BASE_URL = api-fxpractice.oanda.com` | DEMO ONLY | **No live trading - demo accounts only** |
| Paper Trading (Local Sim) | ❌ ABSENT | Orders reach real broker, not simulated | N/A | This is NOT paper trading |
| **RISK MANAGEMENT** |
| Daily Trade Limits | ✅ PRESENT | `ai_trading_system.py:1827-1829` | RUNTIME | Enforced before every trade |
| Position Size Limits | ✅ PRESENT | `max_concurrent_trades`, `max_per_symbol` | RUNTIME | Multiple position caps |
| Minimum R-Multiple | ✅ PRESENT | `ai_trading_system.py:1894-1904` | RUNTIME | Requires 0.5R minimum expected profit |
| News Halt Windows | ✅ PRESENT | `is_news_halt_active()` check | RUNTIME | Suspends trading during news events |
| Kill Switch - Manual | ✅ PRESENT | `trading_enabled` flag, Telegram `/disable` | RUNTIME | Can stop trading remotely |
| Kill Switch - Automatic | ✅ PRESENT | Daily limit auto-shutdown | RUNTIME | Stops when limits reached |
| Diversification Controls | ✅ PRESENT | Reserve slots, symbol caps | RUNTIME | Prevents over-concentration |
| **DATA PERSISTENCE** |
| Trade Logging Code | ⚠️ PARTIAL | `ai_trading_system.py:2024-2046`<br/>`TradeDatabase.record_trade_event()` | UNCLEAR | Code exists but persistence unclear |
| Historical Trade Database | ❌ ABSENT | `reports/daily/2025-11-30.json` has mock data | N/A | No confirmed persistent history |
| Firestore Integration | ⚠️ PARTIAL | `google-cloud-firestore` in requirements | UNCLEAR | Library installed but usage unclear |
| Performance Metrics | ⚠️ PARTIAL | Daily/weekly/monthly reports exist | MOCK DATA | Reports contain placeholder values |
| **BACKTESTING** |
| Integrated Backtesting | ❌ ABSENT | Backtest files in separate folder | N/A | Not integrated with main system |
| Strategy Validation | ❌ ABSENT | No backtest framework | N/A | **Cannot validate before deployment** |
| **OPERATIONAL** |
| Continuous Operation | ✅ PRESENT | `while True` loop, 60s cycle | RUNTIME | `ai_trading_system.py:2507-2528` |
| Multi-Threading | ✅ PRESENT | 4 threads: main, Telegram, adaptive, scheduler | RUNTIME | Concurrent execution |
| Systemd Service | ✅ PRESENT | `ai_trading.service` | DEPLOYED | Running on Google Cloud VM |
| Auto-Restart | ✅ PRESENT | `Restart=always` in service file | DEPLOYED | Recovers from crashes |
| Multi-Account Support | ✅ PRESENT | 8 demo accounts configured | RUNTIME | Processes all accounts per cycle |
| **MONITORING** |
| Telegram Notifications | ✅ PRESENT | Trade alerts, status updates | RUNTIME | Bot token configured |
| Remote Commands | ✅ PRESENT | Telegram command loop | RUNTIME | `/status`, `/disable`, `/enable` |
| Real-time Dashboard | ❌ ABSENT | Dashboard shows cached/old data | BROKEN | Mentioned but not working |
| Logging | ✅ PRESENT | Python logging throughout | RUNTIME | Extensive log output |
| **TESTING** |
| Unit Tests | ⚠️ PARTIAL | 7 test files found | UNCLEAR | Coverage unknown |
| Integration Tests | ❌ ABSENT | Not found | N/A | No end-to-end tests |
| Test Coverage | ❌ ABSENT | No coverage reports | N/A | Unknown coverage level |

---

## Evidence Summary

### ✅ CONFIRMED PRESENT (High Confidence)

1. **Market Data Ingestion**
   - File: `ai_trading_system.py`, function `get_current_prices()` at line 1147
   - Proof: `requests.get(f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/pricing")`
   - Execution: Live HTTP GET request every 60 seconds

2. **Trade Execution to Demo Broker**
   - File: `ai_trading_system.py`, function `execute_trade()` at line 1980
   - Proof: `requests.post(url, headers=self.headers, json=order_data, timeout=10)`
   - Destination: `https://api-fxpractice.oanda.com/v3/accounts/{id}/orders`
   - **This is REAL execution, not simulation**

3. **Risk Controls**
   - File: `ai_trading_system.py`, lines 1817-1862
   - Proof: Multiple checks before `execute_trade()`: daily limits, position caps, R-multiple validation
   - Execution: Enforced at runtime before every order

4. **Continuous Operation**
   - File: `ai_trading_system.py`, function `main()` at line 2507
   - Proof: `while True:` loop with `time.sleep(60)`
   - Deployment: Systemd service on Google Cloud VM (confirmed in `FINAL_DEPLOYMENT_VERIFICATION.md`)

5. **Multi-Strategy System**
   - File: `src/strategies/` directory with 16 strategy files
   - Proof: 13 functional strategies (alpha, gold_scalping variants, ultra_strict_forex, etc.)
   - Evidence: `src/strategies/alpha.py:156` - `analyze_market()` returns `List[TradeSignal]`

### ❌ CONFIRMED ABSENT (High Confidence)

1. **Machine Learning / AI**
   - Search: `ML|machine.learning|neural|model|train|predict|sklearn|tensorflow|pytorch`
   - Result: 9 matches across 3 files, all in comments/docs, no implementation
   - Requirements: No ML libraries in `requirements.txt`
   - **Verdict: "AI Trading System" name is misleading**

2. **Live Broker Trading**
   - File: `ai_trading_system.py`, line 47
   - Proof: `OANDA_BASE_URL = "https://api-fxpractice.oanda.com"` (hardcoded demo)
   - Account IDs: All start with `101-004-30719775-` (OANDA demo format)
   - **Verdict: Demo accounts only, no real money**

3. **Integrated Backtesting**
   - Search: `def.*backtest|class.*Backtest`
   - Result: 10 files found, all in `Sync folder MAC TO PC/` (separate system)
   - Main system: No backtesting framework
   - **Verdict: Cannot validate strategies before deployment**

4. **Persistent Trade History**
   - File: `reports/daily/2025-11-30.json`
   - Content: `{"active_strategy": "mock", "accounts": ["acc-1", "acc-2"]}`
   - **Verdict: Reports contain mock/placeholder data**

5. **Working Dashboard**
   - File: `FINAL_DEPLOYMENT_VERIFICATION.md`, line 139
   - Quote: "Dashboard: Showing old cached data (known issue)"
   - **Verdict: Dashboard exists but not functional**

### ⚠️ PARTIAL / UNCLEAR (Medium Confidence)

1. **Trade History Persistence**
   - Code exists: `ai_trading_system.py:2024-2046` calls `self.trade_db.record_trade_event()`
   - Database: `google-cloud-firestore` in requirements
   - Problem: Unclear if actually persisting to database or just in-memory
   - **Verdict: Code exists but persistence mechanism unverified**

2. **Strategy Completeness**
   - Working: 13 strategies with full implementation
   - Placeholders: 3 strategies return empty signals (`momentum_v2_improved.py:10` returns `[]`)
   - **Verdict: Most strategies functional, some are stubs**

3. **Testing Coverage**
   - Found: 7 test files in `tests/` directory
   - Problem: No test execution results, no coverage reports
   - **Verdict: Tests exist but coverage unknown**

---

## Runtime Flow (Confirmed)

```
STARTUP:
1. Load YAML config → 8 accounts with strategies
2. Initialize AITradingSystem objects
3. Start 4 threads (main, Telegram, adaptive, scheduler)

MAIN LOOP (every 60 seconds):
4. For each account:
   a. get_current_prices() → HTTP GET to OANDA API
   b. analyze_market() → Strategy evaluates MarketData
   c. execute_trade() → HTTP POST to OANDA API (if signal)
   d. monitor_trades() → Check open positions
5. Sleep 60 seconds
6. Repeat

EXECUTION DESTINATION:
→ OANDA fxPractice API (Demo Environment)
→ Orders are ACTUALLY FILLED by broker
→ NOT paper trading (local simulation)
→ BUT using virtual money only
```

---

## Critical Findings

### 🚨 Security Risk: Credentials Exposed

**Evidence:**
- `ai_trading_system.py:45` - OANDA API key hardcoded
- `ai_trading.service:19` - MarketAux API keys hardcoded
- `ai_trading_system.py:50` - Telegram bot token hardcoded

**Risk:** HIGH - All credentials visible in source code

**Recommendation:** Migrate to Google Secret Manager immediately

### 🚨 Missing Component: Backtesting

**Evidence:** No integrated backtesting framework found

**Risk:** HIGH - Strategies deployed without validation

**Impact:** Cannot verify strategy performance before risking money (even demo money)

### 🚨 Misleading Branding: "AI Trading"

**Evidence:** Zero machine learning implementation found

**Reality:** Traditional technical analysis only (EMA, ATR, momentum)

**Impact:** Expectations vs. reality mismatch

---

## What This System Actually Is

### ✅ It IS:
- Fully functional automated trading system
- Executes real orders on OANDA demo broker
- Fetches live market data and news
- Runs continuously on cloud VM
- Manages 8 demo accounts
- Has risk controls and monitoring
- Uses technical analysis strategies

### ❌ It IS NOT:
- Using machine learning or AI
- Trading with real money
- A paper trading simulator (orders reach real broker)
- Production-ready for live trading
- Properly tested or backtested
- Secure (credentials exposed)

---

## Readiness Assessment

### For Demo Trading: ✅ READY
- System is already running on demo accounts
- Orders are being executed successfully
- Risk controls are in place
- Monitoring via Telegram works

### For Live Trading: ❌ NOT READY

**Blocking Issues:**
1. No backtesting framework (cannot validate strategies)
2. No comprehensive test suite
3. Unclear trade history persistence
4. Security vulnerabilities (exposed credentials)
5. No disaster recovery plan
6. Dashboard not working
7. Some strategies are placeholders
8. No regulatory compliance addressed

**Estimated Work Required:** 3-6 months

**Critical Path:**
1. Implement backtesting (4-6 weeks)
2. Build test suite >80% coverage (3-4 weeks)
3. Fix persistence layer (2-3 weeks)
4. Security overhaul (1-2 weeks)
5. Validate all strategies (2-3 weeks)
6. Extended paper trading (4-8 weeks)
7. Gradual live rollout (4-8 weeks)

---

## Conclusion

**System Classification:** REAL AUTOMATED DEMO TRADING SYSTEM

**Confidence Level:** HIGH (based on direct code inspection and deployment evidence)

**Summary:** This is a functional automated trading system that successfully executes trades on OANDA's demo environment. It is NOT a mock or simulation - orders are actually submitted to and filled by the broker. However, it operates exclusively with virtual money. The system demonstrates core capability but lacks critical components (backtesting, testing, security, persistence) required for live trading. The "AI" branding is misleading as no machine learning exists.

**Bottom Line:** System works as a demo trading bot, but needs significant additional work before live trading with real money.

---

**Audit Completed:** December 31, 2025  
**Auditor:** Principal System Auditor  
**Methodology:** Force-truth with proof (no assumptions)  
**Evidence Quality:** STRONG
