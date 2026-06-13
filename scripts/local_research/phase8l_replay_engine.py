"""
Phase 8L: Replay / best-available proxy reconstruction (pure logic).

Uses Phase 8K replay primitives; adds session-bucket tagging and exclusion labels.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from scripts.local_research.phase8k_replay_lib import (  # noqa: E402
    OrbProxyParams,
    build_daily_orb_proxy_trades,
    classify_replay_from_handoff_pack,
    filter_candles_session_window,
    parse_session_window_utc,
    replay_inventory_candidates_against_bars,
    _iter_inventory_candidates,
    load_json_if_exists,
    inventory_path_in_pack,
)

SESSION_SPECS: Dict[str, str] = {
    "NY_OPEN_SECONDARY_PROPOSED": "13:30-16:00",
    "NY_OPEN": "13:30-16:00",
    "LONDON_PRIMARY": "07:00-10:30",
    "LONDON_OPEN": "07:00-10:30",
}


def _load_inventory_candidates_filtered(
    input_pack: Optional[Path],
    *,
    instrument: str,
    session_substr: str,
) -> List[Dict[str, Any]]:
    if input_pack is None or not input_pack.is_dir():
        return []
    inv = load_json_if_exists(inventory_path_in_pack(input_pack))
    if not inv:
        return []
    cands = _iter_inventory_candidates(inv)

    def matches(row: Dict[str, Any]) -> bool:
        sb = row.get("session_bucket") or row.get("session") or row.get("session_key") or ""
        ins = row.get("instrument") or row.get("pair") or row.get("symbol") or ""
        return str(ins).upper() == instrument.upper() and session_substr.lower() in str(sb).lower()

    return [c for c in cands if isinstance(c, dict) and matches(c)]


def candles_df_to_oanda_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        ts = r["time_utc"]
        rows.append(
            {
                "time": ts.isoformat().replace("+00:00", "Z"),
                "o": float(r["o"]),
                "h": float(r["h"]),
                "l": float(r["l"]),
                "c": float(r["c"]),
                "volume": int(r.get("volume") or 0),
            }
        )
    return rows


def _embargo_map(df: pd.DataFrame) -> Dict[str, Tuple[bool, bool]]:
    m: Dict[str, Tuple[bool, bool]] = {}
    for _, r in df.iterrows():
        ts = r["time_utc"]
        k = ts.isoformat().replace("+00:00", "Z")
        emb = bool(r.get("news_embargo_adjacent"))
        cal = bool(r.get("calendar_high_impact_adjacent"))
        m[k] = (emb, cal)
    return m


def run_replay_for_instrument(
    *,
    df_inst: pd.DataFrame,
    input_pack: Optional[Path],
    instrument: str,
    session_key: str,
    granularity: str,
    spread_pips: float,
    slippage_pips: float,
    rr_multiple: float,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    window = SESSION_SPECS.get(session_key, "13:30-16:00")
    start_m, end_m = parse_session_window_utc(window)
    df_sorted = df_inst.sort_values("time_utc")
    candles = candles_df_to_oanda_rows(df_sorted)
    pip = float(df_inst["pip_size"].iloc[0]) if "pip_size" in df_inst.columns else 0.0001
    spread_half = (spread_pips * pip) / 2.0
    slip = slippage_pips * pip
    embargo_by_time = _embargo_map(df_sorted)

    pack_path = input_pack if input_pack is not None and input_pack.is_dir() else Path("_missing_pack_")
    substr = "NY_OPEN" if "NY" in session_key else "LONDON"
    exact_ok, _replay_mode_base, notes, inv_count = classify_replay_from_handoff_pack(
        pack_path,
        instrument=instrument,
        session_bucket_substr=substr,
    )
    if input_pack is None or not input_pack.is_dir():
        exact_ok = False
        replay_mode_base = "best_available_proxy_reconstruction"
        notes = "input_pack_missing_or_invalid"
        inv_count = 0

    filtered_inv = _load_inventory_candidates_filtered(
        input_pack,
        instrument=instrument,
        session_substr=substr,
    )

    in_win = filter_candles_session_window(candles, start_minutes=start_m, end_minutes=end_m)

    ran_exact = False
    trades: List[Dict[str, Any]] = []
    if exact_ok and filtered_inv:
        trades = replay_inventory_candidates_against_bars(
            filtered_inv,
            candles,
            granularity=granularity,
            spread_half=spread_half,
            slippage=slip,
        )
        if len(trades) > 0:
            ran_exact = True

    if not ran_exact:
        trades = build_daily_orb_proxy_trades(
            candles,
            session_start_minutes=start_m,
            session_end_minutes=end_m,
            params=OrbProxyParams(rr_multiple=rr_multiple),
            spread_half=spread_half,
            slippage=slip,
        )
        replay_mode = "best_available_proxy_reconstruction"
    else:
        replay_mode = "exact_replay_possible"

    def enrich(tr: Dict[str, Any]) -> Dict[str, Any]:
        et = str(tr.get("entry_time_utc") or "")
        emb, cal = embargo_by_time.get(et, (False, False))
        clean = not (emb or cal)
        out = dict(tr)
        out["session_bucket"] = session_key
        out["news_embargo_adjacent"] = emb
        out["calendar_high_impact_adjacent"] = cal
        out["clean_sample"] = clean
        out["execution_instruction_emulated"] = "WAIT" if emb or cal else "RESEARCH_ONLY"
        return out

    enriched = [enrich(t) for t in trades]
    meta = {
        "session_key": session_key,
        "session_window_utc": window,
        "replay_mode": replay_mode,
        "exact_replay_possible": ran_exact,
        "classification_notes": notes,
        "inventory_candidate_count": inv_count,
        "in_session_candles": len(in_win),
    }
    return enriched, meta


def run_full_replay(
    *,
    dataset: pd.DataFrame,
    input_pack: Optional[Path],
    instrument: str,
    granularity: str,
    spread_pips: float,
    slippage_pips: float,
    rr_multiple: float,
) -> Dict[str, Any]:
    df_i = dataset[dataset["instrument"].str.upper() == instrument.upper()].copy()
    if df_i.empty:
        raise RuntimeError(f"NO_ROWS_FOR_INSTRUMENT:{instrument}")

    ny_trades, ny_meta = run_replay_for_instrument(
        df_inst=df_i,
        input_pack=input_pack,
        instrument=instrument,
        session_key="NY_OPEN_SECONDARY_PROPOSED",
        granularity=granularity,
        spread_pips=spread_pips,
        slippage_pips=slippage_pips,
        rr_multiple=rr_multiple,
    )
    ld_trades, ld_meta = run_replay_for_instrument(
        df_inst=df_i,
        input_pack=input_pack,
        instrument=instrument,
        session_key="LONDON_PRIMARY",
        granularity=granularity,
        spread_pips=spread_pips,
        slippage_pips=slippage_pips,
        rr_multiple=rr_multiple,
    )
    return {
        "ny_session": {"trades": ny_trades, "meta": ny_meta},
        "london_session": {"trades": ld_trades, "meta": ld_meta},
    }
