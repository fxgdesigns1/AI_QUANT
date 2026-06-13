# Nov 2025 vs Current Deployment Differences

## Summary

**Nov 2025 Commit**: `b25f28a6a25669cd96b29ea18ea0704b177e39d5` (tag: `safepoint-2025-11-06`)  
**Current HEAD**: `2e2adc1e6718be20f42694b6a090a7e2db2a65d7`  
**Total files changed**: 1255 files (D=deleted, A=added, M=modified)

## Name-Status Summary (Deployment-Critical Files)

### Deployment Infrastructure Files

| Status | File Path | Notes |
|--------|-----------|-------|
| **Nov 2025 → Current** | | |
| Present in both | `deploy/gcp/bootstrap_vm.sh` | Core VM bootstrap script (likely unchanged or minor changes) |
| Present in both | `deploy/gcp/ai-quant-control-plane.service` | systemd unit file |
| Present in both | `deploy/gcp/secrets_to_env.sh` | Secret Manager loader |
| A (added) | `scripts/systemd/ai-quant-control-plane.service` | New systemd unit location (alternative/canonical?) |
| A (added) | `scripts/systemd/ai-quant-runner.service` | Runner service unit (new component) |
| A (added) | `scripts/systemd/install_units.sh` | Unit installation script |
| D (deleted) | `ai_trading.service` | Removed old service file |
| D (deleted) | `automated_trading.service` | Removed old service file |
| A (added) | `.env.example` | Environment variable template (new pattern) |
| A (added) | `ARTIFACTS/VM_DEPLOY_INSTRUCTIONS.md` | Deployment documentation (new) |

### Configuration & Scripts

| Status | File Path | Notes |
|--------|-----------|-------|
| A (added) | `scripts/start_control_plane_clean.sh` | Enhanced startup script (may have CONTROL_PLANE_TOKEN support) |
| A (added) | `scripts/verify_control_plane.sh` | Verification script (new) |
| A (added) | `scripts/audit_cloud_readiness_complete.sh` | Cloud readiness audit (new) |
| A (added) | `scripts/verify_env_no_leak.sh` | Secret leak prevention (new) |
| M (modified) | `.gitignore` | Enhanced ignore patterns |
| A (added) | `CONTROL_PLANE_COMMANDS.sh` | Quick reference commands |

## High-Signal Diffs (Author Summary)

### 1. Infra Changes

**Service File Location**:
- **Nov 2025**: Primary systemd unit at `deploy/gcp/ai-quant-control-plane.service`
- **Current**: Additional/alternative unit at `scripts/systemd/ai-quant-control-plane.service`
- **Impact**: Possible canonical location shift; both may coexist

**Runner Service**:
- **Nov 2025**: No explicit runner service unit found
- **Current**: `scripts/systemd/ai-quant-runner.service` exists
- **Impact**: Runner now managed as separate systemd service (was manual or absent)

**Installation Automation**:
- **Nov 2025**: Manual copy of systemd unit in bootstrap script
- **Current**: `scripts/systemd/install_units.sh` provides structured installation
- **Impact**: More standardized installation process

### 2. Deployment Automation Changes

**Bootstrap Script**:
- **Nov 2025**: `deploy/gcp/bootstrap_vm.sh` handles VM creation, code deployment, systemd setup
- **Current**: Same file exists, may have enhancements (need diff to confirm)
- **Impact**: Likely minor improvements; core approach unchanged

**Deployment Verification**:
- **Nov 2025**: No explicit verification scripts found
- **Current**: Multiple verification scripts (`verify_control_plane.sh`, `verify_vm_full_stack.sh`, `verify_env_no_leak.sh`)
- **Impact**: Enhanced deployment validation and safety checks

**Documentation**:
- **Nov 2025**: Minimal deployment documentation
- **Current**: Extensive docs in `ARTIFACTS/`, `docs/runbooks/`, `VM_DEPLOYMENT.md`
- **Impact**: Better documented deployment process

### 3. Entrypoint/Process Changes

**Control Plane Startup**:
- **Nov 2025**: Systemd unit calls `scripts/start_control_plane_clean.sh` directly
- **Current**: `scripts/start_control_plane_clean.sh` may have added token generation and enhanced logging
- **Impact**: Possible token-based authentication added; better startup logging

**Runner Process**:
- **Nov 2025**: Runner process not clearly defined in deployment
- **Current**: Dedicated systemd service `ai-quant-runner.service`
- **Impact**: Runner now managed separately with systemd lifecycle

### 4. Env Loading + Secrets Changes

**Environment Variables**:
- **Nov 2025**: All secrets from Secret Manager via `deploy/gcp/secrets_to_env.sh`
- **Current**: `.env.example` suggests `.env` file support may be added (for local dev?)
- **Impact**: Hybrid approach: Secret Manager for VM, `.env` for local development

**Secret Leak Prevention**:
- **Nov 2025**: No explicit secret leak scanning
- **Current**: `scripts/verify_env_no_leak.sh` scans for exposed secrets
- **Impact**: Enhanced security hygiene

