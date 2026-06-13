"""Regime Bias - directional bias derived from MarketRegimeDetector output.

This module provides a thin, explainable wrapper that turns regime analysis
into a directional bias signal that can participate in the bias hierarchy.

Non‑negotiables:
- NEVER fabricate a direction when the regime is UNKNOWN.
- If we cannot infer direction safely, bias MUST be None with confidence 0.0.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .market_regime import MarketRegime, RegimeAnalysis

logger = logging.getLogger(__name__)


@dataclass
class RegimeBiasResult:
    """Directional bias derived from regime analysis."""

    bias: Optional[str]  # "BULLISH", "BEARISH", or None
    confidence: float
    source: str = "regime_detector"
    metrics: Dict[str, Any] = None


class RegimeBias:
    """Convert RegimeAnalysis into a conservative directional bias."""

    def __init__(self) -> None:
        pass

    def from_analysis(
        self,
        instrument: str,
        analysis: RegimeAnalysis,
    ) -> RegimeBiasResult:
        """
        Map regime analysis into an optional directional bias.

        Contract:
        - If regime is UNKNOWN or CHOPPY -> bias=None (we refuse to guess).
        - If regime is TRENDING but we lack a safe way to infer direction,
          bias=None (no “trend up/down” fabrication).
        - Only when an explicit directional hint is present do we emit bias.
        """
        try:
            # Default: no bias
            bias: Optional[str] = None
            confidence: float = 0.0

            regime = analysis.regime

            # If we have no meaningful regime, do not participate
            if regime in (MarketRegime.UNKNOWN, MarketRegime.CHOPPY):
                metrics = {
                    "regime": regime.value if hasattr(regime, "value") else str(regime),
                    "adx": round(analysis.adx, 2),
                    "consistency": round(analysis.consistency, 3),
                    "volatility": round(analysis.volatility, 4),
                    "reason": "no_stable_trend",
                }
                return RegimeBiasResult(bias=None, confidence=0.0, metrics=metrics)

            # If regime is TRENDING or RANGING we still need direction.
            # Today RegimeAnalysis does NOT carry an explicit direction field.
            # To respect the Brutal Truth standard, we do NOT guess.
            direction = getattr(analysis, "direction", None)

            if direction in ("UP", "BULLISH"):
                bias = "BULLISH"
            elif direction in ("DOWN", "BEARISH"):
                bias = "BEARISH"

            if bias is None:
                # No explicit direction available – stay neutral.
                metrics = {
                    "regime": regime.value if hasattr(regime, "value") else str(regime),
                    "adx": round(analysis.adx, 2),
                    "consistency": round(analysis.consistency, 3),
                    "volatility": round(analysis.volatility, 4),
                    "reason": "direction_not_available",
                }
                return RegimeBiasResult(bias=None, confidence=0.0, metrics=metrics)

            # Confidence: anchored on ADX + consistency.
            # ADX >= 25 and consistency > 0.6 should already be true for TRENDING,
            # but we re‑use them to derive a 0.0‑1.0 confidence score.
            base_conf = 0.0
            if analysis.adx >= 25 and analysis.consistency > 0.6:
                base_conf = 0.7
            elif analysis.adx >= 20 and analysis.consistency > 0.55:
                base_conf = 0.5
            elif analysis.adx >= 18 and analysis.consistency > 0.5:
                base_conf = 0.3

            # Small bump for higher consistency.
            consistency_bonus = max(0.0, min(0.2, (analysis.consistency - 0.6)))
            confidence = max(0.0, min(1.0, base_conf + consistency_bonus))

            metrics = {
                "instrument": instrument,
                "regime": regime.value if hasattr(regime, "value") else str(regime),
                "adx": round(analysis.adx, 2),
                "consistency": round(analysis.consistency, 3),
                "volatility": round(analysis.volatility, 4),
                "base_confidence": round(base_conf, 3),
                "consistency_bonus": round(consistency_bonus, 3),
                "final_confidence": round(confidence, 3),
            }
            return RegimeBiasResult(
                bias=bias,
                confidence=round(confidence, 3),
                metrics=metrics,
            )
        except Exception as e:
            logger.error(
                "Error deriving regime bias for %s: %s", instrument, str(e),
                exc_info=True,
            )
            return RegimeBiasResult(
                bias=None,
                confidence=0.0,
                metrics={"error": str(e)},
            )

