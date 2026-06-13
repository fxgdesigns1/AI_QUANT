# FXG Research Environment Setup - Complete
**Date:** 2026-03-11  
**Status:** ✅ COMPLETE

## AUDIT SUMMARY

### Files Found
- **Backtesting entrypoints:** ✅ CREATED (`scripts/run_strategy_tournament.py`)
- **Tournament entrypoints:** ✅ CREATED (`scripts/run_strategy_tournament.py`)
- **Dataset cache builders:** ✅ CREATED (`scripts/dataset_to_backtest_cache.py`)
- **Monte Carlo runners:** ✅ CREATED (`scripts/run_monte_carlo.py`, `src/research/monte_carlo.py`)
- **Research directory:** ✅ CREATED (`src/research/`)

### Path Resolution
- **REPO_ROOT:** Resolved via `Path(__file__).resolve().parents[1]` in scripts
- **ARTIFACTS:** Configurable via `LOCAL_ARTIFACTS_ROOT` env var
- **Runtime paths:** Configurable via `LOCAL_RUNTIME_ROOT` env var

### Environment Dependency
- **Cached mode:** ✅ Does NOT require OANDA env vars
- **Research mode:** ✅ Controlled via `RESEARCH_MODE=true` and `USE_CACHED_CANDLES=true`
- **Settings helper:** ✅ Created `src/research/settings_helper.py` for research mode checks

## FILES CREATED

### Research Core
- `src/research/__init__.py` - Research module
- `src/research/backtest_core.py` - Backtest engine with cached candle support
- `src/research/monte_carlo.py` - Monte Carlo runner
- `src/research/settings_helper.py` - Research mode settings helper

### Scripts
- `scripts/dataset_to_backtest_cache.py` - Dataset to cache converter
- `scripts/run_strategy_tournament.py` - Tournament runner
- `scripts/run_monte_carlo.py` - Monte Carlo entrypoint
- `scripts/setup_local_research_env.sh` - Local environment setup
- `scripts/sync_vm_artifacts.sh` - VM artifact sync
- `scripts/smoke_test_cached_backtest.sh` - Cached backtest smoke test

### Configuration
- `.env.research.example` - Research environment template (in repo, copy to `.env.research`)

## LOCAL LAYOUT

```
~/fxg-ai-quant-local/
├── repo/                    # Symlink or reference to repo
├── runtime/                 # Runtime configs
├── artifacts/
│   ├── datasets/           # Synced datasets
│   ├── backtests/          # Tournament results
│   ├── monte_carlo/        # Monte Carlo outputs
│   └── candles/            # Cached candle files
├── logs/                    # Research logs
├── exports/                 # Exported results
├── quarantine/              # Quarantined files
└── venv/                    # Python virtual environment
```

## COMMANDS TO RUN ON 5950X

### 1. Initial Setup
```bash
# Clone or link repo
cd ~
bash ~/fxg-ai-quant-local/repo/scripts/setup_local_research_env.sh

# Create Python venv
python3 -m venv ~/fxg-ai-quant-local/venv
source ~/fxg-ai-quant-local/venv/bin/activate

# Install dependencies
pip install -r ~/fxg-ai-quant-local/repo/requirements.txt
```

### 2. Configure Environment
```bash
# Copy research env template
cp ~/fxg-ai-quant-local/repo/.env.research.example ~/fxg-ai-quant-local/.env.research

# Edit if needed (defaults should work)
# nano ~/fxg-ai-quant-local/.env.research

# Load environment
export $(cat ~/fxg-ai-quant-local/.env.research | grep -v '^#' | xargs)
```

### 3. Sync Artifacts from VM
```bash
# Set VM connection details (if not in .env)
export VM_PROJECT="fxg-ai-trading"
export VM_ZONE="us-east1-b"
export VM_INSTANCE="fxg-quant-paper-e2-micro"

# Sync artifacts
bash ~/fxg-ai-quant-local/repo/scripts/sync_vm_artifacts.sh
```

**Expected Output:**
```
=== SYNCING VM ARTIFACTS TO LOCAL 5950X ===
VM: fxg-quant-paper-e2-micro (fxg-ai-trading/us-east1-b)
Local: ~/fxg-ai-quant-local/artifacts

Verifying VM connection...
✅ VM accessible

Syncing dataset: dataset_20260307T222011Z_recent30_enriched
  Found dataset on VM, syncing...

Syncing tournament candle cache: tournament_dataset_20260307T222011Z_recent30_enriched
  Found candle cache on VM, syncing...

Syncing resolved config: tournament_dataset_20260307T222011Z_recent30_enriched_wave2_v1
  Found resolved config on VM, syncing...

✅ Artifact sync complete!
```

### 4. Smoke Test Cached Backtest
```bash
bash ~/fxg-ai-quant-local/repo/scripts/smoke_test_cached_backtest.sh
```

