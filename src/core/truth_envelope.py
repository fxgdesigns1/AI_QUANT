from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass(frozen=True)
class TruthEnvelope:
    """Immutable truth metadata for dashboard payloads."""

    source: str
    freshness_ms: Optional[int]
    complete: bool
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    last_verified_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def live(
        cls,
        source: str = "control_plane",
        freshness_ms: Optional[int] = None,
        last_verified_at: Optional[str] = None,
        assumptions: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> "TruthEnvelope":
        return cls(
            source=source,
            freshness_ms=freshness_ms,
            complete=True,
            assumptions=assumptions or [],
            warnings=warnings or [],
            last_verified_at=last_verified_at,
        )

    @classmethod
    def cache(
        cls,
        source: str = "control_plane",
        freshness_ms: Optional[int] = None,
        last_verified_at: Optional[str] = None,
        assumptions: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> "TruthEnvelope":
        return cls(
            source=source,
            freshness_ms=freshness_ms,
            complete=True,
            assumptions=assumptions or [],
            warnings=warnings or [],
            last_verified_at=last_verified_at,
        )

    @classmethod
    def none(
        cls,
        source: str = "control_plane",
        reason: Optional[str] = None,
        assumptions: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        last_verified_at: Optional[str] = None,
    ) -> "TruthEnvelope":
        merged_warnings: List[str] = []
        if reason:
            merged_warnings.append(reason)
        if warnings:
            merged_warnings.extend(warnings)
        return cls(
            source=source,
            freshness_ms=None,
            complete=False,
            assumptions=assumptions or [],
            warnings=merged_warnings,
            last_verified_at=last_verified_at,
        )
