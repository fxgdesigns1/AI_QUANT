#!/usr/bin/env python3
"""
fxg_backtest_setup.py — FXG one-click backtest environment builder.

Rebuilds / verifies the local backtest environment for a requested date range:
  1. Ensures candle cache coverage in C:\\FXG\\backtest_cache (fetching only what
     is missing via the repo's canonical OANDA fetcher — no parallel HTTP path).
  2. Validates data quality (no >4h gaps on weekday trading sessions).
  3. Runs condensed parity checks against the live-ALPHA-synced files in this repo
     (position_sizer minimums, direction_detector SMA 8/20, session windows).
  4. Prints a readiness summary and writes a JSON setup log.

Usage:
  python fxg_backtest_setup.py --from 2026-01-01 --to 2026-06-12
  python fxg_backtest_setup.py --from 2025-10-01 --to 2026-06-12 --instruments EUR_USD,AUD_JPY,XAU_USD

Design rules (FXG):
  - OANDA credentials come from the repo's existing .env (OANDA_API_KEY / OANDA_ENV).
    Never hardcoded, never printed.
  - Canonical fetcher: scripts/local_research/oanda_mid_historical_fetch.py
  - Idempotent: a second run with the same args fetches nothing and produces the
    same canonical cache files.
  - Fails loudly: any fetch/validation error exits non-zero with the reason.
  - Symbol format: OANDA underscore (AUD_JPY).
  - Timeframes: M15 + H1 (the canonical engine fxg_lon_momentum_engine.py is
    M15-native; all existing cache and validation history is M15/H1).

Canonical cache layout written by this script:
  C:\\FXG\\backtest_cache\\{INST}_{GRAN}_canon.csv   (merged, sorted, deduped)
Legacy files ({INST}_{GRAN}_q1/_april/_full.csv) are read as local sources first
so already-downloaded history is never re-fetched. They are left untouched.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CACHE = Path(r"C:\FXG\backtest_cache")
GRANULARITIES = ["M15", "H1"]
DEFAULT_INSTRUMENTS = [
    # existing champions
    "EUR_USD", "AUD_JPY", "EUR_AUD", "NZD_USD", "NZD_JPY",
    # candidate C targets
    "USD_JPY", "GBP_USD",
    # candidate B target
    "XAU_USD",
]
LEGACY_SUFFIXES = ["q1", "april", "full", ""]  # "" = unsuffixed partial pulls

# Canonical session windows (UTC) — must match live ALPHA trading_windows.py and
# the canonical engine. Verified in FXG_BACKTEST_ENV_AUDIT_2026-06-12.md.
SESSION_WINDOWS_UTC = {
    "LON_OPEN":   ("08:00", "09:30"),
    "LON_FLOW":   ("09:30", "11:00"),
    "NY_OVERLAP": ("13:00", "16:00"),
    "LON_SIGNAL": ("08:00", "08:30"),  # lon_open_momentum signal window
    "NY_SIGNAL":  ("13:30", "14:00"),  # ny_open_momentum signal window
}

UTC = timezone.utc


def load_repo_env() -> None:
    """Load OANDA creds from the repo's existing .env (the same file the rest of
    the repo's local tooling uses). Values are exported to os.environ only;
    never printed."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def parse_t(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1]
    if "." in s:
        head, frac = s.split(".", 1)
        s = head + "." + frac[:6]
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def read_candles_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    return rows


def canon_path(inst: str, gran: str) -> Path:
    return CACHE / f"{inst}_{gran}_canon.csv"


def collect_local(inst: str, gran: str) -> dict[str, dict]:
    """Merge all local files for instrument/granularity into {time: row}."""
    merged: dict[str, dict] = {}
    candidates = [canon_path(inst, gran)]
    for sfx in LEGACY_SUFFIXES:
        name = f"{inst}_{gran}_{sfx}.csv" if sfx else f"{inst}_{gran}.csv"
        candidates.append(CACHE / name)
    for p in candidates:
        if not p.exists():
            continue
        for row in read_candles_csv(p):
            t = row.get("time", "")
            if t and t not in merged:
                merged[t] = {
                    "time": t,
                    "o": row["o"], "h": row["h"], "l": row["l"], "c": row["c"],
                    "volume": row.get("volume", "0"),
                }
    return merged


def find_missing_ranges(times: list[datetime], t_from: datetime, t_to: datetime,
                        gran: str) -> list[tuple[datetime, datetime]]:
    """Return sub-ranges of [t_from, t_to] not covered by existing candles.
    'Covered' tolerance: a hole is only fetch-worthy if wider than 6h (avoids
    refetching weekend/holiday closures every run while still catching real holes)."""
    if not times:
        return [(t_from, t_to)]
    times = sorted(times)
    holes: list[tuple[datetime, datetime]] = []
    tol = timedelta(hours=6)
    # Leading/trailing tolerance is 72h: range edges commonly land on holidays
    # (e.g. Jan 1) or weekends where no candles can ever exist; a hole that can
    # never fill would otherwise trigger a no-op fetch on every run.
    edge_tol = timedelta(hours=72)
    if times[0] - t_from > edge_tol:
        holes.append((t_from, times[0]))
    def _spans_weekend(a: datetime, b: datetime) -> bool:
        """True if any Saturday falls inside (a, b) — covers normal weekends and
        long holiday closures (e.g. Good Friday -> Sunday reopen). Such holes can
        never fill, so re-fetching them every run is pointless."""
        d = a.date()
        while d <= b.date():
            if d.weekday() == 5 and a.date() <= d <= b.date():
                return True
            d += timedelta(days=1)
        return False

    prev = times[0]
    for t in times[1:]:
        if t - prev > tol:
            if not _spans_weekend(prev, t):
                holes.append((prev, t))
        prev = t
    if t_to - times[-1] > edge_tol:
        holes.append((times[-1], t_to))
    return holes


