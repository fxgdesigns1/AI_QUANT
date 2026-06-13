# FXG Strategy Research — 2026-06-12

Status: **GRIDS FROZEN — written before any backtest was executed** (this section is
committed to the research branch prior to running Phase 4; see git history for proof).

Environment audit: see `FXG_BACKTEST_ENV_AUDIT_2026-06-12.md` — verdict **READY** after fixes
(position_sizer + direction_detector synced from live ALPHA; USD_JPY + XAU_USD fetched via the
canonical OANDA fetcher; cost model added in research runner; cache topped up to 2026-06-12).

## Data inventory

- Source: OANDA practice API mid candles via `scripts/local_research/oanda_mid_historical_fetch.py`
  (the repo's canonical fetcher), built by `fxg_backtest_setup.py --from 2026-01-01 --to 2026-06-12`.
- Cache: `C:\FXG\backtest_cache\{INST}_{M15|H1}_canon.csv`
- Instruments (8): EUR_USD, AUD_JPY, EUR_AUD, NZD_USD, NZD_JPY, USD_JPY, GBP_USD, XAU_USD
- Span: 2026-01-01 → 2026-06-12 (≈ 11,030 M15 bars, 2,784 H1 bars per FX instrument)
- Gaps: zero weekday gaps >4h on all FX instruments. XAU_USD has one 73h closure
  2026-04-02→2026-04-05 = **Good Friday/Easter market holiday** (legitimate closure, not missing data).
- April 2026 (tariff-shock crisis month) and May 2026 (clean trend month): **both present for all 8.**

## Top champion family determination (input to Candidates B & C)

From live `configs/lanes/champions.json` + `FXG_BACKTEST_PERFORMANCE_SUMMARY.md` (pulled from ALPHA 2026-06-12):

| Family | Entries | Enabled | Tournament trades | Net R | Note |
|---|---|---|---|---|---|
| trend_pullback_v1 | 19 | 19 | 122 | +186.6 | best top-score entry (3.10), broadest enabled coverage |
| range_edge_v1 | 16 | **0** | 117 | +201.2 | entire family disabled, flagged under-validated |
| lon_open_momentum_v1 | 5 | 5 | 125 | +112.5 | **failed** canonical 5-month walk-forward 2026-06-10 (2/5 months positive) |
| sweep_reclaim_reversal_v2 | 5 | 5 | 30 | +26.7 | small |
| opening_drive_pullback_v2 | 2 | 2 | 19 | +30.4 | small |
| session_extreme_reversion_v2 | 1 | 1 | 5 | +7.0 | small |

**Top family = `trend_pullback_v1`** — largest enabled sample, all 19 entries enabled, top single
score (EUR_AUD LON_FLOW #11: 13 trades, PF 39.0). lon_open_momentum_v1 is excluded from "top"
despite trade count because the canonical engine invalidated it on 2026-06-10; range_edge_v1 is
excluded because the live system has the whole family disabled.

Top champion entry (frozen reference): `trend_pullback_v1#11`, EUR_AUD, LON_FLOW —
params `{atr_period: 14, entry_step: 1, max_hold_bars: 48, pullback_pct: 0.0005, rr_target: 3.0, stop_atr_mult: 1.25}`.
Note: `entry_step` exists in tournament params but is **unused by the live strategy file**
(`/opt/ai-quant/src/strategies/backtested/trend_pullback_v1.py` never reads it); the backtest
mirrors live behaviour and ignores it too. trend_pullback_v1 is LONG-only by live implementation.

## Canonical methodology (Phase 4 rules, frozen)

- **"Filter first (session window + body/setup conditions), then dedupe."** — FXG canonical order,
  enforced by reusing `fxg_lon_momentum_engine.generate_signals` (Candidate A) and implementing the
  identical order in the trend_pullback replication (Candidates B/C). Reversing this order produced
  a ~$3,900 one-month swing historically.
- Risk: $300/trade. Sizing/validation via live-synced `src/core/position_sizer.py`.
  Signal SL below sizer minimum ⇒ **REJECTED** (excluded), never resized.
  USD P&L uses effective risk after lot caps (cap ⇒ risk < $300, parity with live).
- Costs per round trip, converted to R as `cost_price_units / sl_distance` and deducted from every trade:
  EUR_USD, GBP_USD 0.8 pips; AUD_JPY, NZD_JPY, USD_JPY 1.2 pips; EUR_AUD, NZD_USD 1.0 pips; XAU_USD $0.35.
- Span: 2026-01-01 → 2026-06-12 (all cached history after setup run; includes April AND May 2026).
- Split: **train = signal date ≤ 2026-04-24**, **test (OOS) = signal date ≥ 2026-04-25** (70/30 by calendar).
  Parameters selected on train only, frozen, evaluated once on test. No iteration on test results.
- Same-bar SL/TP ambiguity resolved **SL-first (conservative)** — matches canonical engine.
- Variant selection rule (frozen): per candidate, the variant with highest **train** profit factor
  (after costs) among variants with ≥20 train trades advances to single OOS evaluation.
  Candidate C is a pure parameter-transfer test (no selection step; both variants judged against gates as-is).
- Reproducibility: surviving variant re-run once from a clean process; trade count and P&L must match exactly.

## Parameter grids (FROZEN before any run)

### Candidate A — `ny_open_momentum_v1` (9 variants)
Mirror of lon_open_momentum_v1 via the canonical engine, NY session:
- Signal window: **13:30–14:00 UTC** (minutes 810–840), inside NY_OVERLAP 13:00–16:00
- Body filter: ≥ 60% of range; Direction gate: SMA 8/20 H1 (prior closed bar), gates BOTH directions
- Instruments: EUR_USD, USD_JPY, XAU_USD (all cached)
- RR grid: [2.0, 3.0, 4.0]
- Variants = 3 instruments × 3 RR = 9

### Candidate B — `xauusd_session_champion_v1` (6 variants)
trend_pullback_v1 (top family) logic re-parameterised for XAU_USD volatility:
- SL = ATR-multiple sweep: [1.0×, 1.5×, 2.0×] of ATR(14) on M15
- Sessions: LON_OPEN 08:00–09:30 UTC and NY_OVERLAP 13:00–16:00 UTC (one variant per session)
- Fixed from champion #11: pullback_pct 0.0005, rr_target 3.0, max_hold_bars 48
- Sizer rules respected: $1.50 min SL distance, **0.5-lot hard cap** (live sizer value;
  mission brief said 2.0 but live ALPHA caps XAUUSD at 0.5 — live is authoritative)
- Variants = 3 ATR multiples × 2 sessions = 6

### Candidate C — `best_family_extension_v1` (2 variants)
trend_pullback_v1#11 exact champion params — NO re-optimisation:
- params: atr_period 14, max_hold_bars 48, pullback_pct 0.0005, rr_target 3.0, stop_atr_mult 1.25
- Session: LON_FLOW (champion's session; live code window 08:30–10:00 UTC)
- Instruments: GBP_USD, USD_JPY
- Variants = 1 param set × 2 instruments = 2. Pass or fail as-is.

Total variants: 17 (≤ 20-per-candidate limit; grid fixed here, never expanded).

## Promotion gates (hard floors — never loosened)

- G1. ≥40 trades full period AND ≥15 trades in test split
- G2. OOS profit factor ≥1.4 AND full-period PF ≥1.5
- G3. Positive OOS expectancy per trade after costs
- G4. Max drawdown full period ≤ $2,100 (7R at $300)
- G5. Net P&L ≥ breakeven in April 2026 AND May 2026 separately
- G6. Reproducibility: clean re-run identical

Survivors ranked by OOS PF; at most one promoted (lane 010 manual-only). Zero survivors = complete, successful outcome.

---

*Results sections appended below after Phase 4 execution — grids above were not modified after this point.*

---

# RESULTS (Phase 4 execution)

Runner: `fxg_research_backtest_v1.py` (new file; imports the canonical engine unchanged,
adds costs + live sizer + split bookkeeping). Run: `python fxg_research_backtest_v1.py`.
Raw output: `C:\FXG\backtest_cache\research_20260612\results_grid_20260612T234616Z.json`.

**Filter→Dedupe order followed per FXG canonical rule** (window + setup conditions first, then
first-qualifying-per-day dedupe) in all 17 variants. Same-bar SL/TP resolved SL-first.

## All 17 variants — full period + OOS test

| Variant | Full n | Train n | Test n | PF full | PF test | Test exp $/trade | Max DD $ | Apr $ | May $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A\|EUR_USD\|rr2.0 | 36 | 29 | 7 | 0.839 | 0.245 | -123.14 | 2572 | -1304 | -304 |
| A\|EUR_USD\|rr3.0 | 36 | 29 | 7 | 0.576 | 0.000 | -186.57 | 3724 | -1304 | -748 |
| A\|EUR_USD\|rr4.0 | 36 | 29 | 7 | 0.670 | 0.000 | -186.57 | 3724 | -1304 | -748 |
| A\|USD_JPY\|rr2.0 | 29 | 25 | 4 | 1.096 | 0.000 | -160.00 | 1420 | -256 | -524 |
| A\|USD_JPY\|rr3.0 | 29 | 25 | 4 | 0.730 | 0.000 | -160.00 | 1978 | -1156 | -524 |
| A\|USD_JPY\|rr4.0 | 29 | 25 | 4 | 0.979 | 0.000 | -160.00 | 1680 | -1156 | -524 |
| A\|XAU_USD\|rr2.0 | 31 | 20 | 11 | 0.849 | 0.454 | -129.97 | 2662 | -910 | -501 |
| A\|XAU_USD\|rr3.0 | 31 | 20 | 11 | 0.946 | 0.341 | -157.24 | 3565 | -910 | -1101 |
| **A\|XAU_USD\|rr4.0** *(A finalist)* | 31 | 20 | 11 | 1.083 | 0.455 | -129.97 | 2968 | -910 | -1101 |
| B\|XAU_USD\|LON_OPEN\|atr1.0 | 8 | 6 | 2 | 0.408 | 2.873 | 289.43 | 1867 | -308 | 888 |
| B\|XAU_USD\|LON_OPEN\|atr1.5 | 8 | 6 | 2 | 0.416 | 2.941 | 293.40 | 1835 | -300 | 889 |
| B\|XAU_USD\|LON_OPEN\|atr2.0 | 8 | 6 | 2 | 0.881 | 2.884 | 286.85 | 1512 | -292 | 878 |
| B\|XAU_USD\|NY_OVERLAP\|atr1.0 | 33 | 25 | 8 | 1.437 | 0.960 | -9.23 | 2154 | 259 | 242 |
| **B\|XAU_USD\|NY_OVERLAP\|atr1.5** *(B finalist)* | 33 | 25 | 8 | 1.286 | 0.336 | -152.43 | 2127 | 293 | -909 |
| B\|XAU_USD\|NY_OVERLAP\|atr2.0 | 33 | 25 | 8 | 0.953 | 0.259 | -168.37 | 3403 | -891 | -1039 |
| C\|GBP_USD *(transfer)* | 13 | 10 | 3 | 0.557 | 0.890 | -14.81 | 1639 | -508 | -236 |
| C\|USD_JPY *(transfer)* | 10 | 8 | 2 | 1.360 | inf | 319.65 | 1160 | -145 | 411 |

## Finalist selection (frozen rule: highest TRAIN PF among variants with ≥20 train trades)

- **Candidate A → A\|XAU_USD\|rr4.0** (train PF 1.499, highest of the 9 A variants; all had ≥20 train trades)
- **Candidate B → B\|XAU_USD\|NY_OVERLAP\|atr1.5** (train PF 1.646; only NY_OVERLAP variants had ≥20 train trades — LON_OPEN had 6)
- **Candidate C → both GBP_USD and USD_JPY** judged as-is (pure transfer test, no selection)

## Gate-by-gate verdict (hard floors — not loosened)

| Gate | A: XAU_USD rr4.0 | B: XAU NY_OVERLAP atr1.5 | C: GBP_USD | C: USD_JPY |
|---|---|---|---|---|
| G1 ≥40 full & ≥15 test | ❌ 31 / 11 | ❌ 33 / 8 | ❌ 13 / 3 | ❌ 10 / 2 |
| G2 OOS PF≥1.4 & full PF≥1.5 | ❌ 0.46 / 1.08 | ❌ 0.34 / 1.29 | ❌ 0.89 / 0.56 | ❌ inf / 1.36 |
| G3 OOS expectancy > 0 | ❌ -$129.97 | ❌ -$152.43 | ❌ -$14.81 | ✅ +$319.65 |
| G4 Max DD ≤ $2,100 | ❌ $2,968 | ❌ $2,127 | ✅ $1,639 | ✅ $1,160 |
| G5 Apr≥0 AND May≥0 | ❌ -910 / -1101 | ❌ +293 / -909 | ❌ -508 / -236 | ❌ -145 / +411 |
| G6 Reproducibility | ✅ (identical re-run) | ✅ (identical re-run) | n/a | n/a |
| **RESULT** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |

Reproducibility (G6) confirmed for both finalists: a clean second process produced identical
trade counts and P&L (`A|XAU_USD|rr4.0`: n=31, +$545.59; `B|XAU_USD|NY_OVERLAP|atr1.5`: n=33,
+$1912.18). The harness is deterministic.

## Per-month P&L (full period, USD) — finalists and Candidate C

| Variant | Jan | Feb | Mar | **Apr** | **May** | Jun |
|---|---:|---:|---:|---:|---:|---:|
| A\|XAU_USD\|rr4.0 | 2628 | -1812 | 1769 | **-910** | **-1101** | -28 |
| B\|XAU_USD\|NY_OVERLAP\|atr1.5 | 2012 | 1134 | -308 | **+293** | **-909** | -311 |
| C\|GBP_USD | 272 | -405 | -322 | **-508** | **-236** | 192 |
| C\|USD_JPY | 410 | 331 | -817 | **-145** | **+411** | 229 |

No finalist is net-positive in **both** April and May. The closest, B's NY_OVERLAP family, holds
April but loses May; A holds neither.

## Reproduction command (for the record — applies to any variant)

```
cd "H:\My Drive\AI Trading\Gcloud system"
python fxg_backtest_setup.py --from 2026-01-01 --to 2026-06-12     # rebuild env
python fxg_research_backtest_v1.py                                  # full grid
python fxg_research_backtest_v1.py --variant "B|XAU_USD|NY_OVERLAP|atr1.0"   # single
```

## FINAL VERDICT: **NOTHING PROMOTED**

Zero of 17 variants cleared the promotion gates. The dominant, structural failure is **G1
(sample size)**: session-restricted, once-per-day-deduped strategies over a ~5.5-month span
produce only 8–36 trades full-period and 2–11 in the 30% OOS window — well short of the 40/15
floors. Layered on top, **no variant achieves OOS PF ≥1.4 with full PF ≥1.5 (G2)**, and **none is
net-positive in both April and May (G5)**.

Notable near-misses, recorded for honesty, none of which justify deviation:
- `B|XAU_USD|NY_OVERLAP|atr1.0` had the best full-period profile (PF 1.437, +$2,957, **both** Apr
  +259 and May +242 positive) — but full PF < 1.5, OOS PF 0.96 < 1.4, only 8 OOS trades, OOS
  expectancy negative, DD $2,154 > cap. It is *not* the B finalist anyway (lower train PF than atr1.5).
- `C|USD_JPY` was the only finalist with positive OOS expectancy (+$320), but on 2 OOS trades
  (n=10 full) — far below sample floors, and April negative.

Per the integrity rule, nothing was promoted. No gate was loosened, no split changed, no grid
expanded after seeing results. This is a complete, successful research run.

This finding is consistent with the 2026-06-10 canonical validation that failed the parent
lon_open_momentum_v1 family on the same kind of walk-forward criterion (2 of 5 months positive).
The session-momentum / single-daily-trigger archetype does not generate enough independent,
regime-robust trades on this instrument set and window to clear production gates.

### Recommendation for future sessions
- Sample size is the binding constraint. Either widen signal windows / allow multiple trades per
  day per instrument (changes the strategy archetype, needs fresh hypotheses), or extend the data
  span well beyond 5.5 months to grow the OOS count — both require a new pre-registered grid.
- `fxg_backtest_setup.py` + `fxg_research_backtest_v1.py` are now the reusable rails for that work.

