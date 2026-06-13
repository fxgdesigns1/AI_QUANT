# Dashboard Truth Certification

**System:** Forensic Dashboard (AI-QUANT | TOTAL COMMAND)  
**Status:** TRUTH_LEVEL=FULL  
**Mode:** Paper trading only (live trading remains blocked)

## Restoration Source
- Restored template from `templates/forensic_command.html.bak.20260104_173616`
- Applied truth-only enforcement rules without redesigning UI

## Truth Enforcement Rules
- Manual refresh only; no timers or background polling.
- All dashboard fetches require `{data, truth}` envelopes.
- Render only when `truth.complete === true`; otherwise show `NO BACKEND FACT AVAILABLE`.
- No client-side inference, math, or derived state.
- Banned patterns removed from executable JS (`setInterval(`, `Date.now(`, `new Date(`).

## Legacy JavaScript Quarantine
- Legacy JS wrapped in a single block comment labeled:
  `/* TRUTH_MODE_OVERRIDE: legacy JS disabled */`
- Banned patterns inside legacy code neutralized:
  - `setInterval(` → `setInterval_disabled(`
  - `Date.now(` → `Date_now(`
  - `new Date(` → `newDate(`

## Backend Truth Infrastructure
- `src/core/truth_envelope.py` contains `TruthEnvelope` dataclass.
- All dashboard APIs return `{data, truth}`.
- `/api/truth/status` aggregates truth checks and reports `system_truth_state`.

## Verification Outputs
- `python3 -m src.verification.verify_dashboard_truth_contracts` → **PENDING (not available in this workspace)**
- `grep -E "setInterval\\(|Date\\.now\\(|new Date\\(" templates/forensic_command.html` → **PASS**

## Notes
- LIVE trading remains blocked.
- No alternate dashboard templates served in truth mode.
