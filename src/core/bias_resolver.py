"""Bias Resolver - hierarchical bias combination with provenance.

Combines:
- Outlook bias (roadmap / macro bias)
- Price action bias (48h move + slope)
- Regime bias (trend structure)

Goals:
- Survive a single OutlookEngine / credential failure.
- Preserve FAIL‑CLOSED when *all* sources are unavailable or neutral.
- Make every resolution step explainable and fully logged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BiasComponent:
    """Normalized bias component from a single source."""

    bias: Optional[str]  # "BULLISH" | "BEARISH" | None
    confidence: float
    source: str
    status: str = "ok"  # "ok" | "unavailable" | "error"
    details: Dict[str, Any] = None


@dataclass
class ResolvedBias:
    """Final resolved bias with full provenance."""

    bias: Optional[str]
    confidence: float
    sources: List[str]
    penalties: List[Dict[str, Any]]
    resolved_from: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bias": self.bias,
            "confidence": self.confidence,
            "sources": self.sources,
            "penalties": self.penalties,
            "resolved_from": self.resolved_from,
        }


def _agree_direction(components: List[BiasComponent]) -> Tuple[Optional[str], bool]:
    """
    Determine if all non‑null components agree on direction.

    Returns:
        (direction, agreement_ok)
    """
    dirs = {c.bias for c in components if c and c.bias is not None}
    if not dirs:
        return None, False
    if len(dirs) == 1:
        return dirs.pop(), True
    # Conflicting directions
    return None, False


def resolve_bias(
    outlook: Optional[BiasComponent],
    price_action: Optional[BiasComponent],
    regime: Optional[BiasComponent],
    *,
    min_confidence: float = 0.4,
) -> ResolvedBias:
    """
    Resolve final bias from three sources with explicit hierarchy.

    Priority:
    1. Outlook (if status == "ok" and bias set)
    2. Price action (if strong move AND agrees directionally)
    3. Regime (if direction known AND agrees)

    Rules:
    - If multiple sources available, they MUST agree directionally.
    - Confidence is the average of contributing sources with penalties:
        * -10% if Outlook unavailable
        * -10% if only 1 source contributes
    - If disagreement: bias=None, confidence=0.0, penalty recorded.
    """
    components: List[BiasComponent] = []
    penalties: List[Dict[str, Any]] = []

    if outlook:
        components.append(outlook)
    if price_action:
        components.append(price_action)
    if regime:
        components.append(regime)

    # Filter to contributing components (non‑null bias and status ok)
    contributors = [c for c in components if c.bias is not None and c.status == "ok"]

    if not contributors:
        # All sources unavailable or neutral
        penalties.append(
            {
                "type": "all_sources_unavailable_or_neutral",
                "message": "No bias from outlook/price_action/regime",
            }
        )
        return ResolvedBias(
            bias=None,
            confidence=0.0,
            sources=[c.source for c in components if c],
            penalties=penalties,
            resolved_from=[],
        )

    direction, ok = _agree_direction(contributors)
    if not ok or direction is None:
        penalties.append(
            {
                "type": "direction_conflict",
                "message": "Bias sources disagree on direction",
                "components": [{c.source: c.bias} for c in contributors],
            }
        )
        return ResolvedBias(
            bias=None,
            confidence=0.0,
            sources=[c.source for c in components if c],
            penalties=penalties,
            resolved_from=[],
        )

    # Compute base confidence as simple average from agreeing contributors
    if contributors:
        base_conf = sum(max(0.0, min(1.0, c.confidence)) for c in contributors) / len(
            contributors
        )
    else:
        base_conf = 0.0

    final_conf = base_conf

    # Penalty: Outlook unavailable (credential or engine failure)
    if outlook and outlook.status != "ok":
        penalties.append(
            {
                "type": "outlook_unavailable",
                "status": outlook.status,
                "message": "OutlookEngine unavailable; relying on secondary sources",
                "applied_factor": 0.9,
            }
        )
        final_conf *= 0.9

    # Penalty: only a single contributor
    if len(contributors) == 1:
        penalties.append(
            {
                "type": "single_source_only",
                "message": "Only one bias source contributed",
                "applied_factor": 0.9,
            }
        )
        final_conf *= 0.9

    final_conf = max(0.0, min(1.0, final_conf))

    resolved = ResolvedBias(
        bias=direction,
        confidence=round(final_conf, 3),
        sources=[c.source for c in contributors],
        penalties=penalties,
        resolved_from=[c.source for c in components if c],
    )

    # Final safety: if below min_confidence, treat as effectively neutral
    if resolved.confidence < min_confidence:
        penalties.append(
            {
                "type": "confidence_below_threshold",
                "threshold": min_confidence,
                "effective_confidence": resolved.confidence,
            }
        )
        return ResolvedBias(
            bias=None,
            confidence=resolved.confidence,
            sources=resolved.sources,
            penalties=penalties,
            resolved_from=resolved.resolved_from,
        )

    return resolved


def persist_bias_resolution(
    repo_root: Path,
    symbol: str,
    resolved: ResolvedBias,
    *,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Persist latest bias resolution snapshot for observability.

    Writes to:
        runtime/bias_resolution.json
    Overwrites atomically (no history; detailed history lives in audit log).
    """
    runtime_dir = repo_root / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path = runtime_dir / "bias_resolution.json"
    tmp = path.with_suffix(".tmp")

    payload: Dict[str, Any] = {
        "symbol": symbol,
        "resolved_bias": resolved.to_dict(),
        "context": context or {},
    }

    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    tmp.replace(path)

