<!-- 03b93b37-c017-49c8-acc7-cb4cf00835c2 fe91a85a-c740-4db3-bb53-de89cc2d61cf -->
# Comprehensive Dashboard Fix & Code Cleanup

## Issue Analysis

**Primary Problems:**

1. Dashboard manager initializes at module level but becomes None during requests (not using Flask app context)
2. `OandaClient.get_account_info()` being called with account_id argument when it takes none
3. `TradeSignal` object treated as dictionary with `.get()` 
4. Multiple initialization paths create confusion
5. Contextual modules imported but not fully integrated

## Solution Architecture

**Use Flask Application Context** for all singletons instead of module-level globals. This ensures components persist across requests and multiple App Engine instances.

## Implementation Plan

### Phase 1: Fix Flask Application Context (CRITICAL)

**File: `main.py`**

Move dashboard_manager and other components INTO Flask app context:

```python
# BEFORE (lines 32-42): Module-level initialization
dashboard_manager = None
try:
    dashboard_manager = AdvancedDashboardManager()
except Exception as e:
    dashboard_manager = None

# AFTER: Use Flask app context
def get_dashboard_manager():
    """Get or create dashboard manager in Flask app context"""
    if 'dashboard_manager' not in app.config:
        try:
            logger.info("🔄 Initializing dashboard manager...")
            from src.dashboard.advanced_dashboard import AdvancedDashboardManager
            app.config['dashboard_manager'] = AdvancedDashboardManager()
            logger.info("✅ Dashboard manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize dashboard: {e}")
            logger.exception("Full traceback:")
            app.config['dashboard_manager'] = None
    return app.config.get('dashboard_manager')
```

Update ALL route handlers to use `get_dashboard_manager()` instead of global `dashboard_manager`:

```python
# Example - line 279-296
@app.route('/dashboard')
def dashboard():
    """Dashboard route"""
    try:
        mgr = get_dashboard_manager()
        if mgr:
            return render_template('dashboard_advanced.html')
        else:
            return jsonify({"error": "Dashboard not initialized"}), 503
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")
        return jsonify({"error": str(e)}), 500
```

Apply same pattern to:

- `/api/status` (line 1241)
- `/api/overview` (line 1262)
- `/api/accounts` (line 1287)
- `/api/insights` (line 1350)
- `/api/trade_ideas` (line 1379)
- `/api/contextual/<instrument>` (line 1520)
- All other routes using `dashboard_manager`

### Phase 2: Fix OandaClient Method Signature Error

**File: `main.py` (line 175)**

The error "`OandaClient.get_account_info() takes 1 positional argument but 2 were given`" means code is calling `oanda.get_account_info(account_id)` but method signature is `def get_account_info(self)`.

Fix in `capture_performance_snapshots()`:

```python
# Line 175-195 - BEFORE:
try:
    account_info = oanda.get_account_info(account_id)  # WRONG
    # ...
except Exception as e:
    logger.error(f"❌ Failed to get snapshot for {account_id}: {e}")

# AFTER:
try:
    # OandaClient uses account_id from its config, not as parameter
    oanda_instance = get_oanda_client()  # Gets client for current account
    account_info = oanda_instance.get_account_info()  # No argument
    # ...
except Exception as e:
    logger.error(f"❌ Failed to get snapshot for {account_id}: {e}")
```

**Alternative Fix:** Change OandaClient to accept account_id parameter if multiple accounts need one client instance.

### Phase 3: Fix TradeSignal Dictionary Access Error

**File: `src/core/simple_timer_scanner.py`** (likely around trade execution)

Error "`'TradeSignal' object has no attribute 'get'`" means code treats TradeSignal as dict.

Find and fix:

```python
# WRONG:
signal.get('instrument')  # Treats as dictionary

# RIGHT:
signal.instrument  # Access as dataclass attribute
```

Search pattern: `signal\.get\(` and replace with attribute access.

### Phase 4: Consolidate Duplicate Code

**Remove duplicate initialization patterns:**

1. **Scanner initialization** - Currently initialized in 3 places:

   - Line 84: `initialize_scanner()` function
   - Line 96: `run_scanner_job()` checks and re-initializes
   - Line 115: Called at module level

**Consolidate:** Use single lazy initialization in `get_scanner()` function:

```python
def get_scanner():
    """Get or create scanner in Flask app context"""
    if 'scanner' not in app.config:
        try:
            from src.core.simple_timer_scanner import get_simple_scanner
            app.config['scanner'] = get_simple_scanner()
            logger.info("✅ Scanner initialized")
        except Exception as e:
            logger.error(f"❌ Scanner init failed: {e}")
            app.config['scanner'] = None
    return app.config.get('scanner')

def run_scanner_job():
    """APScheduler job"""
    scanner = get_scanner()
    if scanner:
        scanner._run_scan()
```

2. **Remove unused imports** - Clean up duplicate/unused imports at top of files

