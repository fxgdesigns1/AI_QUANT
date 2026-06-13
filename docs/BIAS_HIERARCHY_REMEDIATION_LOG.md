# Bias Hierarchy Remediation Log

Objective: Fix structural trading deadlock by introducing a bias hierarchy with provenance, so strong directional markets are not silenced by a single OutlookEngine / credential failure, while preserving all safety gates and auditability.

## 2026-01-21 – Implementation Notes

- Implemented **explicit OutlookEngine failure signaling**
  - Updated `src/control_plane/outlook_engine.py` to emit per‑instrument records with:
    - `bias: null`
    - `confidence: 0.0`
    - `source: "outlook_engine"`
    - `status: "unavailable"`
    - `error: "<exception message>"`
  - These records are persisted as part of the existing `runtime/outlook_*.json` snapshots to avoid silent NEUTRAL bias on errors.

- Implemented **price‑action bias module**
  - Added `src/core/price_action_bias.py`:
    - Input: 48 H1 candles (≈48h) per instrument.
    - Metrics: 48h return %, linear regression slope.
    - Rule: if `abs(48h_return) >= 2.0%` AND slope agrees with direction:
      - Emit `bias = "BULLISH"` or `"BEARISH"`.
      - Confidence scales from ~0.6 at 2% toward 0.8–0.9 for stronger moves.
    - Otherwise: `bias = None`, `confidence = 0.0`.

- Implemented **regime‑based bias module**
  - Added `src/core/regime_bias.py`:
    - Input: `RegimeAnalysis` from `MarketRegimeDetector`.
    - If regime is `UNKNOWN` or `CHOPPY` → `bias=None` (never guess).
    - If a directional field (`direction` = UP/DOWN) is present:
      - Map to `BULLISH` / `BEARISH`.
      - Confidence derived from ADX and directional consistency.
    - If no safe direction is available, remain neutral with a structured reason.

- Implemented **hierarchical bias resolver**
  - Added `src/core/bias_resolver.py`:
    - Normalizes inputs into `BiasComponent` instances for:
      - Outlook (`source="outlook_engine"`)
      - Price action (`source="price_action"`)
      - Regime (`source="regime_detector"`)
    - `resolve_bias(outlook, price_action, regime, min_confidence=0.4)`:
      - Priority: Outlook → Price Action → Regime.
      - Requires directional agreement across contributors.
      - Averages confidence, then applies penalties:
        - Outlook unavailable: −10% confidence.
        - Single‑source only: −10% confidence.
      - If disagreement or all sources neutral/unavailable:
        - `bias=None`, `confidence=0.0`, penalty entries recorded.
    - `persist_bias_resolution(repo_root, symbol, resolved, context)`:
      - Writes `runtime/bias_resolution.json` atomically with:
        - `symbol`
        - `resolved_bias` (bias, confidence, sources, penalties)
        - lightweight decision context (session, regime, news state, roadmap flag).

- Integrated **bias hierarchy into session regime gate**
  - Updated `src/strategies/session_regime_aligned.py`:
    - Injected `PriceActionBias`, `RegimeBias`, and `bias_resolver` into the strategy.
    - In `should_allow_trade`:
      - Continues to:
        - Classify session.
        - Detect regime via `MarketRegimeDetector`.
        - Extract news state and embargo flag.
        - Compute roadmap details from Outlook snapshots (unchanged for transparency).
      - NEW: builds three bias components:
        - Outlook component from roadmap/effective bias and snapshot health.
        - Price‑action component from 48h return and slope.
        - Regime component from `RegimeAnalysis`.
      - Calls `resolve_bias(...)` with `MIN_BIAS_CONFIDENCE = 0.4`.
      - Extends the gate context with:
        - `resolved_bias`
        - `resolved_confidence`
        - `bias_sources`
        - `bias_penalties`
      - Persists each decision’s resolution summary to `runtime/bias_resolution.json`.
    - **Gating logic (safety preserved, deadlock reduced)**:
      - Gate 1: **News Embargo** – unchanged, still blocks unconditionally.
      - Gate 2: **Bias hierarchy availability/strength**:
        - If `resolved.bias is None` OR `resolved.confidence < MIN_BIAS_CONFIDENCE`:
          - Block with reason code `bias_unavailable_all_sources`.
      - Gate 3: **Policy Store**:
        - `bias_alignment="aligned"` only if a resolved bias exists.
      - Gate 4: **Participation score** – unchanged (`participation_score >= 0.6`).
    - All gate decisions are still written to:
      - `logs/session_regime_gate_audit.jsonl` (existing JSONL audit).
      - Now enriched with the bias hierarchy fields above.

- Extended **session‑regime snapshot API with bias provenance**
  - Updated `src/control_plane/api.py` in:
    - `GET /api/session-regime-gate/snapshot`:
      - Extracts the latest bias hierarchy fields from the last audit event:
        - `resolved_bias`
        - `resolved_confidence`
        - `bias_sources`
        - `bias_penalties`
      - Adds `bias_resolution` to the snapshot payload, so the dashboard can display:
        - Which sources contributed.
        - Effective confidence.
        - Penalties applied (e.g. Outlook unavailable, single‑source only).

## Safety Assertions

- **News Embargo**: still enforced as the first gate in `SessionRegimeAlignedStrategy.should_allow_trade`; bias hierarchy cannot override an embargo.
- **ExecutionGuard** (`src/core/execution_gate.py`): left completely unchanged; live trading remains opt‑in with explicit env flags and confirm token.
- **Risk management** (daily loss limits, account limits): untouched; all new logic is read‑only on the regime gate side.
- **Paper mode**: default behavior unchanged; the new bias hierarchy only influences the gate that decides if trades *would* be allowed, not whether live execution is enabled.

## Expected Behavioral Change

- Previous behavior:
  - Single OutlookEngine or credential failure could cause roadmap alignment to fail,
    resulting in a structurally neutral / blocked state even in strong real‑world trends.
- New behavior:
  - When OutlookEngine is unavailable but:
    - Price‑action bias detects a strong, consistent move, and/or
    - Regime bias confirms a stable trend,
  - The resolver can still emit a non‑neutral `resolved_bias` with moderated confidence,
    allowing the session regime gate to pass (subject to all existing policy and safety gates).
  - If **all** sources are neutral/unavailable, the system remains FAIL‑CLOSED with an explicit
    `bias_unavailable_all_sources` reason code and full audit trail.