**Expected Output:**
```
=== CACHED BACKTEST SMOKE TEST ===

✅ Activated Python venv
✅ OANDA_API_KEY not set (correct for cached mode)
✅ Candle cache found: ~/fxg-ai-quant-local/artifacts/candles/tournament_dataset_20260307T222011Z_recent30_enriched
✅ Tournament config found: ~/fxg-ai-quant-local/artifacts/backtests/.../tournament_config_resolved.json

Running cached tournament...
[Tournament execution logs...]

✅ Smoke test PASSED
   Results: ~/fxg-ai-quant-local/artifacts/backtests/smoke_test_YYYYMMDDTHHMMSSZ/tournament_results.json
```

### 5. Run Monte Carlo
```bash
# Activate venv
source ~/fxg-ai-quant-local/venv/bin/activate

# Run Monte Carlo on tournament results
python3 ~/fxg-ai-quant-local/repo/scripts/run_monte_carlo.py \
    --input-tournament ~/fxg-ai-quant-local/artifacts/backtests/tournament_dataset_20260307T222011Z_recent30_enriched_wave2_v1/report.json \
    --output ~/fxg-ai-quant-local/artifacts/monte_carlo/mc_$(date +%Y%m%dT%H%M%SZ) \
    --iterations 1000 \
    --workers 16 \
    --seed 42 \
    --mode reshuffle
```

**Expected Output:**
```
Starting Monte Carlo run: mc_YYYYMMDDTHHMMSSZ
Iterations: 1000, Workers: 16
Monte Carlo mode: cached data only (no OANDA env vars required)
[Progress logs...]
Completed 1000/1000 iterations
Monte Carlo complete: ~/fxg-ai-quant-local/artifacts/monte_carlo/.../monte_carlo_summary.json

============================================================
MONTE CARLO SUMMARY
============================================================
Run ID: mc_YYYYMMDDTHHMMSSZ
Iterations: 1000/1000
Expectancy - Mean: X.XXXX, Std: X.XXXX
Win Rate - Mean: X.XXXX
Max Drawdown: X.XXXX
Robustness P5-P95: X.XXXX to X.XXXX
============================================================
```

## COMMANDS TO RUN ON M1 MAC (Control Node)

### 1. Setup (One-time)
```bash
# Clone repo
cd ~
git clone <repo-url> ~/fxg-ai-quant-local/repo

# Or if repo already exists, create symlink
mkdir -p ~/fxg-ai-quant-local
ln -sfn <existing-repo-path> ~/fxg-ai-quant-local/repo
```

### 2. Inspection/Orchestration
```bash
# View research results
ls -lh ~/fxg-ai-quant-local/artifacts/monte_carlo/*/monte_carlo_summary.json

# Check sync status
ls -lh ~/fxg-ai-quant-local/artifacts/candles/

# View tournament results
cat ~/fxg-ai-quant-local/artifacts/backtests/*/tournament_results.json | jq
```

## VERIFICATION CHECKLIST

- [ ] Local directory structure created (`~/fxg-ai-quant-local/`)
- [ ] Python venv created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env.research` configured (from `.env.research.example`)
- [ ] VM artifacts synced (datasets, candles, configs)
- [ ] Smoke test passes (cached backtest runs without OANDA)
- [ ] Monte Carlo runs successfully
- [ ] All outputs written to user-owned paths (no root permissions)

## KNOWN CONSTRAINTS ADDRESSED

✅ **VM backtest reruns failed when OANDA env vars missing**
   - Fixed: Cached mode does not require OANDA env vars
   - Research mode explicitly bypasses OANDA requirements

✅ **Monte Carlo must avoid OANDA dependency**
   - Fixed: Monte Carlo uses cached tournament outputs only
   - No live API calls in research mode

✅ **Permission issues on VM artifact directories**
   - Fixed: Local environment writes to user-owned paths only
   - All artifacts under `~/fxg-ai-quant-local/artifacts/`

✅ **Deterministic verification required**
   - Fixed: All research tools support seeded randomness
   - Cached candles ensure deterministic runs

## NEXT STEPS

1. **On 5950X:** Run setup commands above
2. **On 5950X:** Sync artifacts from VM
3. **On 5950X:** Run smoke test to verify
4. **On 5950X:** Run Monte Carlo on tournament results
5. **On M1 Mac:** Review results and orchestrate next research cycle

## RUNLOG_JSON

```json
{
  "audit_date": "2026-03-11",
  "status": "COMPLETE",
  "files_created": [
    "src/research/__init__.py",
    "src/research/backtest_core.py",
    "src/research/monte_carlo.py",
    "src/research/settings_helper.py",
    "scripts/dataset_to_backtest_cache.py",
    "scripts/run_strategy_tournament.py",
    "scripts/run_monte_carlo.py",
    "scripts/setup_local_research_env.sh",
    "scripts/sync_vm_artifacts.sh",
    "scripts/smoke_test_cached_backtest.sh"
  ],
  "local_layout": "~/fxg-ai-quant-local/",
  "cached_mode_support": true,
  "oanda_required_for_research": false,
  "monte_carlo_implemented": true,
  "verification_commands_provided": true
}
```
