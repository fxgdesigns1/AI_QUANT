# Strategy Loading Mechanism

**Date:** 2026-01-05T01:35:00Z  
**Purpose:** Document how strategies are loaded, registered, and activated  
**Status:** ✅ Verified - Strategies are static Python code (cannot be hot-reloaded)

---

## Canonical Strategy Source

### Location

**File:** `src/control_plane/strategy_registry.py`  
**Type:** Static Python dictionary  
**Structure:** `STRATEGIES: Dict[str, StrategyInfo] = {...}`

### Current Strategies

```python
STRATEGIES = {
    "momentum": StrategyInfo(...),
    "gold": StrategyInfo(...),
    "range": StrategyInfo(...),
    "eur_usd_5m_safe": StrategyInfo(...),
    "momentum_v2": StrategyInfo(...),
}
```

### Strategy Metadata Structure

```python
@dataclass
class StrategyInfo:
    key: str
    name: str
    description: str
    instruments: List[str]
    tunables: Dict[str, Any]
    risk_level: str  # low|medium|high
    session_preference: str  # any|london|ny|asia
```

---

## Loading Mechanism

### Registration Process

1. **Module Import Time:**
   - When `src/control_plane/api.py` imports `strategy_registry`, the `STRATEGIES` dict is evaluated
   - Registry is loaded into memory as a Python dict (not from external file)

2. **Access Functions:**
   - `get_strategy_registry()` → Returns copy of `STRATEGIES` dict
   - `get_strategy_info(key)` → Returns `StrategyInfo` for specific key
   - `validate_strategy_key(key)` → Returns `True` if key exists in registry

3. **Validation:**
   - `RuntimeConfig.validate()` checks `active_strategy_key` against registry
   - `POST /api/config` validates via `RuntimeConfig.validate()`
   - `POST /api/strategy/activate` validates via `validate_strategy_key()`

---

## Strategy Activation

### Endpoints

1. **`POST /api/config`**
   - **Body:** `{ "active_strategy_key": "gold" }`
   - **Validation:** Uses `RuntimeConfig.validate()` (checks registry)
   - **Storage:** Writes to `runtime/config.yaml`
   - **Effect:** Runner reads config on next hot-reload cycle

2. **`POST /api/strategy/activate`**
   - **Body:** `{ "strategy_key": "gold" }`
   - **Validation:** Uses `validate_strategy_key()` (checks registry)
   - **Storage:** Writes to `runtime/config.yaml`
   - **Effect:** Same as `/api/config` (both update config file)

### Verification

```bash
# Check active strategy
curl -s http://127.0.0.1:8787/api/status | python -m json.tool | grep active_strategy_key

# Activate strategy
curl -X POST http://127.0.0.1:8787/api/strategy/activate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy_key": "gold"}'

# Verify activation
curl -s http://127.0.0.1:8787/api/status | python -m json.tool | grep active_strategy_key
```

---

## Adding New Strategies

### Process

1. **Edit Registry File:**
   ```python
   # src/control_plane/strategy_registry.py
   STRATEGIES = {
       # ... existing strategies ...
       "my_new_strategy": StrategyInfo(
           key="my_new_strategy",
           name="My New Strategy",
           description="Strategy description",
           instruments=["EUR_USD", "GBP_USD"],
           tunables={"param1": 10, "param2": 20},
           risk_level="medium",
           session_preference="london"
       ),
   }
   ```

2. **Restart Control Plane:**
   ```bash
   # Stop control plane
   pkill -f "python -m src.control_plane.api"
   
   # Start control plane
   python -m src.control_plane.api
   ```

3. **Verify New Strategy:**
   ```bash
   curl -s http://127.0.0.1:8787/api/strategies | python -m json.tool | grep my_new_strategy
   ```

4. **Activate Strategy:**
   ```bash
   curl -X POST http://127.0.0.1:8787/api/strategy/activate \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"strategy_key": "my_new_strategy"}'
   ```

---

## Hot Reload: Why It's Not Implemented

### Technical Constraint

**Strategies are Python code, not external config files.**

- ✅ **CAN hot-reload:** YAML/JSON config files (e.g., `runtime/config.yaml`)
- ❌ **CANNOT hot-reload:** Python code safely (would require dynamic module reimport)

