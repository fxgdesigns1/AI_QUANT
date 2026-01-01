from datetime import datetime
from src.core.account_orchestrator import get_account_orchestrator
from src.core.order_manager import TradeSignal, OrderSide

def main():
    orchestrator = get_account_orchestrator()
    # Prepare two in-memory executors to capture routed signals
    routed_signals = {"acct1": [], "acct2": []}

    def exec_acct1(sig):
        routed_signals["acct1"].append(sig)
        return "ok-acct1"

    def exec_acct2(sig):
        routed_signals["acct2"].append(sig)
        return "ok-acct2"

    # Register two accounts
    orchestrator.register_account("acct1", accounts=None, executor=exec_acct1)
    orchestrator.register_account("acct2", accounts=None, executor=exec_acct2)

    # Create two signals with distinct account_ids
    sig1 = TradeSignal(
        instrument="GBP_USD",
        side=OrderSide.BUY,
        units=100000,
        entry_price=1.2500,
        stop_loss=1.2480,
        take_profit=1.2525,
        confidence=0.8,
        timestamp=datetime.utcnow(),
        strategy_name="smoke-test",
        account_id="acct1"
    )
    sig2 = TradeSignal(
        instrument="EUR_USD",
        side=OrderSide.SELL,
        units=100000,
        entry_price=1.1000,
        stop_loss=1.1015,
        take_profit=1.0985,
        confidence=0.75,
        timestamp=datetime.utcnow(),
        strategy_name="smoke-test",
        account_id="acct2"
    )

    # Route signals
    orchestrator.route_signal(sig1)
    orchestrator.route_signal(sig2)

    print("Routed signals per account:")
    print("acct1:", len(routed_signals["acct1"]), "signal(s)")
    print("acct2:", len(routed_signals["acct2"]), "signal(s)")
    if routed_signals["acct1"] and routed_signals["acct1"][0].instrument == "GBP_USD":
        print("acct1 signal instrument OK")
    if routed_signals["acct2"] and routed_signals["acct2"][0].instrument == "EUR_USD":
        print("acct2 signal instrument OK")

if __name__ == "__main__":
    main()


