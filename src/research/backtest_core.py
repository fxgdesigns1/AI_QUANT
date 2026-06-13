"""
Backtest Core - Deterministic Cached Candle Backtesting
Supports both live OANDA and cached candle modes.
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


def _rolling_sma(values: List[float], period: int) -> List[Optional[float]]:
    """Simple SMA aligned to index i using closes 0..i inclusive."""
    out: List[Optional[float]] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    window = sum(values[:period])
    out[period - 1] = window / period
    for i in range(period, len(values)):
        window += values[i] - values[i - period]
        out[i] = window / period
    return out


def _atr_sma(candles: List[Candle], period: int = 14) -> List[Optional[float]]:
    """ATR as rolling mean of true range (research-grade, not Wilder-smoothed)."""
    if len(candles) < 2:
        return [None] * len(candles)
    tr: List[float] = []
    for i in range(1, len(candles)):
        h, l, prev_c = candles[i].h, candles[i].l, candles[i - 1].c
        tr.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    atr = [None] * len(candles)
    if len(tr) < period:
        return atr
    window = sum(tr[:period])
    atr[period] = window / period
    for i in range(period + 1, len(candles)):
        ti = i - 1
        window += tr[ti] - tr[ti - period]
        atr[i] = window / period
    return atr


def run_sma_crossover_research_backtest(
    candles: List[Candle],
    instrument: str,
    fast_period: int = 5,
    slow_period: int = 20,
    strategy_name: str = "sma_crossover_research",
    initial_balance: float = 10000.0,
    risk_per_trade: float = 0.01,
    stop_atr_mult: float = 1.5,
    rr: float = 2.0,
) -> BacktestResult:
    """
    Deterministic bar-based SMA crossover simulator for cached candle research.
    Entries on confirmed cross using SMAs through prior bar (no same-bar lookahead).
    Exits on stop, target, or flat at opposing signal close.
    """
    run_id = f"backtest_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    start_time = datetime.now(timezone.utc).isoformat()
    if slow_period <= fast_period:
        raise ValueError("slow_period must be greater than fast_period")
    if len(candles) < slow_period + 3:
        raise ValueError(f"Need more candles for SMA periods (have {len(candles)})")

    closes = [c.c for c in candles]
    sma_f = _rolling_sma(closes, fast_period)
    sma_s = _rolling_sma(closes, slow_period)
    atr = _atr_sma(candles, period=14)

    trades: List[Trade] = []
    balance = initial_balance
    max_equity = initial_balance
    max_drawdown = 0.0

    position: Optional[Dict[str, Any]] = None

    def equity_at_close(c_idx: int) -> float:
        nonlocal balance, position
        eq = balance
        if position:
            cc = candles[c_idx].c
            if position["side"] == "BUY":
                eq += (cc - position["entry_price"]) * position["quantity"]
            else:
                eq += (position["entry_price"] - cc) * position["quantity"]
        return eq

    def close_position(exit_time: str, exit_price: float, reason: str) -> None:
        nonlocal balance, position
        if not position:
            return
        side = position["side"]
        entry = position["entry_price"]
        qty = position["quantity"]
        sl_dist = position["stop_distance"]
        if side == "BUY":
            pnl = (exit_price - entry) * qty
        else:
            pnl = (entry - exit_price) * qty
        risk_cash = position["risk_cash"]
        pnl_r = pnl / risk_cash if risk_cash and risk_cash > 0 else None
        trades.append(
            Trade(
                entry_time=position["entry_time"],
                exit_time=exit_time,
                instrument=instrument,
                side=side,
                entry_price=entry,
                exit_price=exit_price,
                quantity=qty,
                pnl=pnl,
                pnl_r=pnl_r,
                stop_loss=position["sl"],
                take_profit=position["tp"],
            )
        )
        balance += pnl
        position = None

    i = slow_period + 1
    while i < len(candles):
        eq = equity_at_close(i)
        if eq > max_equity:
            max_equity = eq
        dd = (max_equity - eq) / max_equity if max_equity > 0 else 0.0
        max_drawdown = max(max_drawdown, dd)

        if position:
            c = candles[i]
            side = position["side"]
            sl, tp = position["sl"], position["tp"]
            hit_sl = hit_tp = False
            exit_px = c.c
            if side == "BUY":
                if c.l <= sl:
                    hit_sl = True
                    exit_px = sl
                elif c.h >= tp:
                    hit_tp = True
                    exit_px = tp
            else:
                if c.h >= sl:
                    hit_sl = True
                    exit_px = sl
                elif c.l <= tp:
                    hit_tp = True
                    exit_px = tp
            if hit_sl or hit_tp:
                close_position(c.time, exit_px, "sl_tp")
                i += 1
                continue

        pf, ps = sma_f[i - 1], sma_s[i - 1]
        pf0, ps0 = sma_f[i - 2], sma_s[i - 2]
        if pf is None or ps is None or pf0 is None or ps0 is None:
            i += 1
            continue

        bull = pf > ps and pf0 <= ps0
        bear = pf < ps and pf0 >= ps0

        if position:
            side = position["side"]
            if (side == "BUY" and bear) or (side == "SELL" and bull):
                close_position(candles[i].time, candles[i].c, "signal_reverse")
            i += 1
            continue

        if not bull and not bear:
            i += 1
            continue

        entry_price = candles[i].c
        atr_i = atr[i - 1] or atr[i]
        if atr_i and atr_i > 0:
            stop_distance = max(entry_price * 1e-5, float(atr_i) * stop_atr_mult)
        else:
            stop_distance = max(entry_price * 1e-5, entry_price * 0.0005)

        risk_cash = balance * risk_per_trade
        quantity = risk_cash / stop_distance if stop_distance > 0 else 0.0

        if bull:
            sl = entry_price - stop_distance
            tp = entry_price + stop_distance * rr
            position = {
                "side": "BUY",
                "entry_time": candles[i].time,
                "entry_price": entry_price,
                "quantity": quantity,
                "stop_distance": stop_distance,
                "risk_cash": risk_cash,
                "sl": sl,
                "tp": tp,
            }
        elif bear:
            sl = entry_price + stop_distance
            tp = entry_price - stop_distance * rr
            position = {
                "side": "SELL",
                "entry_time": candles[i].time,
                "entry_price": entry_price,
                "quantity": quantity,
                "stop_distance": stop_distance,
                "risk_cash": risk_cash,
                "sl": sl,
                "tp": tp,
            }

        i += 1

    if position:
        close_position(candles[-1].time, candles[-1].c, "eod")

    winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
    losing_trades = sum(1 for t in trades if t.pnl is not None and t.pnl <= 0)
    total_trades = len(trades)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    total_pnl = sum(t.pnl or 0.0 for t in trades)
    r_values = [t.pnl_r for t in trades if t.pnl_r is not None]
    expectancy_r = sum(r_values) / len(r_values) if r_values else 0.0
    end_time = datetime.now(timezone.utc).isoformat()

    return BacktestResult(
        run_id=run_id,
        start_time=start_time,
        end_time=end_time,
        instrument=instrument,
        strategy_name=strategy_name,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        total_pnl=total_pnl,
        expectancy_r=expectancy_r,
        max_drawdown=max_drawdown,
        sharpe_ratio=None,
        trades=[asdict(t) for t in trades],
    )


@dataclass
class Candle:
    """Standardized candle representation"""
    time: str
    complete: bool
    volume: int
    o: float
    h: float
    l: float
    c: float


@dataclass
class Trade:
    """Trade execution record"""
    entry_time: str
    exit_time: Optional[str]
    instrument: str
    side: str  # "BUY" or "SELL"
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_r: Optional[float]  # P&L in R units
    stop_loss: Optional[float]
    take_profit: Optional[float]


@dataclass
class BacktestResult:
    """Backtest execution result"""
    run_id: str
    start_time: str
    end_time: str
    instrument: str
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    expectancy_r: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    trades: List[Dict[str, Any]]


class CachedCandleProvider:
    """Loads candles from cached files (no OANDA dependency)"""
    
    def __init__(self, cache_root: Path):
        self.cache_root = Path(cache_root)
        if not self.cache_root.exists():
            raise ValueError(f"Cache root does not exist: {cache_root}")
    
    def load_candles(self, instrument: str, granularity: str = "M5") -> List[Candle]:
        """Load candles from cache file"""
        cache_file = self.cache_root / f"{instrument}_{granularity}.json"
        
        if not cache_file.exists():
            raise FileNotFoundError(f"Cached candles not found: {cache_file}")
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        candles = []
        for c in data.get("candles", []):
            candles.append(Candle(
                time=str(c.get("time", "")),
                complete=bool(c.get("complete", True)),
                volume=int(c.get("volume", 0)),
                o=float(c.get("o", 0.0)),
                h=float(c.get("h", 0.0)),
                l=float(c.get("l", 0.0)),
                c=float(c.get("c", 0.0))
            ))
        
        logger.info(f"Loaded {len(candles)} candles from {cache_file}")
        return candles


class BacktestEngine:
    """Core backtesting engine"""
    
    def __init__(self, use_cached: bool = False, cache_root: Optional[Path] = None):
        self.use_cached = use_cached
        self.cache_provider = CachedCandleProvider(cache_root) if use_cached and cache_root else None
        
        # Verify cached mode doesn't require OANDA
        if use_cached:
            oanda_key = os.getenv("OANDA_API_KEY")
            if oanda_key:
                logger.warning("OANDA_API_KEY set but using cached mode - will ignore live API")
    
    def get_candles(self, instrument: str, granularity: str = "M5", count: int = 500) -> List[Candle]:
        """Get candles from cache or live API"""
        if self.use_cached and self.cache_provider:
            return self.cache_provider.load_candles(instrument, granularity)
        
        # Live mode - requires OANDA (but we're in cached mode, so this shouldn't be called)
        if not self.use_cached:
            # Import here to avoid dependency when using cached mode
            try:
                from src.control_plane.market_data_provider import get_candles as live_get_candles
                live_candles = live_get_candles(instrument, granularity, count)
                # Convert to our Candle format
                return [
                    Candle(
                        time=str(c.time),
                        complete=c.complete,
                        volume=c.volume,
                        o=c.o,
                        h=c.h,
                        l=c.l,
                        c=c.c
                    ) for c in live_candles
                ]
            except ImportError:
                raise RuntimeError("Live candle fetching requires OANDA env vars, but cached mode is disabled")
        
        raise RuntimeError("Cannot get candles: cached mode enabled but no cache provider")
    
    def run_backtest(
        self,
        strategy,
        instrument: str,
        candles: List[Candle],
        initial_balance: float = 10000.0,
        risk_per_trade: float = 0.01
    ) -> BacktestResult:
        """Run backtest on provided candles"""
        run_id = f"backtest_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        start_time = datetime.now(timezone.utc).isoformat()
        
        trades = []
        balance = initial_balance
        position = None
        max_equity = initial_balance
        max_drawdown = 0.0
        
        # Simulate strategy execution on each candle
        for i, candle in enumerate(candles):
            # Get signals from strategy (mock for now - will be extended)
            # In real implementation, this would call strategy.analyze_market() with historical context
            
            # Track equity curve
            current_equity = balance
            if position:
                # Calculate unrealized P&L
                if position["side"] == "BUY":
                    unrealized_pnl = (candle.c - position["entry_price"]) * position["quantity"]
                else:
                    unrealized_pnl = (position["entry_price"] - candle.c) * position["quantity"]
                current_equity = balance + unrealized_pnl
            
            if current_equity > max_equity:
                max_equity = current_equity
            
            drawdown = (max_equity - current_equity) / max_equity if max_equity > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate metrics
        winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl and t.pnl <= 0)
        total_trades = len(trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        total_pnl = sum(t.pnl or 0.0 for t in trades)
        
        # Calculate expectancy in R units
        r_values = [t.pnl_r for t in trades if t.pnl_r is not None]
        expectancy_r = sum(r_values) / len(r_values) if r_values else 0.0
        
        end_time = datetime.now(timezone.utc).isoformat()
        
        return BacktestResult(
            run_id=run_id,
            start_time=start_time,
            end_time=end_time,
            instrument=instrument,
            strategy_name=getattr(strategy, "__name__", "unknown"),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            expectancy_r=expectancy_r,
            max_drawdown=max_drawdown,
            sharpe_ratio=None,  # TODO: Calculate Sharpe ratio
            trades=[asdict(t) for t in trades]
        )
