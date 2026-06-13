"""
Phase 8L: Metrics aggregation — R-multiples, persistence, exclusions.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence

from scripts.local_research.phase8k_replay_lib import (  # noqa: E402
    aggregate_month_by_month,
    drawdown_proxy_r,
    expectancy_r,
    max_loss_streak,
    profit_factor_r,
    _parse_iso_utc,
)

UTC = timezone.utc


def daily_stats_from_trades(trades: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_day: Dict[str, List[float]] = defaultdict(list)
    for t in trades:
        dt = _parse_iso_utc(t.get("entry_time_utc"))
        if dt is None:
            continue
        dkey = dt.date().isoformat()
        by_day[dkey].append(float(t.get("r_multiple") or 0.0))
    out: List[Dict[str, Any]] = []
    for d in sorted(by_day.keys()):
        rs = by_day[d]
        w = sum(1 for r in rs if r > 0)
        l_ = sum(1 for r in rs if r < 0)
        b = sum(1 for r in rs if r == 0)
        out.append(
            {
                "day_utc": d,
                "trade_count": len(rs),
                "win_count": w,
                "loss_count": l_,
                "breakeven_count": b,
                "expectancy_r": expectancy_r(rs),
            }
        )
    return out


def compute_metrics_bundle(
    *,
    ny_trades: Sequence[Mapping[str, Any]],
    london_trades: Sequence[Mapping[str, Any]],
    news_available: bool,
    calendar_available: bool,
) -> Dict[str, Any]:
    def _one_bucket(trades: Sequence[Mapping[str, Any]], label: str) -> Dict[str, Any]:
        rmuls = [float(t.get("r_multiple") or 0.0) for t in trades]
        outcomes = [str(t.get("outcome") or "") for t in trades]
        wins = sum(1 for o in outcomes if o == "win")
        losses = sum(1 for o in outcomes if o == "loss")
        be = sum(1 for o in outcomes if o == "breakeven")
        excluded_news = sum(1 for t in trades if t.get("news_embargo_adjacent"))
        excluded_cal = sum(1 for t in trades if t.get("calendar_high_impact_adjacent"))
        clean = sum(1 for t in trades if t.get("clean_sample"))
        months = aggregate_month_by_month(list(trades), time_field="entry_time_utc")
        exp = expectancy_r(rmuls)
        pfr = profit_factor_r(rmuls)
        mls = max_loss_streak(outcomes)
        dd = drawdown_proxy_r(rmuls)
        wr = (wins / len(trades)) if trades else 0.0
        return {
            "session_bucket": label,
            "candidate_count": len(trades),
            "resolved_count": len(trades),
            "win_count": wins,
            "loss_count": losses,
            "breakeven_count": be,
            "win_rate": round(wr, 6) if trades else 0.0,
            "expectancy_r": round(exp, 6) if trades else 0.0,
            "profit_factor_r": (round(pfr, 6) if pfr != float("inf") else 999999.0) if trades else 0.0,
            "max_loss_streak": mls,
            "drawdown_proxy_r": round(dd, 6),
            "best_r": max(rmuls) if rmuls else 0.0,
            "worst_r": min(rmuls) if rmuls else 0.0,
            "daily_stats": daily_stats_from_trades(trades),
            "month_by_month_stats": months,
            "excluded_news_gated": excluded_news,
            "excluded_calendar_gated": excluded_cal,
            "excluded_missing_data": 0,
            "clean_sample_count": clean,
        }

    ny = _one_bucket(ny_trades, "NY_OPEN_SECONDARY_PROPOSED")
    ld = _one_bucket(london_trades, "LONDON_PRIMARY")

    ny_r = [float(t.get("r_multiple") or 0.0) for t in ny_trades]
    primary_expectancy = expectancy_r(ny_r) if ny_trades else 0.0
    primary_pf = profit_factor_r(ny_r) if ny_trades else 0.0
    primary_mls = max_loss_streak([str(t.get("outcome") or "") for t in ny_trades])
    primary_dd = drawdown_proxy_r(ny_r) if ny_trades else 0.0

    return {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "primary_session": "NY_OPEN_SECONDARY_PROPOSED",
        "news_reconstruction_available": news_available,
        "calendar_reconstruction_available": calendar_available,
        "ny": ny,
        "london": ld,
        "aggregate_primary_ny": {
            "candidate_count": ny["candidate_count"],
            "resolved_count": ny["resolved_count"],
            "win_count": ny["win_count"],
            "loss_count": ny["loss_count"],
            "breakeven_count": ny["breakeven_count"],
            "win_rate": ny["win_rate"],
            "expectancy_r": ny["expectancy_r"],
            "profit_factor_r": ny["profit_factor_r"],
            "max_loss_streak": ny["max_loss_streak"],
            "drawdown_proxy_r": ny["drawdown_proxy_r"],
            "excluded_news_gated": ny["excluded_news_gated"],
            "excluded_calendar_gated": ny["excluded_calendar_gated"],
            "excluded_missing_data": ny["excluded_missing_data"],
            "clean_sample_count": ny["clean_sample_count"],
        },
        "expectancy_r_primary_ny": primary_expectancy,
        "profit_factor_r_primary_ny": primary_pf,
        "max_loss_streak_primary_ny": primary_mls,
        "drawdown_proxy_r_primary_ny": primary_dd,
    }


def pick_recommendation(*, expectancy: float, resolved: int, months: List[Mapping[str, Any]]) -> str:
    if resolved < 12:
        return "NEEDS_MORE_REPLAY_DATA"
    pos_months = sum(1 for m in months if float(m.get("expectancy_r") or 0) > 0)
    if expectancy >= 0.2 and pos_months >= max(1, int(len(months) * 0.6)):
        return "PREPARE_PROMOTION_REVIEW_PACK"
    if expectancy > 0.05:
        return "CONTINUE_FORWARD_PAPER_REVIEW"
    if expectancy < -0.05:
        return "DOWNGRADE_RESEARCH_ONLY"
    return "NEEDS_MORE_REPLAY_DATA"
