import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "route",
            "status",
            "duration_ms",
            "error_code",
            "exception_type",
            "provider",
        ):
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        # No exception message/traceback: provider exceptions can contain credentials.
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    logger = logging.getLogger("aurora")
    logger.setLevel(level)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
