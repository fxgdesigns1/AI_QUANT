# W23 Signal Forensics — Session Checkpoint
**Week:** 2–6 June 2026  
**Date saved:** 2026-06-09  
**Source file:** `backtest_results/untethered_2026-06-W23.csv`  
**Tool:** `scripts/probes/w23_signal_forensics.py`

---

## 1. Forensics Summary

| Metric | Value |
|---|---|
| Total W23 signals | 34 |
| Embargo hits | 6 (17.6%) |
| → Against news | 0 |
| → With news | 0 |
| → Neutral | 6 |
| No-timestamp skips | 0 |
| Overall win rate | 5.9% (2/34) |
| Overall loss rate | 82.4% (28/34) |
| Timeouts | 4 |

---

## 2. All 34 Raw Signals

Columns: date · time UTC · strategy · instrument · dir · session (backtest label) · in_window · outcome · R

| # | Date | Time UTC | Strategy | Instrument | Dir | Session | In Window | Outcome | R |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-06-02 | 05:00 | trend_pullback_v1#15 | AUD_JPY | LONG | LON_PRE | False | **WIN** | **+3.0** |
| 2 | 2026-06-02 | 05:00 | trend_pullback_v1#13 | EUR_NZD | LONG | LON_PRE | False | LOSS | -1.0 |
| 3 | 2026-06-02 | 06:00 | session_extreme_reversion_v2#1 | EUR_GBP | SHORT | LON_PRE | False | LOSS | -1.0 |
| 4 | 2026-06-02 | 10:00 | sweep_reclaim_reversal_v2#1 | EUR_AUD | LONG | LON_FLOW | True | TIMEOUT | +0.72 |
| 5 | 2026-06-02 | 13:30 | range_edge_v1#10 | USD_CAD | LONG | NY_OPEN | True | TIMEOUT | +1.43 |
| 6 | 2026-06-02 | 14:00 | trend_pullback_v1#3 | GBP_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 7 | 2026-06-02 | 15:00 | trend_pullback_v1#4 | EUR_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 8 | 2026-06-02 | 15:00 | sweep_reclaim_reversal_v2#2 | NZD_USD | SHORT | NY_OPEN | True | LOSS | -1.0 |
| 9 | 2026-06-03 | 05:45 | range_edge_v1#1 | GBP_USD | LONG | LON_PRE | False | LOSS | -1.0 |
| 10 | 2026-06-03 | 06:00 | range_edge_v1#2 | AUD_JPY | LONG | LON_PRE | False | LOSS | -1.0 |
| 11 | 2026-06-03 | 08:30 | trend_pullback_v1#4 | GBP_AUD | LONG | LON_FLOW | True | LOSS | -1.0 |
| 12 | 2026-06-03 | 13:45 | range_edge_v1#16 | GBP_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 13 | 2026-06-03 | 13:45 | range_edge_v1#10 | XAU_USD | LONG | NY_OPEN | True | TIMEOUT | -0.20 |
| 14 | 2026-06-03 | 14:00 | range_edge_v1#1 | AUD_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 15 | 2026-06-03 | 14:00 | range_edge_v1#1 | EUR_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 16 | 2026-06-03 | 14:00 | range_edge_v1#1 | NZD_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 17 | 2026-06-03 | 15:00 | sweep_reclaim_reversal_v2#1 | EUR_USD | SHORT | NY_OPEN | True | TIMEOUT | +1.17 |
| 18 | 2026-06-04 | 05:00 | range_edge_v1#2 | AUD_JPY | LONG | LON_PRE | False | LOSS | -1.0 |
| 19 | 2026-06-04 | 08:30 | trend_pullback_v1#11 | EUR_AUD | LONG | LON_FLOW | True | LOSS | -1.0 |
| 20 | 2026-06-04 | 09:00 | trend_pullback_v1#3 | EUR_JPY | LONG | LON_FLOW | True | **WIN** | **+3.0** |
| 21 | 2026-06-04 | 14:00 | trend_pullback_v1#4 | EUR_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 22 | 2026-06-04 | 14:00 | trend_pullback_v1#3 | GBP_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 23 | 2026-06-04 | 14:00 | trend_pullback_v1#4 | AUD_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 24 | 2026-06-05 | 06:00 | session_extreme_reversion_v2#1 | EUR_GBP | SHORT | LON_PRE | False | LOSS | -1.0 |
| 25 | 2026-06-05 | 06:00 | trend_pullback_v1#13 | EUR_NZD | LONG | LON_PRE | False | LOSS | -1.0 |
| 26 | 2026-06-05 | 08:45 | trend_pullback_v1#4 | GBP_AUD | LONG | LON_FLOW | True | LOSS | -1.0 |
| 27 | 2026-06-05 | 09:30 | range_edge_v1#13 | USD_CAD | LONG | LON_FLOW | True | LOSS | -1.0 |
| 28 | 2026-06-05 | 10:00 | trend_pullback_v1#19 | NZD_JPY | LONG | LON_FLOW | True | LOSS | -1.0 |
| 29 | 2026-06-05 | 13:30 | range_edge_v1#16 | GBP_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 30 | 2026-06-05 | 13:45 | range_edge_v1#10 | XAU_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 31 | 2026-06-05 | 14:00 | range_edge_v1#1 | AUD_USD | LONG | NY_OPEN | True | LOSS | -1.0 |
| 32 | 2026-06-05 | 14:00 | range_edge_v1#6 | EUR_JPY | LONG | NY_OPEN | True | LOSS | -1.0 |
| 33 | 2026-06-05 | 14:00 | range_edge_v1#5 | GBP_JPY | LONG | NY_OPEN | True | LOSS | -1.0 |
| 34 | 2026-06-05 | 14:00 | range_edge_v1#1 | NZD_USD | LONG | NY_OPEN | True | LOSS | -1.0 |

