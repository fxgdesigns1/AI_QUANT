## Foundation archive note (5950X)

**Machine**: `G-Machine` (Windows 11 Pro 10.0.26200)  
**Purpose**: Preserve this Google Drive workspace as **non-authoritative evidence only** due to integrity + environment blockers.

### Why this workspace is non-authoritative

- **Git integrity broken**: `git` reports `fatal: bad object HEAD` from `H:/My Drive/AI Trading/Gcloud system`.
- **WSL/bash path missing**: `wsl.exe` reports **no installed distributions**, so the canonical Linux/bash local research wrappers cannot be executed from this machine state.

### What was preserved (do not delete yet)

- `ARTIFACTS/backtests/` contains:
  - `tournament_20260407T022028Z`
  - `tournament_20260407T112506Z`
- `ARTIFACTS/monte_carlo/` contains:
  - `mc_20260407T122513Z`
- `ARTIFACTS/exports/` contains:
  - `pack_20260407T122520Z`
  - `test_pack_1`
- Candle cache used by tournaments:
  - `ARTIFACTS/candles/strict_research_current/cache_manifest.json` (`ready_for_backtest=true`)

### Next authoritative path (intended)

Create a clean WSL Ubuntu estate under `~/fxg-research/current_repo` and re-run the install/verify wrappers there. Until then, treat this Drive-synced repo as **archive only**.

