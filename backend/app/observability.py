"""Privacy-safe structured logging helpers."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format records as one-line JSON without request bodies or credentials."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_logging() -> None:
    """Install JSON formatting only when the application owns the root handler."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(JSONFormatter())
    root.setLevel(logging.INFO)


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