---

## 3. The 2 Winning Signals — Full Details

### Win #1 — AUD_JPY · trend_pullback_v1#15
| Field | Value |
|---|---|
| Date/Time UTC | 2026-06-02 05:00:00 |
| Date/Time BST | 2026-06-02 06:00 (pre-session) |
| Instrument | AUD_JPY |
| Strategy | trend_pullback_v1#15 |
| Direction | LONG |
| Entry | 114.423 |
| Stop loss | 114.3675 |
| Take profit | 114.5895 |
| R ratio | 3.0 |
| Outcome | **WIN +3.0R** |
| Regime | TRENDING |
| was_in_session_window | **False** |
| would_pass_cap_rules | True |
| Orchestrator score | 0.717 |
| Embargo status | CLEAR |

**Critical note:** This signal fired at 05:00 UTC (06:00 BST), which is before London open regardless of timezone interpretation. `was_in_session_window=False` — this trade would be **blocked** by the session gate in live execution. The best W23 result is a ghost trade.

---

### Win #2 — EUR_JPY · trend_pullback_v1#3
| Field | Value |
|---|---|
| Date/Time UTC | 2026-06-04 09:00:00 |
| Date/Time BST | 2026-06-04 10:00 |
| Instrument | EUR_JPY |
| Strategy | trend_pullback_v1#3 |
| Direction | LONG |
| Entry | 185.741 |
| Stop loss | 185.6848 |
| Take profit | 185.9095 |
| R ratio | 3.0 |
| Outcome | **WIN +3.0R** |
| Regime | TRENDING |
| was_in_session_window | **True** |
| would_pass_cap_rules | True |
| Orchestrator score | 0.8448 |
| Embargo status | CLEAR |

**Note:** This is the only "live-executable" winner. It fired in the DEAD_ZONE (08:00–09:30 UTC), specifically at 09:00 UTC = 10:00 BST, after the early London spread spike has typically settled. Highest orchestrator score of all 34 signals (0.8448).

---

## 4. The 6 Embargo Hits

