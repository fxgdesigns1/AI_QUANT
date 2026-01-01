from typing import Any, Dict

class _NoopLossLearner:
    def record_loss(self, **kwargs: Any) -> None:
        pass
    def record_win(self, **kwargs: Any) -> None:
        pass
    def get_performance_summary(self) -> Dict[str, Any]:
        return {}
    def get_avoidance_list(self) -> Dict[str, Any]:
        return {}

def get_loss_learner(strategy_name: str = "unknown") -> _NoopLossLearner:
    return _NoopLossLearner()
