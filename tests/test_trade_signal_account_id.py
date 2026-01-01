from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime

def test_trade_signal_has_account_id_optional():
    t = TradeSignal(
        instrument='EUR_USD',
        side=OrderSide.BUY,
        units=100000,
        entry_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        confidence=0.5,
        timestamp=datetime.now(),
        strategy_name='test'
    )
    assert hasattr(t, 'account_id')
    assert t.account_id is None

def test_trade_signal_with_account_id():
    t = TradeSignal(
        instrument='EUR_USD',
        side=OrderSide.BUY,
        units=100000,
        entry_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        confidence=0.5,
        timestamp=datetime.now(),
        strategy_name='test',
        account_id='ACCT-1'
    )
    assert t.account_id == 'ACCT-1'