def weekday_gaps(times: list[datetime], max_gap_h: float = 4.0) -> list[tuple[str, str, float]]:
    gaps = []
    times = sorted(times)
    for a, b in zip(times, times[1:]):
        d = b - a
        if d > timedelta(hours=max_gap_h):
            if a.weekday() == 4 and b.weekday() in (6, 0):
                continue  # weekend
            gaps.append((a.isoformat(), b.isoformat(), round(d.total_seconds() / 3600, 1)))
    return gaps


def write_canon(inst: str, gran: str, merged: dict[str, dict]) -> int:
    rows = sorted(merged.values(), key=lambda r: parse_t(r["time"]))
    out = canon_path(inst, gran)
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "o", "h", "l", "c", "volume"])
        for r in rows:
            w.writerow([r["time"], r["o"], r["h"], r["l"], r["c"], r["volume"]])
    return len(rows)


def ensure_instrument(inst: str, gran: str, t_from: datetime, t_to: datetime,
                      fetcher, log: dict) -> dict:
    merged = collect_local(inst, gran)
    in_range = {t: r for t, r in merged.items() if t_from <= parse_t(t) <= t_to}
    times_in_range = sorted(parse_t(t) for t in in_range)
    holes = find_missing_ranges(times_in_range, t_from, t_to, gran)

    fetched_rows = 0
    if holes:
        for h_from, h_to in holes:
            print(f"  [FETCH] {inst} {gran}: {h_from.date()} -> {h_to.date()}")
            candles = fetcher(inst, gran, h_from, h_to)
            for c in candles:
                t = str(c["time"])
                if t not in merged:
                    merged[t] = {"time": t, "o": c["o"], "h": c["h"],
                                 "l": c["l"], "c": c["c"], "volume": c.get("volume", 0)}
                    fetched_rows += 1
    total = write_canon(inst, gran, merged)

    in_range_times = sorted(parse_t(t) for t in merged if t_from <= parse_t(t) <= t_to)
    gaps = weekday_gaps(in_range_times)
    status = {
        "instrument": inst, "granularity": gran,
        "rows_total": total,
        "rows_in_range": len(in_range_times),
        "fetched_new": fetched_rows,
        "first": in_range_times[0].isoformat() if in_range_times else None,
        "last": in_range_times[-1].isoformat() if in_range_times else None,
        "weekday_gaps_gt4h": gaps,
    }
    if not in_range_times:
        raise RuntimeError(f"{inst} {gran}: no data in requested range after fetch — UNAVAILABLE")
    return status


def parity_check_position_sizer() -> tuple[bool, str]:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from src.core.position_sizer import calculate_lots  # noqa
        checks = [
            # (desc, result, expect_valid)
            ("forex 2pip rejected", calculate_lots("EURUSD", 1.10000, 1.09980).valid, False),
            ("forex 4pip valid", calculate_lots("EURUSD", 1.10000, 1.09960).valid, True),
            ("jpy 2pip rejected", calculate_lots("USDJPY", 155.000, 154.980).valid, False),
            ("xau $1 rejected", calculate_lots("XAUUSD", 4000.0, 4001.0).valid, False),
            ("xau $2 valid", calculate_lots("XAUUSD", 4000.0, 4002.0).valid, True),
        ]
        for desc, got, want in checks:
            if got != want:
                return False, f"position_sizer parity FAIL: {desc} (got valid={got})"
        r = calculate_lots("XAUUSD", 2000.0, 2005.0)
        if not (r.capped and abs(r.lots - 0.5) < 1e-9):
            return False, "position_sizer parity FAIL: XAUUSD 0.5-lot hard cap missing"
        r2 = calculate_lots("EURUSD", 1.10000, 1.09950)
        if not (r2.capped and abs(r2.lots - 2.0) < 1e-9):
            return False, "position_sizer parity FAIL: forex 2.0-lot hard cap missing"
        import inspect
        from src.core import position_sizer as ps
        if "risk_usd: float = 300.0" not in inspect.getsource(ps):
            return False, "position_sizer parity FAIL: $300 default risk not found"
        return True, "min SLs (3pip fx / 3pip jpy / $1.50 xau), caps (2.0 / 0.5), $300 risk OK"
    except Exception as e:
        return False, f"position_sizer parity FAIL: {e}"


