"""
Phase 8L: Pure dataset transforms — candles, indicators, session labels, news/calendar flags.

No HTTP, no broker execution imports.
"""

from __future__ import annotations

import gzip
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from scripts.local_research.phase8k_replay_lib import (  # noqa: E402
    candle_in_session_window,
    parse_session_window_utc,
)
from scripts.local_research.oanda_mid_historical_fetch import parse_time_iso_utc  # noqa: E402

UTC = timezone.utc

SESSION_WINDOWS: Dict[str, str] = {
    "NY_OPEN_SECONDARY_PROPOSED": "13:30-16:00",
    "LONDON_PRIMARY": "07:00-10:30",
}


def load_jsonl_gz(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as gz:
        for line in gz:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("placeholder"):
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def load_alpha_export_manifest(export_dir: Path) -> Dict[str, Any]:
    p = export_dir / "phase8l_alpha_export_manifest.json"
    if not p.is_file():
        raise FileNotFoundError(f"missing_alpha_manifest:{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def candles_jsonl_gz_to_dataframe(rows: Sequence[Mapping[str, Any]], *, instrument: str, granularity: str) -> pd.DataFrame:
    times: List[Optional[datetime]] = []
    for r in rows:
        times.append(parse_time_iso_utc(r.get("time")))
    df = pd.DataFrame(
        {
            "time_utc": times,
            "o": [float(r.get("o") or 0) for r in rows],
            "h": [float(r.get("h") or 0) for r in rows],
            "l": [float(r.get("l") or 0) for r in rows],
            "c": [float(r.get("c") or 0) for r in rows],
            "volume": [int(r.get("volume") or 0) for r in rows],
        }
    )
    df = df.dropna(subset=["time_utc"])
    df = df.sort_values("time_utc").reset_index(drop=True)
    df["instrument"] = instrument
    df["granularity"] = granularity.upper()
    return df


def _session_label_for_ts(ts: datetime) -> str:
    ts = ts.astimezone(UTC)
    ny_lo, ny_hi = parse_session_window_utc(SESSION_WINDOWS["NY_OPEN_SECONDARY_PROPOSED"])
    ld_lo, ld_hi = parse_session_window_utc(SESSION_WINDOWS["LONDON_PRIMARY"])
    if candle_in_session_window(ts, start_minutes=ny_lo, end_minutes=ny_hi):
        return "NY_OPEN_SECONDARY_PROPOSED"
    if candle_in_session_window(ts, start_minutes=ld_lo, end_minutes=ld_hi):
        return "LONDON_PRIMARY"
    return "OFF_SESSION"


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["h"], df["l"], df["c"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta.clip(upper=0.0))
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _session_day(ts: datetime) -> date:
    return ts.astimezone(UTC).date()


def add_session_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["session_label"] = df["time_utc"].apply(_session_label_for_ts)
    df["session_day_utc"] = df["time_utc"].apply(_session_day)

    def _range_bounds(sub: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """Expanding session high/low within (day, session) plus session open/close."""
        range_hi = np.maximum.accumulate(sub["h"].values)
        range_lo = np.minimum.accumulate(sub["l"].values)
        first_o = sub["o"].iloc[0]
        last_c = sub["c"].iloc[-1]
        rh_s = pd.Series(range_hi, index=sub.index)
        rl_s = pd.Series(range_lo, index=sub.index)
        so = pd.Series(first_o, index=sub.index)
        sc = pd.Series(last_c, index=sub.index)
        return rh_s, rl_s, so, sc

    range_high = pd.Series(index=df.index, dtype=float)
    range_low = pd.Series(index=df.index, dtype=float)
    session_open = pd.Series(index=df.index, dtype=float)
    session_close = pd.Series(index=df.index, dtype=float)
    for (_ins, _day, lab), g in df.groupby(["instrument", "session_day_utc", "session_label"], sort=False):
        if lab == "OFF_SESSION":
            continue
        idx = g.index
        rh, rl, so, sc = _range_bounds(g)
        range_high.loc[idx] = rh.values
        range_low.loc[idx] = rl.values
        session_open.loc[idx] = so.values
        session_close.loc[idx] = sc.values
    df["range_high_session"] = range_high
    df["range_low_session"] = range_low
    df["session_open"] = session_open
    df["session_close"] = session_close
    return df


def _parse_event_time(row: Mapping[str, Any]) -> Optional[datetime]:
    for k in ("published_at", "date_utc", "time", "Date"):
        v = row.get(k)
        if not v:
            continue
        dt = parse_time_iso_utc(str(v)) if k == "published_at" else None
        if dt is None and isinstance(v, str):
            try:
                if len(v) == 10 and v[4] == "-":
                    dt = datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=UTC)
                else:
                    v2 = v.replace("Z", "+00:00") if v.endswith("Z") else v
                    dt = datetime.fromisoformat(v2)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    dt = dt.astimezone(UTC)
            except ValueError:
                continue
        if dt is not None:
            return dt
    return None


def build_event_blackouts(
    news_rows: Sequence[Mapping[str, Any]],
    cal_rows: Sequence[Mapping[str, Any]],
    *,
    window_minutes: int = 30,
) -> Tuple[List[Tuple[datetime, datetime]], List[Tuple[datetime, datetime]]]:
    news_blk: List[Tuple[datetime, datetime]] = []
    cal_blk: List[Tuple[datetime, datetime]] = []
    w = timedelta(minutes=window_minutes)
    for r in news_rows:
        t = _parse_event_time(r)
        if t is None:
            continue
        news_blk.append((t - w, t + w))
    for r in cal_rows:
        imp = str(r.get("importance") or r.get("impact") or "").lower()
        if imp and imp not in ("high", "3", "red"):
            continue
        t = _parse_event_time(r)
        if t is None:
            continue
        cal_blk.append((t - w, t + w))
    return news_blk, cal_blk


def label_embargo(df: pd.DataFrame, news_blk: List[Tuple[datetime, datetime]], cal_blk: List[Tuple[datetime, datetime]]) -> pd.DataFrame:
    df = df.copy()

    def in_any(ts: datetime, blocks: List[Tuple[datetime, datetime]]) -> bool:
        for a, b in blocks:
            if a <= ts <= b:
                return True
        return False

    df["news_embargo_adjacent"] = df["time_utc"].apply(lambda t: bool(in_any(t, news_blk)))
    df["calendar_high_impact_adjacent"] = df["time_utc"].apply(lambda t: bool(in_any(t, cal_blk)))
    df["embargo_or_degraded"] = df["news_embargo_adjacent"] | df["calendar_high_impact_adjacent"]
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["c"]
    df["bar_return"] = c.pct_change()
    df["rolling_volatility"] = df["bar_return"].rolling(20, min_periods=2).std()
    df["ema_20"] = c.ewm(span=20, adjust=False).mean()
    df["ema_50"] = c.ewm(span=50, adjust=False).mean()
    df["sma_20"] = c.rolling(20, min_periods=1).mean()
    df["sma_50"] = c.rolling(50, min_periods=1).mean()
    df["rsi_14"] = _compute_rsi(c, 14)
    df["atr_14"] = _compute_atr(df, 14)
    tr = pd.concat(
        [
            df["h"] - df["l"],
            (df["h"] - c.shift(1)).abs(),
            (df["l"] - c.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["adx_14"] = (tr.rolling(14).mean() / df["atr_14"]).clip(0, 100)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    df["macd"] = macd
    df["macd_signal"] = macd.ewm(span=9, adjust=False).mean()
    mid = df["sma_20"]
    std = c.rolling(20, min_periods=2).std()
    df["bollinger_upper"] = mid + 2 * std
    df["bollinger_lower"] = mid - 2 * std
    df["spread_proxy"] = (df["h"] - df["l"]).rolling(5, min_periods=1).mean()
    df["news_impact_score"] = np.where(df["news_embargo_adjacent"], 1.0, 0.0) + np.where(
        df["calendar_high_impact_adjacent"], 1.0, 0.0
    )
    return df


def build_dataset_from_alpha_export(
    *,
    export_dir: Path,
    primary_granularity: str = "M15",
    spread_pips: float = 1.0,
    slippage_pips: float = 0.5,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    manifest = load_alpha_export_manifest(export_dir)
    instruments = list(manifest.get("instruments") or [])
    granularities = list(manifest.get("granularities") or [])
    days = int(manifest.get("days_requested") or 14)

    news_path = export_dir / f"phase8l_news_context_{days}d.jsonl.gz"
    cal_path = export_dir / f"phase8l_calendar_context_{days}d.jsonl.gz"
    news_rows = load_jsonl_gz(news_path)
    cal_rows = load_jsonl_gz(cal_path)
    news_blk, cal_blk = build_event_blackouts(news_rows, cal_rows)

    frames: List[pd.DataFrame] = []
    missing_gaps: List[str] = []
    for ins in instruments:
        fname = f"phase8l_candles_{ins}_{primary_granularity.upper()}_{days}d.jsonl.gz"
        fp = export_dir / fname
        if not fp.is_file():
            missing_gaps.append(f"missing_file:{fname}")
            continue
        rows = load_jsonl_gz(fp)
        if not rows:
            missing_gaps.append(f"empty_candles:{fname}")
            continue
        dfc = candles_jsonl_gz_to_dataframe(rows, instrument=ins, granularity=primary_granularity)
        dfc = add_session_features(dfc)
        dfc = label_embargo(dfc, news_blk, cal_blk)
        dfc = add_indicators(dfc)
        pip = 0.0001 if "JPY" not in ins.upper() and "XAU" not in ins.upper() and "XAG" not in ins.upper() else 0.01
        dfc["spread_assumption_pips"] = float(spread_pips)
        dfc["slippage_assumption_pips"] = float(slippage_pips)
        dfc["pip_size"] = float(pip)
        frames.append(dfc)

    if not frames:
        raise RuntimeError("NO_DATASET_BUILT:missing_candles")

    out = pd.concat(frames, ignore_index=True).sort_values(["instrument", "time_utc"]).reset_index(drop=True)

    meta: Dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase": "Phase 8L",
        "classification": "RESEARCH_DATASET_LOCAL",
        "machine_role": "5950X",
        "source_alpha_export_manifest": str((export_dir / "phase8l_alpha_export_manifest.json").resolve()),
        "input_pack": None,
        "dataset_start_utc": out["time_utc"].min().isoformat().replace("+00:00", "Z"),
        "dataset_end_utc": out["time_utc"].max().isoformat().replace("+00:00", "Z"),
        "instruments": instruments,
        "granularities": [primary_granularity.upper()],
        "row_counts": {str(g): int(len(g)) for _, g in out.groupby("instrument")},
        "indicator_columns": [
            c
            for c in out.columns
            if c
            not in (
                "time_utc",
                "o",
                "h",
                "l",
                "c",
                "volume",
                "instrument",
                "granularity",
                "session_day_utc",
            )
        ],
        "news_reconstruction_available": bool(manifest.get("news_reconstruction_available")),
        "calendar_reconstruction_available": bool(manifest.get("calendar_reconstruction_available")),
        "session_windows": SESSION_WINDOWS,
        "missing_data_gaps": missing_gaps,
        "spread_slippage_assumptions": {
            "spread_pips": spread_pips,
            "slippage_pips_per_side": slippage_pips,
        },
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    return out, meta
