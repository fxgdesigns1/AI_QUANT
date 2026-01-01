import unittest
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime


class TestAccountOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orc = get_account_orchestrator()
        # clear state
        try:
            self.orc._managers.clear()
            self.orc._executors.clear()
        except Exception:
            pass
        self.executed_1 = []
        self.executed_2 = []

        def exec1(signal):
            self.executed_1.append(signal)
            return {"status": "ok", "account": "acct-1", "instrument": signal.get("instrument")}

        def exec2(signal):
            self.executed_2.append(signal)
            return {"status": "ok", "account": "acct-2", "instrument": signal.get("instrument")}

        self.orc.register_account("acct-1", executor=exec1)
        self.orc.register_account("acct-2", executor=exec2)

    def test_object_routing(self):
        sig1 = TradeSignal(
            instrument="EUR_USD",
            side=OrderSide.BUY,
            units=100000,
            entry_price=1.1,
            stop_loss=1.099,
            take_profit=1.103,
            confidence=0.5,
            timestamp=datetime.now(),
            strategy_name="ts",
            account_id="acct-1",
        )
        res = self.orc.route_signal(sig1)
        self.assertEqual(res.get("account"), "acct-1")
        self.assertEqual(len(self.executed_1), 1)

    def test_dict_routing(self):
        d = {
            "instrument": "XAU_USD",
            "side": "SELL",
            "entry_price": 2000.0,
            "stop_loss": 2005.0,
            "take_profit": 1990.0,
            "confidence": 0.6,
            "strategy": "ts",
            "account_id": "acct-2",
        }
        res = route_signal_dict(d)
        self.assertEqual(res.get("account"), "acct-2")
        self.assertEqual(len(self.executed_2), 1)


if __name__ == "__main__":
    unittest.main()

import pytest
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime


def test_orchestrator_routing_object_and_dict():
    orc = get_account_orchestrator()
    # clear state
    orc._managers.clear()
    orc._executors.clear()

    called = {"a": [], "b": []}

    def exec_a(sig):
        called["a"].append(sig)
        return {"status": "ok", "account": "A"}

    def exec_b(sig):
        called["b"].append(sig)
        return {"status": "ok", "account": "B"}

    orc.register_account("A", executor=exec_a)
    orc.register_account("B", executor=exec_b)

    ts_a = TradeSignal(
        instrument="EUR_USD",
        side=OrderSide.BUY,
        units=100000,
        entry_price=1.1,
        stop_loss=1.099,
        take_profit=1.103,
        confidence=0.5,
        timestamp=datetime.utcnow(),
        strategy_name="t",
        account_id="A",
    )

    ts_b = TradeSignal(
        instrument="GBP_USD",
        side=OrderSide.SELL,
        units=100000,
        entry_price=1.27,
        stop_loss=1.271,
        take_profit=1.266,
        confidence=0.6,
        timestamp=datetime.utcnow(),
        strategy_name="t",
        account_id="B",
    )

    res1 = orc.route_signal(ts_a)
    res2 = orc.route_signal(ts_b)
    assert res1["account"] == "A"
    assert res2["account"] == "B"

    # dict routing
    d = {"instrument": "USD_JPY", "side": "BUY", "entry_price": 149.0, "stop_loss": 148.5, "take_profit": 149.5, "confidence": 0.5, "strategy": "t", "account_id": "A"}
    rd = route_signal_dict(d)
    assert rd["account"] == "A"

import pytest
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime


def test_orchestrator_routes_to_executors():
    orch = get_account_orchestrator()
    # clear state
    orch._managers.clear()
    orch._executors.clear()

    called = {}

    def exec_a(signal):
        called['a'] = signal
        return {'status': 'ok', 'account': 'A'}

    def exec_b(signal):
        called['b'] = signal
        return {'status': 'ok', 'account': 'B'}

    orch.register_account('A', executor=exec_a)
    orch.register_account('B', executor=exec_b)

    s1 = TradeSignal(
        instrument='EUR_USD',
        side=OrderSide.BUY,
        units=100000,
        entry_price=1.10,
        stop_loss=1.09,
        take_profit=1.12,
        confidence=0.5,
        timestamp=datetime.utcnow(),
        strategy_name='test',
        account_id='A'
    )

    s2 = TradeSignal(
        instrument='GBP_USD',
        side=OrderSide.SELL,
        units=100000,
        entry_price=1.27,
        stop_loss=1.28,
        take_profit=1.25,
        confidence=0.6,
        timestamp=datetime.utcnow(),
        strategy_name='test',
        account_id='B'
    )

    res1 = orch.route_signal(s1)
    res2 = orch.route_signal(s2)

    assert res1['account'] == 'A'
    assert res2['account'] == 'B'
    assert 'a' in called and 'b' in called

    # test dict routing helper
    d = {'instrument': 'XAU_USD', 'side': 'BUY', 'entry_price': 2000.0, 'stop_loss':1990.0, 'take_profit':2010.0, 'confidence':0.5, 'strategy': 'test', 'account_id': 'A'}
    rd = route_signal_dict(d)
    assert rd['account'] == 'A'

import unittest
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime


class TestAccountOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orc = get_account_orchestrator()
        # clear managers/executors
        try:
            self.orc._managers.clear()
            self.orc._executors.clear()
        except Exception:
            pass

    def test_object_routing_to_executor(self):
        executed = []

        def exec_cb(signal):
            executed.append(signal)
            return {"status": "ok"}

        self.orc.register_account("acct-test", executor=exec_cb)

        ts = TradeSignal(
            instrument="EUR_USD",
            side=OrderSide.BUY,
            units=100000,
            entry_price=1.1,
            stop_loss=1.099,
            take_profit=1.103,
            confidence=0.5,
            timestamp=datetime.now(),
            strategy_name="test",
            account_id="acct-test",
        )

        res = self.orc.route_signal(ts)
        self.assertTrue(executed)
        self.assertEqual(res.get("status"), "ok")

    def test_dict_routing_to_executor(self):
        executed = []

        def exec_cb(signal):
            executed.append(signal)
            return {"status": "ok"}

        self.orc.register_account("acct-dict", executor=exec_cb)

        sig = {
            "instrument": "XAU_USD",
            "side": "SELL",
            "entry_price": 2000.0,
            "stop_loss": 2005.0,
            "take_profit": 1990.0,
            "confidence": 0.6,
            "strategy": "test",
            "account_id": "acct-dict",
        }

        res = route_signal_dict(sig)
        self.assertTrue(executed)
        self.assertEqual(res.get("status"), "ok")


if __name__ == "__main__":
    unittest.main()

from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime

def test_orchestrator_routes_by_account():
    orc = get_account_orchestrator()
    orc._managers.clear()
    orc._executors.clear()

    executed = {}
    def exec_a(sig):
        executed['a'] = sig
        return {'status': 'ok', 'account': 'A'}
    def exec_b(sig):
        executed['b'] = sig
        return {'status': 'ok', 'account': 'B'}

    orc.register_account('A', executor=exec_a)
    orc.register_account('B', executor=exec_b)

    sig = TradeSignal(
        instrument='EUR_USD',
        side=OrderSide.BUY,
        units=100000,
        entry_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        confidence=0.5,
        timestamp=datetime.now(),
        strategy_name='test',
        account_id='A'
    )
    res = orc.route_signal(sig)
    assert res['account'] == 'A'

    d = {'instrument':'XAU_USD','side':'SELL','entry_price':2000.0,'stop_loss':2010.0,'take_profit':1990.0,'confidence':0.6,'strategy':'t','account_id':'B'}
    res2 = route_signal_dict(d)
    assert res2['account'] == 'B'

import pytest
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime


def test_object_routing_to_executor():
    orc = get_account_orchestrator()
    orc._managers.clear()
    orc._executors.clear()

    executed = []

    def exec_cb(sig):
        executed.append(sig)
        return {"status": "ok", "acct": sig.get("account_id") if isinstance(sig, dict) else getattr(sig, "account_id", None)}

    orc.register_account("t1", executor=exec_cb)

    sig = TradeSignal(
        instrument="EUR_USD",
        side=OrderSide.BUY,
        units=100000,
        entry_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        confidence=0.6,
        timestamp=datetime.utcnow(),
        strategy_name="test",
        account_id="t1",
    )

    res = orc.route_signal(sig)
    assert res["status"] == "ok"
    assert len(executed) == 1


def test_dict_routing_via_route_signal_dict():
    orc = get_account_orchestrator()
    orc._managers.clear()
    orc._executors.clear()

    executed = []

    def exec_cb(sig):
        executed.append(sig)
        return {"status": "ok", "acct": sig.get("account_id")}

    orc.register_account("t2", executor=exec_cb)

    d = {"instrument": "USD_JPY", "side": "BUY", "entry_price": 150.0, "stop_loss": 149.5, "take_profit": 150.5, "confidence": 0.5, "strategy": "test", "account_id": "t2"}
    res = route_signal_dict(d)
    assert res["status"] == "ok"
    assert len(executed) == 1

import unittest
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime


class TestAccountOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orc = get_account_orchestrator()
        # clear registrations
        self.orc._managers.clear()
        self.orc._executors.clear()

    def test_object_routing_to_executor(self):
        called = {}

        def exec_fn(sig):
            called['ok'] = True
            called['sig'] = sig
            return {'status': 'ok'}

        self.orc.register_account('t1', executor=exec_fn)
        sig = TradeSignal(
            instrument='EUR_USD',
            side=OrderSide.BUY,
            units=1000,
            entry_price=1.1,
            stop_loss=1.099,
            take_profit=1.103,
            confidence=0.5,
            timestamp=datetime.utcnow(),
            strategy_name='test',
            account_id='t1'
        )
        res = self.orc.route_signal(sig)
        self.assertEqual(res.get('status'), 'ok')
        self.assertTrue(called.get('ok', False))

    def test_dict_routing(self):
        called = {}

        def exec_fn(sig):
            called['ok'] = True
            called['sig'] = sig
            return {'status': 'ok', 'instrument': sig.get('instrument')}

        self.orc.register_account('t2', executor=exec_fn)
        d = {'instrument': 'USD_JPY', 'side': 'BUY', 'entry_price': 149.0, 'stop_loss': 148.5, 'take_profit': 149.5, 'confidence': 0.6, 'strategy': 'test', 'account_id': 't2'}
        res = route_signal_dict(d)
        self.assertEqual(res.get('status'), 'ok')
        self.assertTrue(called.get('ok', False))


if __name__ == '__main__':
    unittest.main()

import unittest
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict
from src.core.order_manager import TradeSignal, OrderSide
from datetime import datetime


class TestAccountOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orc = get_account_orchestrator()
        # Clear state
        try:
            self.orc._managers.clear()
            self.orc._executors.clear()
        except Exception:
            pass

    def test_executor_routing(self):
        executed = []

        def exec_fn(sig):
            executed.append(sig)
            return {"status": "ok", "account": "A"}

        self.orc.register_account("A", executor=exec_fn)
        sig = TradeSignal(
            instrument="EUR_USD",
            side=OrderSide.BUY,
            units=100000,
            entry_price=1.2,
            stop_loss=1.199,
            take_profit=1.203,
            confidence=0.5,
            timestamp=datetime.now(),
            strategy_name="test",
            account_id="A",
        )
        res = self.orc.route_signal(sig)
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(len(executed), 1)

    def test_dict_routing(self):
        executed = []

        def exec_fn(sig):
            executed.append(sig)
            return {"status": "ok", "account": "B"}

        self.orc.register_account("B", executor=exec_fn)
        d = {
            "instrument": "GBP_USD",
            "side": "SELL",
            "entry_price": 1.3,
            "stop_loss": 1.301,
            "take_profit": 1.295,
            "confidence": 0.6,
            "strategy": "test",
            "account_id": "B",
        }
        res = route_signal_dict(d)
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(len(executed), 1)


if __name__ == "__main__":
    unittest.main()