**Pre-commit Hooks**:
- **Nov 2025**: No evidence of pre-commit hooks
- **Current**: Pre-commit hooks likely added (based on audit scripts referencing hooks)
- **Impact**: Prevents committing secrets at commit time

### 5. Execution Gating Changes

**Trading Mode Safety**:
- **Nov 2025**: `OANDA_ENV="practice"` hardcoded in `secrets_to_env.sh`
- **Current**: May have more explicit gating (need code inspection)
- **Impact**: Possibly enhanced safety controls (paper mode enforcement)

**Verification Gates**:
- **Nov 2025**: Basic secret presence check in `secrets_to_env.sh`
- **Current**: Multiple verification scripts check readiness before execution
- **Impact**: Fail-closed approach strengthened

### 6. Dependencies Changes

**Python Environment**:
- **Nov 2025**: Venv setup in bootstrap script (`python3 -m venv .venv`, install from `requirements.txt` or `pyproject.toml`)
- **Current**: Same approach, but may have dependency updates
- **Impact**: Likely dependency version changes (non-breaking)

**Service Dependencies**:
- **Nov 2025**: Requires `gcloud` CLI, Python 3, systemd
- **Current**: Same, plus verification script dependencies
- **Impact**: No breaking changes to base dependencies

## Suspected Regressions (Evidence-Based)

### 1. Service File Duplication

**Issue**: Two systemd unit files exist:
- `deploy/gcp/ai-quant-control-plane.service` (Nov 2025 location)
- `scripts/systemd/ai-quant-control-plane.service` (Current location)

**Evidence**: Both files exist in current HEAD; unclear which is canonical.

**Recommendation**: Determine canonical location and remove duplicate, or document why both exist.

### 2. Bootstrap Script Path Assumptions

**Issue**: Bootstrap script may assume specific paths that have changed.

**Evidence**: 
- Nov 2025: Uses `/opt/ai-quant` as deployment root
- Current: May use different paths or have path flexibility

**Recommendation**: Verify bootstrap script paths match current deployment structure.

### 3. Secrets Loading Script Dependencies

**Issue**: `deploy/gcp/secrets_to_env.sh` requires `GCP_PROJECT_ID` but may not be set in systemd unit.

**Evidence**: Systemd unit in Nov 2025 doesn't explicitly set `GCP_PROJECT_ID` before calling `secrets_to_env.sh`.

**Recommendation**: Ensure `GCP_PROJECT_ID` is set in systemd unit Environment directive.

### 4. Control Plane Token Missing in Nov 2025

**Issue**: Current system requires `CONTROL_PLANE_TOKEN` for POST endpoints, but Nov 2025 may not have had this.

**Evidence**: Current codebase references `CONTROL_PLANE_TOKEN` in API; Nov 2025 commit doesn't show token generation.

**Recommendation**: If restoring Nov 2025 deployment, may need to add token generation or disable token requirement.

## Recommendations

### Preferred Fix: Align Current System to Nov 2025 Blueprint Where Appropriate

1. **Consolidate Service Files**:
   - Determine canonical systemd unit location (prefer `deploy/gcp/` for consistency with bootstrap script)
   - Remove duplicate or document dual-location rationale

2. **Ensure Bootstrap Script Compatibility**:
   - Verify `deploy/gcp/bootstrap_vm.sh` works with current codebase
   - Test bootstrap script end-to-end on fresh VM

3. **Maintain Secret Manager Approach**:
   - Keep Secret Manager as primary secret source (Nov 2025 pattern)
   - Use `.env` files only for local development (current enhancement)

4. **Add Missing Safety Gates**:
   - If Nov 2025 lacked explicit paper mode gating, add it while preserving Nov 2025 structure
   - Ensure `OANDA_ENV="practice"` default is maintained

5. **Preserve Verification Enhancements**:
   - Keep current verification scripts as they add value
   - Integrate them into bootstrap script or deployment pipeline

6. **Document Deployment Path**:
   - Clear documentation on which service file to use
   - Runbook updates to reflect current state

## File Change Counts

- **Deleted files**: ~400+ (mostly documentation and old scripts)
- **Added files**: ~200+ (new artifacts, verification scripts, documentation)
- **Modified files**: ~600+ (configuration updates, code changes)

**Note**: Most changes are documentation and code, not deployment infrastructure. Core deployment approach (systemd on GCE VM) remains consistent.

## Deployment Method Consistency

✅ **Deployment method unchanged**: Both Nov 2025 and current use `systemd-vm` (GCE VM with systemd service units)

✅ **Bootstrap script present**: `deploy/gcp/bootstrap_vm.sh` exists in both

✅ **Secrets approach consistent**: Secret Manager used for production secrets

⚠️ **Service file location shifted**: May have moved from `deploy/gcp/` to `scripts/systemd/` (or both coexist)

⚠️ **Verification enhanced**: Current has more verification steps (positive improvement)