All 6 are classified NEUTRAL direction (neither clearly with nor against USD move) because the events themselves were NEUTRAL-tagged in the calendar.

| # | Timestamp UTC | Instrument | Dir | Strategy | Event | Impact | Window | Offset | Status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-06-02 15:00 | EUR_USD | LONG | trend_pullback_v1#4 | ISM Manufacturing PMI | MEDIUM | ±30m | 0s | LOSS |
| 2 | 2026-06-02 15:00 | NZD_USD | SHORT | sweep_reclaim_reversal_v2#2 | ISM Manufacturing PMI | MEDIUM | ±30m | 0s | LOSS |
| 3 | 2026-06-05 13:30 | GBP_USD | LONG | range_edge_v1#16 | US Initial Jobless Claims | MEDIUM | ±30m | 0s | LOSS |
| 4 | 2026-06-05 13:45 | XAU_USD | LONG | range_edge_v1#10 | US Initial Jobless Claims | MEDIUM | ±30m | +900s | LOSS |
| 5 | 2026-06-05 14:00 | AUD_USD | LONG | range_edge_v1#1 | US Initial Jobless Claims | MEDIUM | ±30m | +1800s | LOSS |
| 6 | 2026-06-05 14:00 | NZD_USD | LONG | range_edge_v1#1 | US Initial Jobless Claims | MEDIUM | ±30m | +1800s | LOSS |

All 6 embargo hits resulted in **LOSS**. The embargo detection is working in the forensics tool, but the live gate is not filtering these — all 6 fired and lost.

**Notable:** NFP on 2026-06-06 (EXTREME impact, BULLISH, 172k vs 88k expected) did not catch any signals because no signals fired on Friday 6th. NFP embargo window would have covered 12:30–13:30 UTC.

---

## 5. Parity Audit Divergences

### 5a. BST/UTC Session Window Bug

The backtest `was_in_session_window` field exposes a clock mismatch between the backtest session labeling and the gate's UTC window boundaries.

| Session label | Signal times (UTC) | In-window? | BST equivalent |
|---|---|---|---|
| LON_PRE | 05:00–06:00 UTC | **False** | 06:00–07:00 BST |
| LON_FLOW | 08:30–10:00 UTC | **True** | 09:30–11:00 BST |
| NY_OPEN | 13:30–15:00 UTC | **True** | 14:30–16:00 BST |

**The bug:** In June, the UK is on BST (UTC+1). London market open is 08:00 BST = **07:00 UTC**. But the session gate's `was_in_session_window` starts registering `True` at 08:30 UTC = 09:30 BST — meaning the gate runs **1 hour behind** real London open.

Consequence: the first 60 minutes of the genuine London session (07:00–08:00 UTC) is treated as "out of window" by the gate. Signals in that band would be blocked in live trading even though London is open and liquid.

### 5b. Ghost-Trade Parity Divergence

8 of 34 signals (23.5%) have `was_in_session_window=False`. These are LON_PRE signals at 05:00–06:00 UTC. The **untethered** backtest executes them anyway. In a live-gated system they would all be blocked.

**Impact on reported performance:**
- Without ghost trades: 1/26 = 3.8% win rate (the EUR_JPY at 09:00 UTC)
- With ghost trades included: 2/34 = 5.9% win rate
- The AUD_JPY +3.0R win (best result of the week) is a ghost trade.

| Cohort | Signals | Wins | Losses | WR% |
|---|---|---|---|---|
| In-window (live-eligible) | 26 | 1 | 21 + 4 TO | 3.8% |
| Out-of-window (ghost trades) | 8 | 1 | 7 | 12.5% |

### 5c. Embargo Gate Not Applied

All 6 embargo-hit signals show `was_in_session_window=True` and fired anyway. The embargo filter exists in the forensics analysis tool but is not wired into the live execution gate. The gate only checks paper/live mode and kill-switch; no news embargo logic is present in `runner_src/core/execution_gate.py`.

