# Nov 2025 vs Current — Quick Answers

## What we compared

- **Nov (known-good)**: `b25f28a6a25669cd96b29ea18ea0704b177e39d5` (tag: `safepoint-2025-11-06`)
- **Current**: `2e2adc1e6718be20f42694b6a090a7e2db2a65d7` (HEAD on `safety/savepoint-pre-lockin`)

## Critical Differences (Why Nov Worked, Current Struggles)

### 1) **Secret Loading Method Changed: Secret Manager → .env File**

**Nov 2025** (`deploy/gcp/ai-quant-control-plane.service:12`):
```bash
ExecStart=/bin/bash -lc 'source /opt/ai-quant/deploy/gcp/secrets_to_env.sh >/tmp/aiquant_env_check.log 2>&1 && CONTROL_PLANE_BG=0 REQUIRE_OANDA=1 REQUIRE_NEWS=1 REQUIRE_TELEGRAM=1 bash scripts/start_control_plane_clean.sh'
```

**Current** (`scripts/systemd/ai-quant-control-plane.service:12`):
```ini
EnvironmentFile=/etc/ai-quant/.env
ExecStart=/bin/bash -c 'cd /opt/ai-quant && source .venv/bin/activate && CONTROL_PLANE_BG=0 bash scripts/start_control_plane_clean.sh'
```

**Why this breaks**:
- Nov loaded secrets from **GCP Secret Manager** via `secrets_to_env.sh` script, which validates all required secrets exist and **fails closed** if missing
- Current expects secrets in `/etc/ai-quant/.env` file, which:
  - May not exist or be incomplete
  - Has no validation step before service starts
  - Service may start with missing/invalid secrets and fail later
- **File evidence**: 
  - Nov: `deploy/gcp/secrets_to_env.sh` validates secrets and exits with error if missing
  - Current: `scripts/systemd/ai-quant-control-plane.service` just loads `.env` file without validation

**Impact**: Service may start but fail at runtime due to missing secrets (OANDA, NEWSAPI, TELEGRAM, etc.)

---

### 2) **REQUIRE_ Flags Removed: No Runtime Validation**

**Nov 2025** (`deploy/gcp/ai-quant-control-plane.service:12`):
- Set `REQUIRE_OANDA=1 REQUIRE_NEWS=1 REQUIRE_TELEGRAM=1` in ExecStart
- These flags were passed to startup script for validation

**Current** (`scripts/systemd/ai-quant-control-plane.service:14`):
- No `REQUIRE_*` flags set
- Service starts without checking if required services are available

**Why this breaks**:
- Nov enforced that OANDA, NEWS, and TELEGRAM credentials must be present before starting
- Current has no such validation, so service may start with missing credentials and fail when APIs are called
- **File evidence**: 
  - `scripts/local_run_and_verify.sh` shows REQUIRE_ flags are used in local scripts but not in systemd unit
  - `src/core/settings.py` has `require_oanda()`, `require_telegram()` methods, but they're only called if code explicitly checks

**Impact**: Service starts successfully but fails when trying to use OANDA/NEWS/TELEGRAM APIs due to missing credentials

---

### 3) **CONTROL_PLANE_TOKEN Now Required for POST Endpoints**

**Nov 2025**: 
- No evidence of `CONTROL_PLANE_TOKEN` in systemd unit or secrets loader
- API authentication may have been disabled or not implemented

**Current** (`src/control_plane/api.py:36,112-124`):
```python
CONTROL_PLANE_TOKEN = os.getenv("CONTROL_PLANE_TOKEN", "")
# ...
if not CONTROL_PLANE_TOKEN:
    print("⚠️  Warning: No CONTROL_PLANE_TOKEN set - authentication disabled")
    # POST endpoints still work but warn
```

**Why this breaks**:
- Current system generates token in `scripts/start_control_plane_clean.sh` if not set
- But if systemd unit doesn't export `CONTROL_PLANE_TOKEN`, it may generate a new one each restart, breaking dashboard authentication
- **File evidence**: 
  - `scripts/start_control_plane_clean.sh:16-31` generates token if missing
  - `src/control_plane/api.py:1081-1084` shows warning if token not set
  - Systemd unit doesn't set or persist `CONTROL_PLANE_TOKEN`

**Impact**: Dashboard POST requests (strategy switching, config updates) may fail if token not set consistently

---

### 4) **News Integration Gating: No Explicit Enable/Disable**

**Nov 2025**:
- `REQUIRE_NEWS=1` enforced news credentials must exist
- Secrets loader validated `NEWSAPI_API_KEY` and `ALPHAVANTAGE_API_KEY` presence

**Current**:
- No `REQUIRE_NEWS` flag in systemd unit
- News integration may be optional or disabled by default
- No validation that news APIs are configured

**Why this breaks**:
- If news features are enabled in dashboard/config but credentials are missing, API calls will fail
- No fail-closed behavior for news integration
- **File evidence**: 
  - `scripts/local_run_and_verify.sh:39-44` shows news integration can be enabled via config API POST
  - But systemd unit doesn't set `REQUIRE_NEWS=1`, so validation doesn't happen

**Impact**: News/macro integration may be broken silently if credentials missing

---

### 5) **Environment Variable Source: No Centralized Loading**

