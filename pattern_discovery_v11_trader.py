#!/usr/bin/env python3
"""
Pattern Discovery v11 trading service.

This standalone script wraps the core `AITradingSystem` infrastructure but
swaps in the pattern discovery signal engine derived from the v11 optimisation
results. It is designed to run on the Google Cloud VM against the dedicated
practice account `101-004-30719775-006`.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from ai_trading_system import AITradingSystem, OANDA_API_KEY

CONFIG_PATH = Path("/opt/quant_system_clean/pattern_discovery_v11_config.json")
ACCOUNT_ID = "101-004-30719775-006"
SL_PCT = 0.002  # 0.2%
TP_PCT = 0.003  # 0.3%
EMA_FAST = 8
EMA_SLOW = 21
EMA_SIGNAL = 3
RSI_PERIOD = 14
MOMENTUM_LOOKBACK = 5

logger = logging.getLogger("pattern_discovery_v11")


def _compute_ema(values: List[float], period: int) -> float:
    if not values or len(values) < period:
        return 0.0
    k = 2 / (period + 1)
    ema = values[0]
    for price in values[1:]:
        ema = price * k + ema * (1 - k)
    return float(ema)


def _compute_rsi(values: List[float], period: int = RSI_PERIOD) -> float:
    if len(values) <= period:
        return 50.0
    gains = []
    losses = []
    for i in range(-period, 0):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains.append(change)
        else:
            losses.append(abs(change))
    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss if avg_loss else math.inf
    return 100 - (100 / (1 + rs))


def _compute_momentum(values: List[float], lookback: int = MOMENTUM_LOOKBACK) -> float:
    if len(values) <= lookback:
        return 0.0
    base = values[-lookback]
    if base == 0:
        return 0.0
    return (values[-1] - base) / base


def _round_price(symbol: str, price: float) -> str:
    if symbol in {"EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD"}:
        return f"{price:.5f}"
    if symbol == "USD_JPY":
        return f"{price:.3f}"
    if symbol == "XAU_USD":
        return f"{price:.2f}"
    return f"{price:.5f}"


class PatternDiscoveryV11System(AITradingSystem):
    def __init__(self) -> None:
        self.pattern_filters = self._load_filters()
        super().__init__()
        self.account_id = ACCOUNT_ID
        self.headers["Authorization"] = f"Bearer {OANDA_API_KEY}"
        self.instruments = list(self.pattern_filters.keys())
        self.risk_per_trade = 0.01
        self.base_risk = self.risk_per_trade
        self.max_daily_trades = 50
        self.max_concurrent_trades = 10
        self.per_symbol_cap = {symbol: 2 for symbol in self.instruments}
        self.per_symbol_cap["XAU_USD"] = 1
        self.reserve_slots_for_diversification = 2
        self.max_units_per_instrument.update(
            {
                "EUR_USD": 75000,
                "GBP_USD": 75000,
                "AUD_USD": 75000,
                "NZD_USD": 50000,
                "USD_JPY": 200000,
                "XAU_USD": 300,
            }
        )
        self.daily_trade_count = 0
        logger.info("Pattern Discovery v11 system initialised for account %s", self.account_id)

    def _load_filters(self) -> Dict[str, Dict[str, float]]:
        if not CONFIG_PATH.is_file():
            logger.warning("Pattern config missing at %s", CONFIG_PATH)
            return {}
        try:
            payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to load pattern config: %s", exc)
            return {}
        filters: Dict[str, Dict[str, float]] = {}
        for instrument, cfg in payload.items():
            meta = cfg.get("ultra_filters", {})
            filters[instrument] = {
                "rsi_min": float(meta.get("rsi_min", 0.0)),
                "rsi_max": float(meta.get("rsi_max", 100.0)),
                "min_momentum": float(meta.get("min_momentum", 0.0)),
                "min_ema_separation": float(meta.get("min_ema_separation", 0.0)),
                "best_hours": meta.get("best_hours", []),
            }
        return filters

    # Override to use pattern logic
    def analyze_market(self, prices: Dict[str, Dict[str, float]]):
        signals = []
        now_hour = datetime.utcnow().hour
        for instrument in self.instruments:
            config = self.pattern_filters.get(instrument)
            price_data = prices.get(instrument)
            if not config or not price_data:
                continue

            hours = config.get("best_hours") or []
            if hours and now_hour not in hours:
                continue

            candles = self._fetch_candles(instrument, granularity="M5", count=200)
            closes: List[float] = []
            for candle in candles:
                try:
                    closes.append(float(candle["mid"]["c"]))
                except Exception:
                    continue
            if len(closes) < max(RSI_PERIOD, EMA_SLOW + 5):
                continue

            rsi = _compute_rsi(closes)
            momentum = _compute_momentum(closes)
            fast = _compute_ema(closes[-(EMA_FAST + EMA_SIGNAL * 5) :], EMA_FAST)
            slow = _compute_ema(closes[-(EMA_SLOW + EMA_SIGNAL * 5) :], EMA_SLOW)
            ema_sep = abs(fast - slow)

            if not (config["rsi_min"] <= rsi <= config["rsi_max"]):
                continue

            if ema_sep < config["min_ema_separation"]:
                continue

            direction = None
            if fast > slow and momentum >= config["min_momentum"]:
                direction = "BUY"
            elif fast < slow and momentum <= -config["min_momentum"]:
                direction = "SELL"

            if not direction:
                continue

            entry_price = price_data["ask"] if direction == "BUY" else price_data["bid"]
            stop_loss, take_profit = self._calculate_brackets(instrument, entry_price, direction)
            signals.append(
                {
                    "instrument": instrument,
                    "side": direction,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "confidence": 80,
                    "strategy": "pattern_discovery_v11",
                }
            )
        return signals

    def _calculate_brackets(self, instrument: str, entry_price: float, side: str) -> Tuple[float, float]:
        sl_distance = entry_price * SL_PCT
        tp_distance = entry_price * TP_PCT
        if instrument == "USD_JPY":
            sl_distance = max(0.08, entry_price * SL_PCT)
            tp_distance = max(0.12, entry_price * TP_PCT)
        elif instrument == "XAU_USD":
            sl_distance = max(4.5, entry_price * SL_PCT)
            tp_distance = max(7.0, entry_price * TP_PCT)
        if side == "BUY":
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        return stop_loss, take_profit

    # Ensure orders use correct rounding via inherited execution
    def _round_price(self, inst: str, px: float) -> str:  # pragma: no cover
        return _round_price(inst, px)


def main() -> None:
    system = PatternDiscoveryV11System()
    system.send_telegram_message(
        "🤖 Pattern Discovery v11 trader activated for account 101-004-30719775-006"
    )
    cycle = 0
    while True:
        try:
            cycle += 1
            logger.info("🔄 Pattern Discovery cycle %s", cycle)
            system.run_trading_cycle()
            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Pattern Discovery trader stopped by user")
            sys.exit(0)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Pattern Discovery trader error: %s", exc, exc_info=True)
            time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()








