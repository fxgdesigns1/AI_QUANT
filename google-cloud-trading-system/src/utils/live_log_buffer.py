import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional


@dataclass
class LogRecordView:
    level: str
    message: str
    logger: str
    timestamp: float


class LiveLogBufferHandler(logging.Handler):
    """A lightweight in-memory ring buffer for recent log records."""

    def __init__(self, max_records: int = 500):
        super().__init__()
        self._records: Deque[LogRecordView] = deque(maxlen=max_records)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._records.append(
                LogRecordView(
                    level=record.levelname,
                    message=self.format(record),
                    logger=record.name,
                    timestamp=record.created,
                )
            )
        except Exception:
            # Never raise from logging handler
            pass

    def get_recent(self, limit: Optional[int] = 200) -> List[LogRecordView]:
        if limit is None or limit <= 0:
            return list(self._records)
        # Return most recent first
        return list(self._records)[-limit:][::-1]