**Nov 2025**:
- Single source of truth: `deploy/gcp/secrets_to_env.sh` loads all secrets from Secret Manager
- Script validates all required secrets before service starts

**Current**:
- Multiple potential sources: `.env` file, `EnvironmentFile` directive, explicit env vars
- No centralized validation before service starts
- Control plane API loads settings via `src/core/settings.py` which reads from environment

**Why this breaks**:
- Secrets may be missing, incomplete, or from wrong source
- No early validation means failures happen at runtime, not startup
- **File evidence**: 
  - `src/core/settings.py:70` has `load_settings()` that reads from env vars
  - But validation methods (`require_oanda()`, etc.) are only called if code explicitly checks
  - No startup-time validation in current systemd unit

**Impact**: Configuration errors discovered at runtime instead of startup, leading to partial failures

---

### 6) **Working Directory and Venv Activation Changed**

**Nov 2025** (`deploy/gcp/ai-quant-control-plane.service:12`):
```bash
# ExecStart runs from /opt/ai-quant (set by WorkingDirectory)
source /opt/ai-quant/deploy/gcp/secrets_to_env.sh
```

**Current** (`scripts/systemd/ai-quant-control-plane.service:14`):
```bash
cd /opt/ai-quant && source .venv/bin/activate
```

**Why this breaks**:
- Nov assumed venv was already activated or Python was system-wide
- Current explicitly activates venv, which may fail if venv doesn't exist or is corrupted
- Path assumptions changed (venv must exist and be valid)

**Impact**: Service may fail to start if venv is missing or broken

---

### 7) **Network Binding: Same (127.0.0.1:8787), But No Firewall Check**

**Nov 2025**:
- Service binds to `127.0.0.1:8787` (inferred from systemd unit)
- Bootstrap script creates firewall rule `aiquant-allow-8787` for TCP:8787

**Current**:
- Service binds to `127.0.0.1:8787` (same, from `src/control_plane/api.py:37-38`)
- No evidence of firewall rule creation in current deployment scripts

**Why this breaks**:
- If VM is recreated or firewall rules reset, port 8787 may not be accessible
- External access (if needed) will fail
- **File evidence**: 
  - `deploy/gcp/bootstrap_vm.sh:25-31` (Nov) creates firewall rule
  - Current bootstrap script may not create it

**Impact**: Service runs but may not be accessible externally or from other VMs

---

## Top Suspected Regressions (Summary)

1. **Secret validation removed**: Current systemd unit doesn't validate secrets before starting, so service may start with missing credentials and fail later
2. **REQUIRE_ flags not set**: No enforcement that OANDA/NEWS/TELEGRAM must be configured before service starts
3. **CONTROL_PLANE_TOKEN not persisted**: Token may regenerate on each restart, breaking dashboard authentication
4. **.env file dependency**: System expects `/etc/ai-quant/.env` but may not be created or populated correctly
5. **Venv activation added**: Explicit venv activation may fail if venv doesn't exist (vs Nov which may have used system Python)
6. **No centralized secret loading**: Multiple env sources without validation leads to inconsistent state

---

## Immediate Paper-Safe Restore Actions (Document Only)

1. **Restore Secret Manager loading**:
   - Update `scripts/systemd/ai-quant-control-plane.service` ExecStart to source `deploy/gcp/secrets_to_env.sh` like Nov
   - Or create `/etc/ai-quant/.env` with all required secrets manually

2. **Add REQUIRE_ flags back**:
   - Set `REQUIRE_OANDA=1 REQUIRE_NEWS=1 REQUIRE_TELEGRAM=1` in ExecStart command
   - Ensure startup script validates these flags

3. **Persist CONTROL_PLANE_TOKEN**:
   - Generate token once and store in Secret Manager or `/etc/ai-quant/.env`
   - Set it in systemd unit's `Environment` directive

4. **Validate secrets at startup**:
   - Ensure `secrets_to_env.sh` (or equivalent) validates all required secrets and exits with error if missing
   - Check `/tmp/aiquant_env_check.log` after service start

5. **Verify firewall rule exists**:
   - Run: `gcloud compute firewall-rules describe aiquant-allow-8787 --project $GCP_PROJECT_ID`
   - Create if missing: `gcloud compute firewall-rules create aiquant-allow-8787 --allow tcp:8787 --target-tags aiquant`

6. **Test startup sequence**:
   - Manually run: `source deploy/gcp/secrets_to_env.sh` and verify all secrets load
   - Check: `echo $OANDA_API_KEY | wc -c` (should be > 0)
   - Verify: `/tmp/aiquant_env_check.log` shows all secrets present

---

## File Evidence References

- **Nov systemd unit**: `deploy/gcp/ai-quant-control-plane.service` (commit `b25f28a`)
- **Current systemd unit**: `scripts/systemd/ai-quant-control-plane.service` (commit `2e2adc1`)
- **Secrets loader**: `deploy/gcp/secrets_to_env.sh` (exists in both, but usage differs)
- **API code**: `src/control_plane/api.py:36-38,112-124` (token handling)
- **Settings loader**: `src/core/settings.py:49-68` (validation methods exist but not called at startup)
- **Start script**: `scripts/start_control_plane_clean.sh:16-31` (token generation)
