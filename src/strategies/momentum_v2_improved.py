# Lightweight placeholder implementation for MomentumV2Improved
# Provides a stable class that the registry can instantiate.
class MomentumV2Improved:
    def __init__(self, config: object = None):
        self.config = config or {}
        self.name = "Momentum V2 Improved (Placeholder)"
        self.daily_trades = 0

    def analyze_market(self, market_data):
        # Placeholder: no signals generated in this stub
        return []

    def generate_signals(self, data=None, pair=None):
        return []

    def reset_daily_tracking(self):
        self.daily_trades = 0

def get_momentum_trading_strategy() -> MomentumV2Improved:
    return MomentumV2Improved()
