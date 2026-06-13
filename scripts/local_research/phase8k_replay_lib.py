"""
Phase 8K local research: replay-mode classification, session filtering, R-stats.

Pure logic only — no HTTP, no broker execution imports.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Sequence, Tuple

UTC = timezone.utc

ReplayMode = Literal[
    "exact_replay_possible",
    "exact_replay_blocked",
    "best_available_proxy_reconstruction",
]


def _parse_iso_utc(s: Any) -> Optional[datetime]:
    if s is None or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def parse_session_window_utc(spec: str) -> Tuple[int, int]:
    """
    Parse 'HH:MM-HH:MM' as UTC inclusive start, inclusive end window on the minute resolution.
    Returns (start_minutes_from_midnight, end_minutes_from_midnight).
    """
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$", spec)
    if not m:
        raise ValueError(f"invalid_session_window_utc:{spec!r}")
    sh, sm, eh, em = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    for v, name in ((sh, "start_h"), (sm, "start_m"), (eh, "end_h"), (em, "end_m")):
        if v < 0:
            raise ValueError(f"invalid_session_window_utc:{spec!r}:{name}")
    if sh > 23 or eh > 23 or sm > 59 or em > 59:
        raise ValueError(f"invalid_session_window_utc:{spec!r}:out_of_range")
    start_m = sh * 60 + sm
    end_m = eh * 60 + em
    return start_m, end_m


def minutes_since_midnight_utc(dt: datetime) -> int:
    d = dt.astimezone(UTC)
    return d.hour * 60 + d.minute


def candle_in_session_window(
    candle_time_utc: datetime,
    *,
    start_minutes: int,
    end_minutes: int,
) -> bool:
    """True if candle OPEN time (passed as candle_time_utc) falls inside [start, end] inclusive."""
    m = minutes_since_midnight_utc(candle_time_utc)
    return start_minutes <= m <= end_minutes


def filter_candles_session_window(
    candles: Sequence[Mapping[str, Any]],
    *,
    start_minutes: int,
    end_minutes: int,
    time_key: str = "time",
) -> List[Mapping[str, Any]]:
    out: List[Mapping[str, Any]] = []
    for c in candles:
        t = _parse_iso_utc(c.get(time_key))
        if t is None:
            continue
        if candle_in_session_window(t, start_minutes=start_minutes, end_minutes=end_minutes):
            out.append(c)
    return out


# --- Inventory / classification ---

_INVENTORY_CANDIDATE_KEYS = (
    "candidates",
    "archived_candidates",
    "entries",
    "rows",
)


def _iter_inventory_candidates(inv: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    for k in _INVENTORY_CANDIDATE_KEYS:
        v = inv.get(k)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return []


def _candidate_has_exact_replay_fields(row: Mapping[str, Any]) -> bool:
    """Heuristic: enough to simulate bar path without inventing levels."""
    time_fields = (
        "entry_time_utc",
        "open_time_utc",
        "signal_time_utc",
        "timestamp_utc",
        "ts_utc",
        "entry_ts",
    )
    has_time = any(row.get(f) for f in time_fields)
    px = row.get("entry_price") or row.get("open_price") or row.get("price")
    sl = row.get("stop_loss") or row.get("sl") or row.get("stopLoss")
    tp = row.get("take_profit") or row.get("tp") or row.get("takeProfit")
    side = row.get("direction") or row.get("side") or row.get("signal_side")
    inst = row.get("instrument") or row.get("pair") or row.get("symbol")
    return bool(has_time and px is not None and sl is not None and tp is not None and side and inst)


def load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def inventory_path_in_pack(input_pack: Path) -> Path:
    return input_pack / "ARTIFACTS" / "performance" / "latest_phase8h_archived_candidate_inventory.json"


def classify_replay_from_handoff_pack(
    input_pack: Path,
    *,
    instrument: str,
    session_bucket_substr: str,
) -> Tuple[bool, ReplayMode, str, int]:
    """
    Returns (exact_replay_possible, replay_mode, notes, candidate_count).
    """
    inv_p = inventory_path_in_pack(input_pack)
    inv = load_json_if_exists(inv_p)
    if inv is None:
        return (
            False,
            "best_available_proxy_reconstruction",
            f"missing_inventory:{inv_p.as_posix()}",
            0,
        )
    cands = _iter_inventory_candidates(inv)
    if not cands:
        return (
            False,
            "exact_replay_blocked",
            "inventory_empty_or_unrecognized_shape",
            0,
        )

    def matches_session(row: Mapping[str, Any]) -> bool:
        sb = row.get("session_bucket") or row.get("session") or row.get("session_key") or ""
        ins = row.get("instrument") or row.get("pair") or row.get("symbol") or ""
        if str(ins).upper() != instrument.upper():
            return False
        return session_bucket_substr.lower() in str(sb).lower()

    filtered = [c for c in cands if matches_session(c)]
    count = len(filtered)
    if count == 0:
        return (
            False,
            "best_available_proxy_reconstruction",
            f"no_candidates_for_{instrument}_{session_bucket_substr}",
            len(cands),
        )
    ok_rows = sum(1 for c in filtered if _candidate_has_exact_replay_fields(c))
    if ok_rows == count and count > 0:
        return (True, "exact_replay_possible", "all_filtered_rows_have_replay_fields", count)
    if ok_rows > 0:
        return (
            False,
            "exact_replay_blocked",
            f"partial_replay_fields:{ok_rows}/{count}",
            count,
        )
    return (
        False,
        "best_available_proxy_reconstruction",
        "candidates_present_but_missing_entry/sl/tp/side fields",
        count,
    )


# --- R simulation (bar path, conservative same-bar: SL wins if both touched) ---


def _f(x: Any) -> float:
    if x is None:
        return 0.0
    return float(x)


def normalize_side(raw: Any) -> str:
    s = str(raw or "").upper()
    if s in ("BUY", "LONG", "B", "1"):
        return "BUY"
    if s in ("SELL", "SHORT", "S", "-1"):
        return "SELL"
    return s


def extract_candidate_entry_time(row: Mapping[str, Any]) -> Optional[datetime]:
    for f in (
        "entry_time_utc",
        "open_time_utc",
        "signal_time_utc",
        "timestamp_utc",
        "ts_utc",
        "entry_ts",
    ):
        dt = _parse_iso_utc(row.get(f))
        if dt is not None:
            return dt
    return None


def _bar_duration_minutes(granularity: str) -> int:
    g = granularity.upper()
    if g == "M5":
        return 5
    if g == "M15":
        return 15
    if g == "H1":
        return 60
    return 15


def find_bar_index_for_entry(
    candles_chrono: Sequence[Mapping[str, Any]],
    entry_time: datetime,
    granularity: str = "M15",
) -> Optional[int]:
    """Index of candle whose interval contains entry_time (OANDA candle `time` = bar open)."""
    step = timedelta(minutes=_bar_duration_minutes(granularity))
    et = entry_time.astimezone(UTC)
    for i, c in enumerate(candles_chrono):
        t0 = _parse_iso_utc(c.get("time"))
        if t0 is None:
            continue
        if t0 <= et < t0 + step:
            return i
    return None


def replay_inventory_candidates_against_bars(
    candidates: Sequence[Mapping[str, Any]],
    candles_chrono: Sequence[Mapping[str, Any]],
    *,
    granularity: str = "M15",
    spread_half: float = 0.0,
    slippage: float = 0.0,
) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    for row in candidates:
        if not _candidate_has_exact_replay_fields(row):
            continue
        et = extract_candidate_entry_time(row)
        if et is None:
            continue
        idx = find_bar_index_for_entry(candles_chrono, et, granularity=granularity)
        if idx is None:
            continue
        entry = _f(row.get("entry_price") or row.get("open_price") or row.get("price"))
        sl = _f(row.get("stop_loss") or row.get("sl") or row.get("stopLoss"))
        tp = _f(row.get("take_profit") or row.get("tp") or row.get("takeProfit"))
        side = normalize_side(row.get("direction") or row.get("side") or row.get("signal_side"))
        bars_after = list(candles_chrono[idx:])
        outcome, exit_px, rmul = simulate_trade_r(
            side=side,
            entry=entry,
            stop_loss=sl,
            take_profit=tp,
            bars_after_entry=bars_after,
            spread_half=spread_half,
            slippage=slippage,
        )
        trades.append(
            {
                "entry_time_utc": et.isoformat().replace("+00:00", "Z"),
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "exit_price": exit_px,
                "direction": side,
                "outcome": outcome,
                "r_multiple": rmul,
                "candidate_id": row.get("id") or row.get("candidate_id") or row.get("key"),
                "replay_source": "archived_inventory",
            }
        )
    return trades


def simulate_trade_r(
    *,
    side: str,
    entry: float,
    stop_loss: float,
    take_profit: float,
    bars_after_entry: Sequence[Mapping[str, Any]],
    spread_half: float = 0.0,
    slippage: float = 0.0,
) -> Tuple[str, float, float]:
    """
    Walk forward OHLC bars after entry. Returns (outcome, exit_price, r_multiple).
    outcome: 'win'|'loss'|'breakeven'
    Long: SL if low <= sl_eff first on bar when both hit; TP if high >= tp_eff before SL.
    """
    su = str(side).upper()
    is_long = su in ("BUY", "LONG", "B")
    entry_eff = entry - slippage if is_long else entry + slippage
    sl_eff = stop_loss - spread_half if is_long else stop_loss + spread_half
    tp_eff = take_profit - spread_half if is_long else take_profit + spread_half
    risk = abs(entry_eff - sl_eff)
    if risk <= 0:
        return ("breakeven", entry_eff, 0.0)

    for b in bars_after_entry:
        hi = _f(b.get("h"))
        lo = _f(b.get("l"))
        if is_long:
            hit_sl = lo <= sl_eff
            hit_tp = hi >= tp_eff
            if hit_sl and hit_tp:
                return ("loss", sl_eff, -1.0)
            if hit_sl:
                return ("loss", sl_eff, -1.0)
            if hit_tp:
                rr = (tp_eff - entry_eff) / risk
                return ("win", tp_eff, rr)
        else:
            hit_sl = hi >= sl_eff
            hit_tp = lo <= tp_eff
            if hit_sl and hit_tp:
                return ("loss", sl_eff, -1.0)
            if hit_sl:
                return ("loss", sl_eff, -1.0)
            if hit_tp:
                rr = (entry_eff - tp_eff) / risk
                return ("win", tp_eff, rr)
    # No resolution — mark as open / use last close as neutral (research: count as breakeven at last close)
    last_c = _f(bars_after_entry[-1].get("c")) if bars_after_entry else entry_eff
    r = (last_c - entry_eff) / risk if is_long else (entry_eff - last_c) / risk
    if abs(r) < 1e-9:
        return ("breakeven", last_c, 0.0)
    return ("breakeven", last_c, r)


# --- Aggregation ---


def max_loss_streak(outcomes: Sequence[str]) -> int:
    streak = 0
    best = 0
    for o in outcomes:
        if o == "loss":
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def drawdown_proxy_r(r_sequence: Sequence[float]) -> float:
    """Peak-to-trough of cumulative R (negative number = max drawdown in R)."""
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_sequence:
        cum += float(r)
        peak = max(peak, cum)
        dd = cum - peak
        if dd < max_dd:
            max_dd = dd
    return float(max_dd)


def expectancy_r(r_multiples: Sequence[float]) -> float:
    if not r_multiples:
        return 0.0
    return float(sum(r_multiples) / len(r_multiples))


def profit_factor_r(r_multiples: Sequence[float]) -> float:
    wins = sum(r for r in r_multiples if r > 0)
    losses = -sum(r for r in r_multiples if r < 0)
    if losses <= 0:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def month_key_utc(dt: datetime) -> str:
    d = dt.astimezone(UTC)
    return f"{d.year:04d}-{d.month:02d}"


def aggregate_month_by_month(
    trades: Sequence[Mapping[str, Any]],
    *,
    time_field: str = "entry_time_utc",
) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[float]] = {}
    for t in trades:
        dt = _parse_iso_utc(t.get(time_field))
        if dt is None:
            continue
        mk = month_key_utc(dt)
        buckets.setdefault(mk, []).append(float(t.get("r_multiple") or 0.0))
    out: List[Dict[str, Any]] = []
    for mk in sorted(buckets.keys()):
        rs = buckets[mk]
        w = sum(1 for r in rs if r > 0)
        l_ = sum(1 for r in rs if r < 0)
        b = sum(1 for r in rs if r == 0)
        out.append(
            {
                "month_utc": mk,
                "trade_count": len(rs),
                "win_count": w,
                "loss_count": l_,
                "breakeven_count": b,
                "expectancy_r": expectancy_r(rs),
            }
        )
    return out


# --- ORB proxy inside session window (documented approximation) ---


@dataclass
class OrbProxyParams:
    """First M15 bar in session defines range; first breakout closes trade same day."""

    rr_multiple: float = 2.0


def build_daily_orb_proxy_trades(
    m15_candles_chrono: Sequence[Mapping[str, Any]],
    *,
    session_start_minutes: int,
    session_end_minutes: int,
    params: Optional[OrbProxyParams] = None,
    spread_half: float = 0.0,
    slippage: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    One trade per UTC day max. Uses first in-session bar as ORB; breakout of range on a later
    in-session bar triggers market entry at that bar's close, SL at opposite range bound, TP at rr_multiple R.
    """
    p = params or OrbProxyParams()
    by_date: Dict[date, List[Tuple[datetime, Mapping[str, Any]]]] = {}
    for c in m15_candles_chrono:
        t = _parse_iso_utc(c.get("time"))
        if t is None:
            continue
        if not candle_in_session_window(t, start_minutes=session_start_minutes, end_minutes=session_end_minutes):
            continue
        by_date.setdefault(t.date(), []).append((t, c))
    trades: List[Dict[str, Any]] = []
    for d, arr in sorted(by_date.items(), key=lambda x: x[0]):
        arr.sort(key=lambda x: x[0])
        if len(arr) < 2:
            continue
        t0, b0 = arr[0]
        range_hi = _f(b0.get("h"))
        range_lo = _f(b0.get("l"))
        if range_hi <= range_lo:
            continue
        entered = False
        for i in range(1, len(arr)):
            if entered:
                break
            _, bi = arr[i]
            cl = _f(bi.get("c"))
            # breakout at close of bar i
            side = None
            entry = cl
            if cl > range_hi:
                side = "BUY"
                sl = range_lo
                risk = entry - sl
                tp = entry + p.rr_multiple * risk
            elif cl < range_lo:
                side = "SELL"
                sl = range_hi
                risk = sl - entry
                tp = entry - p.rr_multiple * risk
            else:
                continue
            if risk <= 0:
                continue
            # forward bars from i+1 same day in session
            rest = [x[1] for x in arr[i + 1 :]]
            outcome, exit_px, rmul = simulate_trade_r(
                side=side,
                entry=entry,
                stop_loss=sl,
                take_profit=tp,
                bars_after_entry=rest,
                spread_half=spread_half,
                slippage=slippage,
            )
            trades.append(
                {
                    "entry_time_utc": arr[i][0].isoformat().replace("+00:00", "Z"),
                    "entry_price": entry,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "exit_price": exit_px,
                    "direction": side,
                    "outcome": outcome,
                    "r_multiple": rmul,
                    "proxy_rule": "ny_session_first_bar_orb_breakout_close",
                }
            )
            entered = True
    return trades
