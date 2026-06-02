# Strategy Add Workflow

**Date:** 2026-01-05T02:15:00Z  
**Purpose:** Document the authoritative workflow for adding new strategies  
**Status:** ✅ Verified — Strategies are static Python code (require restart)

---

## Executive Summary

**Strategies are static Python code in `src/control_plane/strategy_registry.py`.**

- ✅ **Single authoritative registry** defines allowed keys
- ✅ **Used by BOTH** `/api/strategies` and config validation
- ✅ **Adding strategies requires:** Edit code + restart control plane
- ❌ **Hot reload is NOT supported** (Python code cannot be safely reloaded)

---

## Canonical Strategy Registry

### Location

**File:** `src/control_plane/strategy_registry.py`  
**Variable:** `STRATEGIES: Dict[str, StrategyInfo] = {...}`

### Structure

```python
STRATEGIES: Dict[str, StrategyInfo] = {
    "momentum": StrategyInfo(...),
    "gold": StrategyInfo(...),
    "range": StrategyInfo(...),
    "eur_usd_5m_safe": StrategyInfo(...),
    "momentum_v2": StrategyInfo(...),
    # Add new strategies here
}
```

---

## Workflow: Adding a New Strategy

### Step 1: Edit Registry File

Edit `src/control_plane/strategy_registry.py` and add your strategy:

```python
STRATEGIES: Dict[str, StrategyInfo] = {
    # ... existing strategies ...
    "mean_rev_v2": StrategyInfo(
        key="mean_rev_v2",
        name="Mean Reversion V2",
        description="Enhanced mean reversion strategy with adaptive filters",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY"],
        tunables={
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adaptive_filter": True,
            "volatility_threshold": 0.5,
        },
        risk_level="low",
        session_preference="asia"
    ),
}
```

### Step 2: Restart Control Plane

**Required:** Restart the control plane to load the new strategy.

```bash
# Stop control plane (if running)
pkill -f "python -m src.control_plane.api"

# Start control plane
python -m src.control_plane.api
```

**Why restart?**
- Python code is loaded at module import time
- Cannot safely reload Python modules at runtime
- Registry is evaluated when `strategy_registry` module is imported

### Step 3: Verify New Strategy

```bash
# Check strategy appears in /api/strategies
curl -s http://127.0.0.1:8787/api/strategies | python3 -m json.tool | grep -A 5 "mean_rev_v2"

# Verify validation accepts it
curl -s -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"active_strategy_key": "mean_rev_v2"}' | python3 -m json.tool

# Check active strategy
curl -s http://127.0.0.1:8787/api/status | python3 -m json.tool | grep active_strategy_key
```

---

## Validation Flow

### Single Source of Truth

**Registry (`STRATEGIES` dict) is the authoritative source:**

1. **`GET /api/strategies`** → Returns `list(STRATEGIES.keys())`
2. **`RuntimeConfig.validate()`** → Checks `active_strategy_key in STRATEGIES`
3. **`POST /api/config`** → Uses `RuntimeConfig.validate()` (checks registry)
4. **`POST /api/strategy/activate`** → Uses `validate_strategy_key()` (checks registry)

**All validation paths use the same registry.**

---

## StrategyInfo Schema

```python
@dataclass
class StrategyInfo:
    key: str                    # Unique identifier (e.g., "mean_rev_v2")
    name: str                   # Display name (e.g., "Mean Reversion V2")
    description: str            # Human-readable description
    instruments: List[str]      # Preferred instruments (e.g., ["EUR_USD", "GBP_USD"])
    tunables: Dict[str, Any]    # Editable parameters (future use)
    risk_level: str            # "low" | "medium" | "high"
    session_preference: str     # "any" | "london" | "ny" | "asia"
```

---

## Example: Adding `mean_rev_v2`

### 1. Edit Registry

```python
# src/control_plane/strategy_registry.py

STRATEGIES: Dict[str, StrategyInfo] = {
    # ... existing strategies ...
    "mean_rev_v2": StrategyInfo(
        key="mean_rev_v2",
        name="Mean Reversion V2",
        description="Enhanced mean reversion strategy with adaptive Bollinger Bands and volatility filters",
        instruments=["EUR_USD", "GBP_USD", "USD_JPY"],
        tunables={
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adaptive_filter": True,
            "volatility_threshold": 0.5,
            "min_range_width": 10,
        },
        risk_level="low",
        session_preference="asia"
    ),
}
```

### 2. Restart Control Plane

```bash
# Stop (if running)
pkill -f "python -m src.control_plane.api"

# Start
cd "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
python -m src.control_plane.api
```

### 3. Verify

```bash
# Check /api/strategies
curl -s http://127.0.0.1:8787/api/strategies | python3 -m json.tool | grep -A 10 "mean_rev_v2"

# Test validation (requires auth token)
curl -s -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"active_strategy_key": "mean_rev_v2"}' | python3 -m json.tool

# Check active strategy
curl -s http://127.0.0.1:8787/api/status | python3 -m json.tool | grep active_strategy_key
```

---

## Why Not Hot Reload?

### Technical Constraint

**Strategies are Python code, not external config files.**

- ✅ **CAN hot-reload:** YAML/JSON config files (e.g., `runtime/config.yaml`)
- ❌ **CANNOT hot-reload:** Python code safely (would require dynamic module reimport)

### Safety Reasons

1. **Security:** Dynamic code loading is a security risk
2. **State Corruption:** Module reload can cause state corruption
3. **Dependencies:** Complex dependency tracking required
4. **Design Principle:** System designed with "NO DYNAMIC CODE LOADING" principle

### Design Decision

**Keep strategies as static Python code:**
- ✅ Simple and safe
- ✅ Type-safe (IDE support)
- ✅ Version controlled (git)
- ✅ No runtime code injection risk

**Trade-off:** Requires restart (acceptable for strategy changes which are infrequent)

---

## Alternative: Config-Based Strategies (Future)

If hot-reload is required in the future:

1. **Move strategies to YAML/JSON:**
   - `runtime/strategies.yaml`
   - Load at startup + on `/api/strategies/reload`

2. **Implement reload endpoint:**
   - Read YAML file
   - Validate structure
   - Update in-memory registry
   - Return success/failure

3. **Trade-offs:**
   - ✅ Can hot-reload
   - ❌ Lose Python code flexibility
   - ❌ Need validation schema

**Current Design:** Keep static Python code (simpler, safer)

---

## Verification Checklist

After adding a new strategy:

- [ ] Strategy appears in `GET /api/strategies` → `allowed` list
- [ ] Strategy appears in `GET /api/strategies` → `strategies` array
- [ ] `POST /api/config` accepts new key (no validation error)
- [ ] `POST /api/strategy/activate` accepts new key (no validation error)
- [ ] `GET /api/status` shows new key as `active_strategy_key` (after activation)
- [ ] Runner uses new strategy after restart (if runner is restarted)

---

## Summary

✅ **Single authoritative registry:** `src/control_plane/strategy_registry.py`  
✅ **Used by all validation:** `/api/strategies`, config validation, strategy activation  
✅ **Adding strategies:** Edit code + restart control plane  
❌ **Hot reload:** Not supported (Python code requires restart)  
✅ **Workflow:** Edit registry → Restart control plane → Verify

---

**Last Updated:** 2026-01-05T02:15:00Z