3. **Single Source of Truth for Accounts:**

   - All account access should go through `account_manager`
   - Remove any direct YAML reading in dashboard code
   - Use `account_manager.get_active_accounts()` consistently

### Phase 5: Complete Contextual Integration

**Already partially done, but needs verification:**

1. **Dashboard Manager** (`advanced_dashboard.py` lines 208-220):

   - ✅ Contextual modules imported
   - ✅ Initialized in **init**
   - ✅ Used in get_contextual_insights()

2. **Add missing integration:**
```python
# In get_system_status() - enhance with contextual data
def get_system_status(self):
    status = {
        # ... existing fields ...
    }
    
    # Add session context
    if self.session_manager:
        try:
            now = datetime.now(pytz.UTC)
            quality, sessions = self.session_manager.get_session_quality(now)
            status['session_context'] = {
                'quality': quality,
                'active_sessions': sessions,
                'description': self.session_manager.get_session_description(now)
            }
        except Exception as e:
            logger.warning(f"Session context unavailable: {e}")
    
    return status
```

3. **Dashboard Template Updates** (`dashboard_advanced.html`):

   - ✅ Contextual panel HTML added (lines 833-867)
   - ✅ CSS styles added (lines 692-709)
   - ✅ JavaScript added (lines 2413-2462)
   - Verify JavaScript is calling correct endpoint

### Phase 6: Add Comprehensive Error Handling & Logging

**Pattern to apply everywhere:**

```python
def any_function():
    """Function with proper error handling"""
    try:
        # Main logic
        result = do_something()
        logger.info(f"✅ Success: {result}")
        return result
    except SpecificError as e:
        logger.error(f"❌ Specific error: {e}")
        # Handle gracefully
        return fallback_value
    except Exception as e:
        logger.error(f"❌ Unexpected error in any_function: {e}")
        logger.exception("Full traceback:")
        return None
```

Apply to:

- All route handlers
- All dashboard manager methods
- All data fetch operations

### Phase 7: Clean Up Initialization Flow

**Current flow is messy:**

- Dashboard manager: module level
- Scanner: module level + lazy
- Monitor: background thread
- News/AI: module level

**New clean flow:**

```python
# main.py structure:

# 1. Imports and logging setup
# 2. Create Flask app
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = ...

# 3. Lazy getter functions (use app.config)
def get_dashboard_manager(): ...
def get_scanner(): ...
def get_news_integration(): ...
def get_ai_assistant(): ...

# 4. Background jobs use getters
def run_scanner_job():
    scanner = get_scanner()
    if scanner: scanner._run_scan()

# 5. Routes use getters
@app.route('/dashboard')
def dashboard():
    mgr = get_dashboard_manager()
    ...

# 6. Start scheduler AFTER app setup
scheduler.init_app(app)
scheduler.add_job(...)
scheduler.start()
```

### Phase 8: Testing & Validation

**Local Testing:**

```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system
python3 -m pytest tests/ -v  # If tests exist
python3 -c "from main import app, get_dashboard_manager; print(get_dashboard_manager())"
```

**Deployment Testing:**

1. Deploy to Google Cloud
2. Check logs for initialization errors
3. Test endpoints:

   - `/api/health` - should show dashboard_manager: "initialized"
   - `/api/status` - should return 200 with 10 accounts
   - `/dashboard` - should load without 503
   - `/api/contextual/XAU_USD` - should return contextual data

4. Monitor for 10 minutes, check no ERROR/CRITICAL logs

### Success Criteria

- Dashboard loads without 503 errors
- All 10 accounts visible in `/api/status`
- No `OandaClient.get_account_info()` argument errors
- No `TradeSignal.get()` attribute errors  
- No module-level None references
- Contextual data flows to dashboard
- Clean logs with only INFO/WARNING
- Single initialization path per component
- No duplicate code patterns
- All routes use Flask app context

## Files to Modify

1. `main.py` - Refactor to use Flask app context (400+ lines affected)
2. `src/dashboard/advanced_dashboard.py` - Verify contextual integration
3. `src/core/simple_timer_scanner.py` - Fix TradeSignal.get() calls
4. `src/core/oanda_client.py` - Verify get_account_info() signature
5. `src/templates/dashboard_advanced.html` - Verify contextual JS endpoints

## Rollback Plan

If deployment fails, revert to previous version:

```bash
gcloud app services set-traffic default --splits 20251018t185455=1.0 --quiet
```

### To-dos

- [ ] Fix timestamp attribute errors in advanced_dashboard.py using _safe_timestamp helper
- [ ] Add robust error handling for account initialization to load all 10 accounts
- [ ] Import session_manager, quality_scoring, and price_context_analyzer modules
- [ ] Add contextual data (session quality, price context) to system status API
- [ ] Create /api/contextual/<instrument> endpoint for contextual insights
- [ ] Update dashboard HTML to display session quality and key levels
- [ ] Test locally to verify dashboard loads and all accounts connect
- [ ] Deploy to Google Cloud and migrate 100% traffic to new version
- [ ] Verify 10 accounts active, no errors, contextual data flowing