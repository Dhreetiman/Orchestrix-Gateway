import logging
import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

# Patterns that should never appear unredacted in logs.
# Order matters: more-specific patterns first.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b"), "sk-ant-***REDACTED***"),  # Anthropic
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "sk-***REDACTED***"),          # OpenAI
    (re.compile(r"\bogw_[A-Za-z0-9_-]{16,}\b"), "ogw_***REDACTED***"),        # Gateway keys
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{16,}", re.IGNORECASE), r"\1***REDACTED***"),
)


def _redact(text: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _redact_event(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Walk string values in the event dict and redact known secret shapes."""
    for k, v in list(event_dict.items()):
        if isinstance(v, str) and len(v) > 8:
            event_dict[k] = _redact(v)
    return event_dict


def _add_app_context(_: Any, __: str, event_dict: EventDict) -> EventDict:
    event_dict.setdefault("app", "orchestrix-gateway")
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging for JSON output suitable for shipping to a log collector."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_app_context,
        _redact_event,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logs (uvicorn, sqlalchemy) through structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