def parity_check_direction_detector() -> tuple[bool, str]:
    p = REPO_ROOT / "src" / "control_plane" / "direction_detector.py"
    if not p.exists():
        return False, "direction_detector.py missing from repo"
    src = p.read_text(encoding="utf-8", errors="replace")
    needed = ["closes[-8:]) / 8", "closes[-20:]) / 20",
              "slow * 1.0001", "slow * 0.9999", 'granularity="H1"', "CACHE_TTL = 300"]
    missing = [n for n in needed if n not in src]
    if missing:
        return False, f"direction_detector parity FAIL: missing {missing}"
    return True, "SMA 8/20 H1, x1.0001/x0.9999 thresholds, 5-min cache OK"


def parity_check_session_windows() -> tuple[bool, str]:
    """Engine signal window must equal canonical LON_SIGNAL window."""
    eng = CACHE / "fxg_lon_momentum_engine.py"
    if not eng.exists():
        return False, "canonical engine missing from cache dir"
    src = eng.read_text(encoding="utf-8", errors="replace")
    if '"window_start_hm": 480' not in src or '"window_end_hm":   510' not in src:
        return False, "engine LON signal window != 08:00-08:30 UTC"
    return True, "engine LON signal 08:00-08:30; canonical windows " + \
        ", ".join(f"{k} {a}-{b}" for k, (a, b) in SESSION_WINDOWS_UTC.items())


def main() -> int:
    ap = argparse.ArgumentParser(description="FXG one-click backtest environment builder")
    ap.add_argument("--from", dest="t_from", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", dest="t_to", required=True, help="YYYY-MM-DD")
    ap.add_argument("--instruments", default=",".join(DEFAULT_INSTRUMENTS),
                    help="comma-separated OANDA symbols (underscore format)")
    args = ap.parse_args()

    t_from = datetime.fromisoformat(args.t_from).replace(tzinfo=UTC)
    t_to = datetime.fromisoformat(args.t_to).replace(tzinfo=UTC) + timedelta(hours=23, minutes=59)
    instruments = [i.strip() for i in args.instruments.split(",") if i.strip()]
    for inst in instruments:
        if not re.fullmatch(r"[A-Z]{3}_[A-Z]{3}", inst):
            print(f"ERROR: instrument '{inst}' is not OANDA underscore format (e.g. AUD_JPY)")
            return 2

    CACHE.mkdir(parents=True, exist_ok=True)
    load_repo_env()
    if not os.getenv("OANDA_API_KEY"):
        print("ERROR: OANDA_API_KEY not available from repo .env or environment")
        return 2

    # canonical fetcher — the repo's only sanctioned OANDA candle path
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "local_research"))
    from oanda_mid_historical_fetch import fetch_oanda_mid_candles_range

    print(f"FXG backtest setup: {args.t_from} -> {args.t_to}  instruments={','.join(instruments)}")
    print(f"Cache: {CACHE}\n")

    log: dict = {
        "run_utc": datetime.now(UTC).isoformat(),
        "range": {"from": args.t_from, "to": args.t_to},
        "instruments": {},
        "parity": {},
    }
    failures: list[str] = []

    for inst in instruments:
        log["instruments"][inst] = {}
        for gran in GRANULARITIES:
            try:
                st = ensure_instrument(inst, gran, t_from, t_to,
                                       fetch_oanda_mid_candles_range, log)
                log["instruments"][inst][gran] = st
                gap_n = len(st["weekday_gaps_gt4h"])
                mark = "OK " if gap_n == 0 else "WARN"
                extra = f" fetched {st['fetched_new']} new" if st["fetched_new"] else " cached"
                print(f"[{mark}] {inst} {gran}: {st['first'][:10]} -> {st['last'][:10]}"
                      f" ({st['rows_in_range']} bars{extra}, gaps>4h={gap_n})")
                if gap_n:
                    for g in st["weekday_gaps_gt4h"][:5]:
                        print(f"        gap {g[0]} -> {g[1]} ({g[2]}h)")
            except Exception as e:
                msg = f"{inst} {gran}: {e}"
                failures.append(msg)
                log["instruments"][inst][gran] = {"error": str(e)}
                print(f"[FAIL] {msg}")

    print("\nParity checks (live-ALPHA-synced files):")
    for name, fn in [("position_sizer", parity_check_position_sizer),
                     ("direction_detector", parity_check_direction_detector),
                     ("session_windows", parity_check_session_windows)]:
        ok, detail = fn()
        log["parity"][name] = {"ok": ok, "detail": detail}
        print(f"  {'PASS' if ok else 'FAIL'} {name}: {detail}")
        if not ok:
            failures.append(f"parity:{name}: {detail}")

    verdict = "READY" if not failures else "NOT_READY"
    log["verdict"] = verdict
    log["failures"] = failures

    stamp = datetime.now(UTC).strftime("%Y%m%d")
    log_path = CACHE / f"setup_log_{stamp}.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"\nSetup log: {log_path}")
    print(f"VERDICT: {verdict}" + ("" if verdict == "READY" else f" — {len(failures)} failure(s)"))
    return 0 if verdict == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
