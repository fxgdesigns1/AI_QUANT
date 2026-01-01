#!/usr/bin/env python3
"""
Trade With Pat - Dual Session Open Range Breakout Strategy

Hybrid configuration: Defaults to Firestore 'ai-trading-config' (Native Mode),
falls back to local YAML if cloud is unreachable.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yaml
from zoneinfo import ZoneInfo

# Cloud Client
try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False

logger = logging.getLogger(__name__)

try:
    from src.core.order_manager import TradeSignal, OrderSide
except Exception:
    class OrderSide:
        BUY = "BUY"
        SELL = "SELL"

    @dataclass
    class TradeSignal:
        instrument: str
        side: str
        confidence: float
        entry_price: float
        stop_loss: float
        take_profit: float
        timestamp: datetime
        strategy: str
        metadata: Dict[str, float]


CONFIG_ENV_VAR = "TRADE_WITH_PAT_ORB_CONFIG_PATH"
CONFIG_FILENAME = "trade_with_pat_orb_dual_session.yaml"
FIRESTORE_PROJECT = "ai-quant-trading"
FIRESTORE_DB = "ai-trading-config"
FIRESTORE_COLLECTION = "strategies"
FIRESTORE_DOC = "trade_with_pat_orb_dual"


def _default_config_candidates() -> List[str]:
    """Return candidate paths for the YAML configuration."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return [
        os.getenv(CONFIG_ENV_VAR, ""),
        os.path.join(root, "AI_QUANT_credentials", "strategy_configs", CONFIG_FILENAME),
        os.path.join(root, "strategy_configs", CONFIG_FILENAME),
        os.path.join(root, CONFIG_FILENAME),
        os.path.join(root, "..", "Strategies here", CONFIG_FILENAME),
    ]


def _load_firestore_config() -> Optional[Dict]:
    """Attempt to load configuration from Firestore."""
    if not FIRESTORE_AVAILABLE:
        logger.warning("⚠️ Google Cloud Firestore library not installed. Skipping cloud config.")
        return None
    
    try:
        db = firestore.Client(project=FIRESTORE_PROJECT, database=FIRESTORE_DB)
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(FIRESTORE_DOC)
        doc = doc_ref.get()
        if doc.exists:
            logger.info(f"✅ Loaded config from Firestore: {FIRESTORE_DB}/{FIRESTORE_COLLECTION}/{FIRESTORE_DOC}")
            return doc.to_dict()
        else:
            logger.warning(f"⚠️ Config document {FIRESTORE_DOC} not found in Firestore.")
    except Exception as e:
        logger.error(f"❌ Failed to load from Firestore: {e}")
    return None


def _load_config() -> Dict:
    """Load configuration: Cloud First -> Local Fallback."""
    # 1. Try Cloud
    cloud_config = _load_firestore_config()
    if cloud_config:
        return cloud_config

    # 2. Try Local YAML
    for candidate in _default_config_candidates():
        if not candidate:
            continue
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as handle:
                    payload = yaml.safe_load(handle) or {}
                logger.info("✅ Loaded local config fallback from %s", candidate)
                return payload
            except Exception as e:
                logger.error(f"Error reading local config {candidate}: {e}")

    raise FileNotFoundError(
        "Trade With Pat ORB configuration not found in Cloud OR Local paths."
    )


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _pip_value(instrument: str) -> float:
    """Return pip/point granularity per instrument."""
    if instrument.endswith("JPY"):
        return 0.01
    if instrument.startswith("XAU"):
        return 0.1
    if instrument in {"US500_USD", "NAS100_USD"}:
        return 1.0
    return 0.0001


