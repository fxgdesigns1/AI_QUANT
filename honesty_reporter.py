from typing import Any

class _NoopHonestyReporter:
    def report(self, *args: Any, **kwargs: Any) -> None:
        pass

def get_honesty_reporter(strategy_name: str = "unknown") -> _NoopHonestyReporter:
    return _NoopHonestyReporter()




