### Why Not Implement `POST /api/strategies/reload`?

1. **Safety:** Dynamic module reimport in production is risky
   - Could break if module dependencies changed
   - Could cause memory leaks or import conflicts
   - No safe way to reload Python code without restart

2. **Security:** Dynamic code loading is a security risk
   - System is designed with "NO DYNAMIC CODE LOADING" principle
   - Registry is static to prevent code injection

3. **Complexity:** Would require complex module reloading
   - Need to track module dependencies
   - Need to handle import conflicts
   - Need to ensure no state corruption

### Alternative: Config-Based Strategies (Future)

If hot-reload of strategies is required in the future:

1. **Move strategies to YAML/JSON file:**
   - `runtime/strategies.yaml`
   - Load at startup + on `/api/strategies/reload`

2. **Implement reload endpoint:**
   - Read YAML file
   - Validate structure
   - Update in-memory registry
   - Return success/failure

3. **Trade-offs:**
   - ✅ Can hot-reload
   - ❌ Lose Python code flexibility (no complex logic)
   - ❌ Need validation schema for strategy metadata

**Current Design Decision:** Keep strategies as static Python code (simpler, safer, sufficient for current needs)

---

## Validation Flow

```
User Request (POST /api/config or POST /api/strategy/activate)
    ↓
Strategy Key Validation
    ├─ validate_strategy_key(key) OR RuntimeConfig.validate()
    ├─ Checks: key in STRATEGIES dict
    └─ Returns: True (valid) or False (invalid)
    ↓
If Invalid: HTTP 400 Bad Request
    └─ Error: "Invalid strategy key: {key}"
    ↓
If Valid: Update Config
    ├─ config_store.save(partial_update={"active_strategy_key": key})
    ├─ RuntimeConfig.validate() (double-check)
    ├─ Write to runtime/config.yaml
    └─ Return: Success response
    ↓
Runner Hot-Reload
    ├─ Runner checks config file mtime
    ├─ Reloads config on change
    ├─ Updates active_strategy_key
    └─ Uses new strategy on next scan
```

---

## API Endpoints Summary

| Endpoint | Method | Purpose | Validates Key | Hot Reload |
|----------|--------|---------|---------------|------------|
| `/api/strategies` | GET | List all strategies | N/A | N/A |
| `/api/config` | POST | Update config (including strategy) | ✅ Yes | ✅ Yes (runner) |
| `/api/strategy/activate` | POST | Activate strategy | ✅ Yes | ✅ Yes (runner) |
| `/api/strategies/reload` | POST | ❌ **NOT IMPLEMENTED** | N/A | N/A |

**Note:** Strategy registry itself cannot be hot-reloaded (requires restart). Strategy **activation** can be hot-reloaded (via config file).

---

## Verification Commands

### Check Registry

```bash
# List all strategies
curl -s http://127.0.0.1:8787/api/strategies | python -m json.tool

# Check specific strategy
curl -s http://127.0.0.1:8787/api/strategies | python -m json.tool | grep -A 10 "gold"
```

### Check Active Strategy

```bash
# Get current active strategy
curl -s http://127.0.0.1:8787/api/status | python -m json.tool | grep active_strategy_key
```

### Activate Strategy

```bash
# Activate strategy (requires auth token)
curl -X POST http://127.0.0.1:8787/api/strategy/activate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy_key": "gold"}'

# Verify activation
curl -s http://127.0.0.1:8787/api/status | python -m json.tool | grep active_strategy_key
```

### Verify Validation

```bash
# Try invalid strategy (should fail)
curl -X POST http://127.0.0.1:8787/api/strategy/activate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy_key": "invalid_strategy"}'

# Expected: HTTP 400 Bad Request
# Response: {"detail": "Invalid strategy key: invalid_strategy"}
```

---

## Summary

- ✅ **Strategy Source:** Static Python code in `src/control_plane/strategy_registry.py`
- ✅ **Validation:** Both `/api/config` and `/api/strategy/activate` validate strategy keys
- ✅ **Activation:** Strategies can be activated via config file (hot-reload supported)
- ❌ **Registry Reload:** Cannot hot-reload registry (Python code requires restart)
- ✅ **Adding Strategies:** Edit `strategy_registry.py` + restart control plane

---

**Last Updated:** 2026-01-05T01:35:00Z