class TradeWithPatOrbDualStrategy:
    """Session-based open range breakout strategy."""

    def __init__(self, config: Optional[Dict] = None):
        payload = config or _load_config()
        self.strategy_key = "trade_with_pat_orb_dual"
        
        # Handle cases where root key might be missing in flattened Cloud config
        if self.strategy_key in payload.get("strategies", {}):
            self.strategy_block = payload["strategies"][self.strategy_key]
        else:
            # If loaded flat from Firestore (document root IS the strategy config)
            # We check if we are inside the strategies block or if the doc itself is the block
            self.strategy_block = payload.get("strategies", {}).get(self.strategy_key, payload)

        self.parameters = self.strategy_block.get("parameters", {})
        self.session_templates = self.parameters.get("session_templates", {})
        self.risk_overrides = self.parameters.get("risk_overrides", {})
        
        global_conf = payload.get("global", {})
        timezone_name = global_conf.get("timezone", "Europe/London")
        self.tz = ZoneInfo(timezone_name)

        self.range_window = int(self.parameters.get("range_window_minutes", 15))
        self.kill_switch_drawdown = payload.get("risk_management", {}).get("kill_switch_drawdown_pct", 0.07)
        self.daily_trade_cap = int(self.risk_overrides.get("max_trades_per_day", 12))
        self.session_trade_cap = {
            name: template.get("per_session_trade_cap", 2)
            for name, template in self.session_templates.items()
        }
        
        # Instrument logic
        inst_block = self.strategy_block.get("instruments", {})
        if isinstance(inst_block, dict):
            self.instruments = sorted(set(
                inst_block.get("london_lane", []) + inst_block.get("ny_lane", [])
            ))
        else:
            self.instruments = sorted(list(inst_block))

        self._reset_counters(datetime.now(self.tz))
        logger.info("✅ Trade With Pat ORB strategy ready | instruments=%s", ", ".join(self.instruments))

    def _reset_counters(self, now: datetime) -> None:
        self.daily_anchor = now.date()
        self.daily_trades = 0
        self.session_trades: Dict[str, int] = {name: 0 for name in self.session_templates}

    def _maybe_reset(self, now: datetime) -> None:
        if now.date() != self.daily_anchor:
            self._reset_counters(now)

    # --------------------------------------------------------------------- data
    def _extract_dataframe(self, market_data, instrument: str) -> Optional[pd.DataFrame]:
        if market_data is None:
            return None
        data_obj = None
        if isinstance(market_data, dict):
            data_obj = market_data.get(instrument)
        elif hasattr(market_data, "get"):
            data_obj = market_data.get(instrument)
        if data_obj is None and hasattr(market_data, instrument):
            data_obj = getattr(market_data, instrument)
        if data_obj is None:
            return None

        if isinstance(data_obj, pd.DataFrame):
            df = data_obj.copy()
        elif hasattr(data_obj, "to_dataframe"):
            df = data_obj.to_dataframe()
        elif hasattr(data_obj, "candles"):
            df = pd.DataFrame(data_obj.candles)
        else:
            df = pd.DataFrame(data_obj)

        if df.empty:
            return None

        columns_map = {
            "time": "timestamp",
            "DateTime": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
        }
        for src, dst in columns_map.items():
            if src in df.columns and dst not in df.columns:
                df[dst] = df[src]

        if "timestamp" not in df.columns:
            return None

        ts = pd.to_datetime(df["timestamp"])
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize("UTC")
        df["timestamp"] = ts.dt.tz_convert(self.tz)
        for column in ("open", "high", "low", "close"):
            if column not in df.columns:
                return None
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        return df

    # ------------------------------------------------------------------ helpers
    def _session_window(self, template: Dict, now: datetime) -> Tuple[datetime, datetime]:
        window = template.get("window", "08:00-08:15")
        start_str, end_str = window.split("-")
        start_dt = datetime.combine(now.date(), _parse_time(start_str), tzinfo=self.tz)
        end_dt = datetime.combine(now.date(), _parse_time(end_str), tzinfo=self.tz)
        return start_dt, end_dt

    def _is_evaluation_window(self, now: datetime, template: Dict) -> bool:
        start_dt, end_dt = self._session_window(template, now)
        return start_dt <= now <= end_dt + timedelta(hours=2)

    def _calculate_range(self, df: pd.DataFrame, template: Dict, now: datetime) -> Optional[Tuple[float, float, float]]:
        start_dt, end_dt = self._session_window(template, now)
        window_df = df[(df["timestamp"] >= start_dt) & (df["timestamp"] <= end_dt)]
        if window_df.empty:
            return None

        range_high = float(window_df["high"].max())
        range_low = float(window_df["low"].min())
        pip = _pip_value(df.name if hasattr(df, "name") else template.get("label", ""))
        min_range = template.get("min_range_pips", 5) * pip
        max_range = template.get("max_range_pips", 35) * pip
        width = range_high - range_low
        if width < min_range or width > max_range:
            return None

        atr_period = int(self.parameters.get("atr_filter", {}).get("period", 14))
        atr = self._compute_atr(df, atr_period)
        return range_high, range_low, atr

    def _compute_atr(self, df: pd.DataFrame, period: int) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(window=period, min_periods=3).mean().iloc[-1]
        return float(atr) if pd.notna(atr) else float(tr.iloc[-1])

    def _passes_filters(self, df: pd.DataFrame, template: Dict, side: str) -> bool:
        ema_filter = self.parameters.get("ema_filter", {})
        if ema_filter.get("enabled"):
            period = int(ema_filter.get("period", 200))
            ema = df["close"].ewm(span=period, adjust=False).mean().iloc[-1]
            price = df["close"].iloc[-1]
            if side == OrderSide.BUY and price < ema:
                return False
            if side == OrderSide.SELL and price > ema:
                return False

        momentum = self.parameters.get("momentum_filter", {})
        if momentum.get("enabled"):
            ema_stack = momentum.get("ema_stack", [3, 8, 21])
            rms = []
            for length in ema_stack:
                rms.append(df["close"].ewm(span=length, adjust=False).mean().iloc[-1])
            if side == OrderSide.BUY and not (rms[0] > rms[1] > rms[2]):
                return False
            if side == OrderSide.SELL and not (rms[0] < rms[1] < rms[2]):
                return False
        return True

    # ------------------------------------------------------------------ trading
    def generate_signals(self, market_data) -> List[TradeSignal]:
        now = datetime.now(self.tz)
        self._maybe_reset(now)
        if self.daily_trades >= self.daily_trade_cap:
            return []

        signals: List[TradeSignal] = []
        for session_key, template in self.session_templates.items():
            if self.session_trades.get(session_key, 0) >= self.session_trade_cap.get(session_key, 1):
                continue
            if not self._is_evaluation_window(now, template):
                continue

            for instrument in self._session_instruments(session_key):
                df = self._extract_dataframe(market_data, instrument)
                if df is None or len(df) < self.range_window + 5:
                    continue

                df.name = instrument
                range_stats = self._calculate_range(df, template, now)
                if not range_stats:
                    continue

                signal = self._build_signal(instrument, df, template, range_stats, session_key)
                if not signal:
                    continue

                signals.append(signal)  # Fixed indentation logic
                self.session_trades[session_key] += 1
                self.daily_trades += 1
                if self.daily_trades >= self.daily_trade_cap:
                    return signals
                if self.session_trades[session_key] >= self.session_trade_cap.get(session_key, 1):
                    break
        return signals

    def _session_instruments(self, session_key: str) -> List[str]:
        lanes = self.strategy_block.get("instruments", {})
        if session_key == "london_open":
            return lanes.get("london_lane", [])
        if session_key == "ny_open":
            return lanes.get("ny_lane", [])
        return self.instruments

    def _build_signal(
        self,
        instrument: str,
        df: pd.DataFrame,
        template: Dict,
        range_stats: Tuple[float, float, float],
        session_key: str,
    ) -> Optional[TradeSignal]:
        range_high, range_low, atr = range_stats
        last_price = float(df["close"].iloc[-1])
        pip = _pip_value(instrument)
        buffer_pips = self.parameters.get("supply_demand_detection", {}).get("mitigation_buffer_pips", 2.0)
        buffer = buffer_pips * pip

        side = None
        if last_price > range_high + buffer:
            side = OrderSide.BUY
        elif last_price < range_low - buffer:
            side = OrderSide.SELL
        if not side:
            return None
        if not self._passes_filters(df, template, side):
            return None

        range_width = range_high - range_low
        target_logic = self.parameters.get("target_logic", {})
        tp_multiple = target_logic.get("tp_multiple_of_range", 0.8)
        fallback_atr = target_logic.get("tp_fallback_atr_multiple", 1.2)
        projected_move = max(range_width * tp_multiple, atr * fallback_atr)

        if side == OrderSide.BUY:
            stop_loss = range_low - buffer
            take_profit = last_price + projected_move
        else:
            stop_loss = range_high + buffer
            take_profit = last_price - projected_move

        risk_per_trade = self.risk_overrides.get("max_risk_per_trade", 0.02)
        confidence = min(0.95, max(0.6, projected_move / (atr + 1e-6)))

        metadata = {
            "session": session_key,
            "range_high": range_high,
            "range_low": range_low,
            "atr": atr,
            "range_width": range_width,
            "risk_per_trade": risk_per_trade,
        }
        return TradeSignal(
            instrument=instrument,
            side=side,
            confidence=float(confidence),
            entry_price=last_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=datetime.utcnow(),
            strategy=self.strategy_key,
            metadata=metadata,
        )


def get_trade_with_pat_orb_dual_strategy() -> TradeWithPatOrbDualStrategy:
    """Factory for registry."""
    return TradeWithPatOrbDualStrategy()






















