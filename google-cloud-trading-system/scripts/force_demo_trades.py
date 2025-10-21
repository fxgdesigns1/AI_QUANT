#!/usr/bin/env python3
"""
Force Demo Trades (Winning) Across All Strategies
This script uses a mock OANDA client to simulate immediate winning trades
for Ultra-Strict Forex, Gold Scalping, and Momentum strategies.
It does not touch real accounts; it runs entirely in-memory.
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from typing import Dict, List, Optional

# Import core types
from src.core.order_manager import TradeSignal, OrderSide

# Strategies
from src.strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
from src.strategies.gold_scalping import get_gold_scalping_strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy

# Monkey patch target
import src.core.oanda_client as oc
import src.core.account_manager as am
from src.core.order_manager import OrderManager


# ----------------------
# Mock OANDA Client
# ----------------------
@dataclass
class MockAccount:
    account_id: str
    currency: str = 'USD'
    balance: float = 100000.0
    unrealized_pl: float = 0.0
    realized_pl: float = 0.0
    margin_used: float = 0.0
    margin_available: float = 100000.0
    open_trade_count: int = 0
    open_position_count: int = 0
    pending_order_count: int = 0


@dataclass
class MockPrice:
    instrument: str
    bid: float
    ask: float
    timestamp: datetime
    spread: float
    is_live: bool = True


@dataclass
class MockOrder:
    order_id: str
    instrument: str
    units: int
    side: str
    type: str
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    time_in_force: str
    status: str
    create_time: datetime
    fill_time: Optional[datetime] = None
    trade_id: Optional[str] = None


class MockOandaClient:
    def __init__(self, account_id: str):
        self.account_id = account_id
        self.account = MockAccount(account_id=account_id)
        self.orders: Dict[str, MockOrder] = {}
        self._id = 0

    def _next_id(self) -> str:
        self._id += 1
        return f"MOCK-{self._id:06d}"

    def get_account_info(self):
        return self.account

    def is_connected(self) -> bool:
        return True

    def get_current_prices(self, instruments: List[str]) -> Dict[str, MockPrice]:
        now = datetime.utcnow()
        prices: Dict[str, MockPrice] = {}
        # Static but plausible quotes
        static = {
            'EUR_USD': (1.17200, 1.17205),
            'GBP_USD': (1.35580, 1.35595),
            'USD_JPY': (147.570, 147.585),
            'AUD_USD': (0.66545, 0.66556),
            'USD_CAD': (1.38340, 1.38358),
            'NZD_USD': (0.59538, 0.59552),
            'XAU_USD': (3639.10, 3639.80),
        }
        for inst in instruments:
            bid, ask = static.get(inst, (1.0000, 1.0002))
            prices[inst] = MockPrice(
                instrument=inst,
                bid=bid,
                ask=ask,
                timestamp=now,
                spread=ask - bid,
                is_live=True,
            )
        return prices

    def place_market_order(self, instrument: str, units: int, stop_loss: Optional[float] = None,
                           take_profit: Optional[float] = None) -> MockOrder:
        oid = self._next_id()
        side = 'buy' if units > 0 else 'sell'
        order = MockOrder(
            order_id=oid,
            instrument=instrument,
            units=units,
            side=side,
            type='MARKET',
            price=None,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force='FOK',
            status='FILLED',
            create_time=datetime.utcnow(),
            fill_time=datetime.utcnow(),
            trade_id=oid.replace('MOCK', 'TRADE'),
        )
        self.orders[oid] = order
        # Simulate instant small profit realization
        self.account.realized_pl += 50.0
        return order

    def get_positions(self) -> Dict[str, object]:
        return {}

    def close_position(self, instrument: str, long_units: Optional[int] = None,
                       short_units: Optional[int] = None) -> Dict:
        return {'closed': instrument}


def main():
    # Build three mock clients for three demo accounts
    primary_id = os.getenv('PRIMARY_ACCOUNT', 'DEMO-PRIMARY')
    gold_id = os.getenv('GOLD_SCALP_ACCOUNT', 'DEMO-GOLD')
    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT', 'DEMO-ALPHA')

    mock_clients = {
        primary_id: MockOandaClient(primary_id),
        gold_id: MockOandaClient(gold_id),
        alpha_id: MockOandaClient(alpha_id),
    }

    # Monkey-patch global client getter to return the primary mock by default
    def _mock_get_oanda_client():
        return mock_clients[primary_id]

    oc.oanda_client = _mock_get_oanda_client()
    oc.get_oanda_client = _mock_get_oanda_client

    # Monkey-patch AccountManager to use our mock clients
    mgr = am.get_account_manager()
    mgr.accounts = mock_clients

    # Create OrderManager for each account
    om_primary = OrderManager(account_id=primary_id)
    om_gold = OrderManager(account_id=gold_id)
    om_alpha = OrderManager(account_id=alpha_id)

    # Create one winning trade per strategy
    trades: List[TradeSignal] = []

    # Ultra Strict Forex: BUY EUR_USD
    trades.append(TradeSignal(
        instrument='EUR_USD',
        side=OrderSide.BUY,
        units=10000,
        stop_loss=1.17000,
        take_profit=1.17350,
        strategy_name='Ultra Strict Forex',
        confidence=0.95,
    ))

    # Gold Scalping: BUY XAU_USD
    trades.append(TradeSignal(
        instrument='XAU_USD',
        side=OrderSide.BUY,
        units=10,
        stop_loss=3635.00,
        take_profit=3642.00,
        strategy_name='Gold Scalping',
        confidence=0.90,
    ))

    # Momentum Trading: SELL USD_JPY
    trades.append(TradeSignal(
        instrument='USD_JPY',
        side=OrderSide.SELL,
        units=10000,
        stop_loss=147.900,
        take_profit=147.300,
        strategy_name='Momentum Trading',
        confidence=0.92,
    ))

    # Execute with respective order managers
    print("\n🚀 Executing forced demo trades (mock, instantly winning)...\n")
    for signal in trades:
        if signal.instrument in ('EUR_USD', 'GBP_USD', 'AUD_USD', 'USD_JPY'):
            exec_result = om_primary.execute_trade(signal)
        elif signal.instrument == 'XAU_USD':
            exec_result = om_gold.execute_trade(signal)
        else:
            exec_result = om_alpha.execute_trade(signal)

        status = "WIN" if exec_result.success else f"FAIL: {exec_result.error_message}"
        print(f"{signal.strategy_name}: {signal.instrument} {signal.side.value} -> {status}")

    # Show resulting P&L from mock accounts
    print("\n📊 Mock account P&L (realized):")
    for acc_id, client in mock_clients.items():
        print(f"  {acc_id}: ${client.account.realized_pl:.2f}")


if __name__ == '__main__':
    main()


