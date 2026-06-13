# FXG Backtest Environment Audit — 2026-06-12

Mission: verify the G-Machine backtest environment is fit for strategy research with
parity against the live ALPHA system (`fxg-paper-e2-small-main-2026`, /opt/ai-quant).

> Path note: the mission brief referenced `H:\My Drive\AI Trading\fxg-orchestrator\` as the
> orchestrator repo. That directory exists but is **not a git repository** (no `.git`); the
> actual git repo carrying branch `fxg-strategy-research-20260612` is
> `H:\My Drive\AI Trading\Gcloud system` (origin: github.com/fxgdesigns1/AI_QUANT). All
> version-controlled deliverables live here; a copy of this audit is dropped in
> `fxg-orchestrator\` for discoverability.

---

## CHECK 1 — Harness entry point: **PASS (with notes)**

| Item | Finding |
|---|---|
| `fxg-orchestrator/orchestrator/run_backtest.py` | **Stub** — MT5 Strategy Tester launcher, body is `TODO`, never implemented. Not the harness. |
| `C:\FXG\backtest_cache\fxg_lon_momentum_engine.py` | **Canonical harness.** Filter-first-then-dedupe (window → body → SMA gate → day-dedupe), M15 signals, H1 SMA 8/20 bias from the *prior closed* H1 bar (no look-ahead), 48-bar M15 SL/TP walk-forward evaluation. stdlib-only (csv module). |
| Dry-run import test | **PASS** — `IMPORT OK`, smoke run EUR_USD `full` period: 9 trades, +6.0R. Python 3.13.5, `requests` available. |
| `lon_open_momentum_v1.py` | Not in the local repo. Lives on ALPHA at `/opt/ai-quant/src/strategies/backtested/lon_open_momentum_v1.py` (fetched 2026-06-12, 214 lines). Confirmed structural template: TradeSignal dataclass, `generate_signals(instrument, timeframe)`, direction_detector import, metadata dict with session/bias/body_ratio/rr_target. |
| Important history | `C:\FXG\backtest_cache\LON_MOMENTUM_VALIDATION_REPORT.md` (2026-06-10) shows lon_open_momentum_v1 **failed its own 5-month walk-forward gate** (2 of 5 months net-positive, needed 4). It is approved/enabled in champions.json from the (small-sample) Feb tournament, but the canonical multi-month validation failed it. New candidates must clear the harder Phase-5 gates of this mission. |

## CHECK 2 — Candle data inventory: **PASS for 8 instruments; 2 missing**

Cache: `C:\FXG\backtest_cache\` — 7.4 MB, 56 CSV files, M15 + H1 only (no M5/H4 — engine is M15-native; mission text said M5 but the canonical engine and all prior validation use M15).

Per-instrument coverage (M15, via `_q1` + `_april` + `_full` files):

| Instrument | M15 span | H1 span | April 2026 | May 2026 | Weekday gaps >4h |
|---|---|---|---|---|---|
| AUD_JPY | 2026-01-05 → 2026-06-09 | 2026-01-05 → 2026-06-09 | YES | YES | 0 |
| EUR_USD | 2026-01-05 → 2026-06-09 | 2026-01-05 → 2026-06-09 | YES | YES | 0 |
| EUR_AUD | 2026-01-05 → 2026-06-09 | 2026-01-05 → 2026-06-09 | YES | YES | 0 |
| NZD_USD | 2026-01-05 → 2026-06-09 | 2026-01-05 → 2026-06-09 | YES | YES | 0 |
| NZD_JPY | 2026-01-05 → 2026-06-09 | 2026-01-05 → 2026-06-09 | YES | YES | 0 |
| GBP_USD | 2026-04-10 → 2026-06-09 (no q1) | 2026-01-13 → 2026-06-09 | YES | YES | 0 |
| GBP_AUD | 2026-04-10 → 2026-06-09 (no q1) | 2026-01-13 → 2026-06-09 | YES | YES | 0 |
| EUR_JPY | 2026-05-11 → 2026-06-09 (full only) | 2026-02-12 → 2026-06-09 | NO (M15) | YES | 0 |
| **USD_JPY** | **MISSING** | **MISSING** | — | — | — |
| **XAU_USD** | **MISSING** | **MISSING** | — | — | — |

- Gap scan (all 56 files): **zero weekday gaps >4h**. Weekend gaps (Fri→Sun/Mon) excluded by rule.
- File-suffix semantics: `_q1` = 2026-01-05→04-10, `_april` = 04-10→05-08, `_full` = 05-11→06-09,
  unsuffixed = stale partial pulls (superseded; harmless).
- **Fix applied (Phase 2):** USD_JPY and XAU_USD fetched via the repo's canonical fetcher
  `scripts/local_research/oanda_mid_historical_fetch.py` (`fetch_oanda_mid_candles_range`) —
  the exact path `w24_fetch_research_candles.py` already uses. No new HTTP code. All
  instruments topped up to 2026-06-12 by `fxg_backtest_setup.py`.

## CHECK 3 — Position sizer parity: **FIXED (was FAIL — file absent locally)**

- Local repo had **no** `src/core/position_sizer.py` at all (G-Machine repo diverged from ALPHA tree).
- Live version pulled from ALPHA 2026-06-12 (195 lines, header: "FXG FIX 2026-06-12 … champion cross pairs").
- **Synced verbatim into the local repo** at `src/core/position_sizer.py`
  (commit "sync: position_sizer from live ALPHA 2026-06-12").

Live sizer facts (authoritative for backtests):

| Class | Min SL distance | Hard lot cap | Risk-per-lot model |
|---|---|---|---|
| Forex standard (incl. EUR_USD, GBP_USD, EUR_AUD, NZD_USD, GBP_AUD…) | 3.0 pips (0.00030) | 2.0 lots | sl_dist × 100,000 |
| JPY pairs (USD_JPY, AUD_JPY, NZD_JPY, EUR_JPY…) | 3.0 pips (0.030) | 2.0 lots | sl_dist × 100,000/150 |
| XAU_USD | $1.50 | **0.5 lots** | sl_dist × 100 |
| XAG_USD | $0.10 | 0.5 lots | sl_dist × 5,000 |

- $300 default risk per trade: **confirmed hardcoded** (`risk_usd: float = 300.0`).
- XAU_USD entry **exists** (the 924d8b1 / 2026-06-12 fix is live).
- ⚠️ Mission brief said XAU_USD "2.0 lot hard cap" — the **live sizer caps XAUUSD at 0.5 lots**.
  The live value is used everywhere in this research (live is authoritative).
- Backtest rule: signal whose SL distance < minimum ⇒ **REJECTED**, not resized.

## CHECK 4 — Direction detector parity: **FIXED (was FAIL — file absent locally)**

- Local repo had no `direction_detector.py`. Live copy at
  `/opt/ai-quant/src/control_plane/direction_detector.py` (46 lines) pulled and
  **synced verbatim** to `src/control_plane/direction_detector.py`.
- Live logic: SMA 8/20 on H1 closes (last 25 candles, complete only), 5-minute cache,
  LONG if fast > slow×1.0001, SHORT if fast < slow×0.9999, else NEUTRAL. Gates **both** directions.
- Backtest engine `_get_bias()` parity: same SMA periods, same ×1.0001/×0.9999 thresholds,
  same H1 granularity, uses prior **closed** H1 bar — equivalent to live behaviour without look-ahead. **MATCH.**

## CHECK 5 — Session window parity: **PASS (documented)**

- ALPHA `runtime/config.yaml` contains **no** session window keys (grep returned strategy/
  scan config only). Windows live in code: `/opt/ai-quant/src/control_plane/trading_windows.py`:
  - `london`: 08:00–10:30 UTC (quality 85)
  - `london_ny_overlap`: 13:00–16:00 UTC (quality 100) → classified `NY_OVERLAP`
- Canonical engine LON signal window 08:00–08:30 UTC (minutes 480–510) — matches the live
  lon_open_momentum_v1 `_is_london_open_window` exactly.
- Mission windows confirmed against live code: LON_OPEN 08:00–09:30 ⊂ london window;
  NY_OVERLAP 13:00–16:00 exact; NY signal window 13:30–14:00 ⊂ overlap window.
- trend_pullback_v1 (live file) session tuples (UTC, authoritative over its own comments):
  LON_PRE 05:00–06:15, LON_FLOW 08:30–10:00, NY_OPEN 13:30–15:00. The comments in that file
  are UTC+1 local equivalents; the code tuples are what executes.

## CHECK 6 — Spread/slippage model: **NEEDS_FIX → FIXED in research runner**

- `fxg_lon_momentum_engine.py` applies **zero cost** per trade (confirmed by code read:
  `pnl_r = rr` / `-1.0` raw). The 2026-06-10 validation ran cost-free.
- Fix: research runner (`fxg_research_backtest_v1.py`, new file — engine reused via import,
  not modified) deducts per-round-trip costs from every trade:

| Instrument class | Round-trip cost |
|---|---|
| EUR_USD, GBP_USD | 0.8 pips |
| AUD_JPY, NZD_JPY, USD_JPY (JPY crosses) | 1.2 pips |
| EUR_AUD, NZD_USD, GBP_AUD | 1.0 pips |
| XAU_USD | $0.35 |

Cost is converted to R by `cost_price_units / sl_distance` and subtracted from each trade's R.
No zero-cost backtests in this research.

## CHECK 7 — Verdict

**NEEDS_FIXES → all fixes applied → READY**

| # | Issue | Fix | Status |
|---|---|---|---|
| 1 | USD_JPY, XAU_USD not cached | fetched via canonical OANDA fetcher (fxg_backtest_setup.py) | FIXED |
| 2 | position_sizer.py absent locally | synced from ALPHA verbatim | FIXED |
| 3 | direction_detector.py absent locally | synced from ALPHA verbatim | FIXED |
| 4 | zero-cost harness | cost model layered in research runner (engine untouched) | FIXED |
| 5 | cache ends 2026-06-09 | topped up to 2026-06-12 by setup script | FIXED |

### Keeping environments in sync going forward
1. The G-Machine repo and `/opt/ai-quant` have **diverged structurally** (no `src/shared/`,
   no `src/strategies/backtested/` locally). Treat ALPHA as authoritative for runtime files;
   sync the three parity-critical files (`position_sizer.py`, `direction_detector.py`,
   `trading_windows.py`) into this repo whenever ALPHA changes them — they are now tracked here.
2. Run `python fxg_backtest_setup.py --from <start> --to <today>` at the start of every research
   session; it re-checks parity (sizer minimums, SMA 8/20 thresholds, session windows) and
   refreshes the candle cache idempotently.
3. Never re-introduce a parallel downloader or a second sizer implementation (universal fix rule).