---

## 6. Pass 3 — Session Bucket Win-Rate Analysis

Classification (UTC, priority order: DEAD_ZONE > LON_PRIMARY > NY_OVERLAP > OUTSIDE):
- **DEAD_ZONE:** 08:00–09:30 UTC (known coverage gap — first 90 min of London open in UTC, before spread normalises)
- **LON_PRIMARY:** 09:31–10:30 UTC
- **NY_OVERLAP:** 13:00–16:00 UTC
- **OUTSIDE:** everything else (pre-session, Asian hours)

```
Bucket          Sigs   WIN   LOSS   TO   WinRate%   ClearLoss
-------------------------------------------------------------
DEAD_ZONE          5     1      4    0      20.0%           4
LON_PRIMARY        2     0      1    1       0.0%           1
NY_OVERLAP        19     0     16    3       0.0%          10
OUTSIDE            8     1      7    0      12.5%           7
-------------------------------------------------------------
TOTAL             34     2     28    4       5.9%          22

CLEAR LOSSES breakdown (of 22 CLEAR+LOSS signals):
  OUTSIDE     :   7  (31.8%)
  DEAD_ZONE   :   4  (18.2%)
  LIVE windows:  11  (50.0%)  [LON_PRIMARY=1  NY_OVERLAP=10]
```

**Key readings:**
- **NY_OVERLAP is the volume crisis.** 19/34 signals (56%) fired there, all losing. 10 of 22 clear losses came from this window alone.
- **DEAD_ZONE beat OUTSIDE** on win rate (20% vs 12.5%), driven by the EUR_JPY win at 09:00 UTC.
- **50% of clear losses are in theoretically live windows** (LON_PRIMARY + NY_OVERLAP). The losses are not a gate misconfiguration artifact — the strategies themselves are losing in correct-hours execution.
- **6 losses were embargo hits** (28 total LOSS − 22 clear losses = 6 embargo losses). All embargo hits lost; none were filtered pre-trade.

---

## 7. Strategy-Level Breakdown

| Strategy | Signals | Wins | Losses | TO | WR% |
|---|---|---|---|---|---|
| range_edge_v1 | 16 | 0 | 14 | 2 | 0.0% |
| trend_pullback_v1 | 14 | 2 | 11 | 1 | 14.3% |
| sweep_reclaim_reversal_v2 | 3 | 0 | 2 | 1 | 0.0% |
| session_extreme_reversion_v2 | 1 | 0 | 1 | 0 | 0.0% |

`range_edge_v1` is responsible for 47% of all signals and 100% of the embargo hits (all 6 are range_edge). `trend_pullback_v1` is the only strategy with positive results (both wins).

---

## 8. Next Steps

- [ ] **Session breakdown analysis** — complete. Results captured in section 6 above.
- [ ] **Embargo gate integration** — wire `cross_reference_signal()` from `w23_signal_forensics.py` into `runner_src/core/execution_gate.py` as a pre-trade check. Block on EXTREME/HIGH impact events; warn on MEDIUM.
- [ ] **BST/UTC fix** — audit session window boundary definitions in the backtester and live gate. Replace hardcoded UTC boundaries with `pytz`/`zoneinfo` London-localised times so DST is handled automatically.
- [ ] **Ghost trade audit** — re-run backtest with `was_in_session_window=True` filter applied to get honest performance. Expected live-eligible win rate: ~3.8% (1/26).
- [ ] **range_edge_v1 review** — 0% win rate across 16 signals including 6 embargo hits during news events. Candidate for suspension pending parameter review.
- [ ] **NY_OVERLAP signal volume** — investigate why 19/34 signals concentrate at 13:30–15:00 UTC. Check if multiple instruments are triggering simultaneously on the same macro condition (correlated loss risk).
- [ ] **NFP signal absence** — confirm system correctly blocked all signals on 2026-06-06 (NFP day). No Friday signals appear in the CSV; verify the gate had NFP embargo active.
