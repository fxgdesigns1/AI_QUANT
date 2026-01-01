class _NoopEarlyTrendDetector:
    def detect(self, *args, **kwargs):
        return None

def get_early_trend_detector() -> _NoopEarlyTrendDetector:
    return _NoopEarlyTrendDetector()
