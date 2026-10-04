"""Owned console + JSONL logger with recursive credential redaction."""
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import sys

from .serialization import canonical_json

SENSITIVE_KEYS = {"api_key", "groq_api_key", "authorization", "password", "secret", "token", "access_token", "refresh_token"}


def redact(value, secrets=()):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS or k.lower().endswith(("_api_key", "_secret", "_password")) else redact(v, secrets)
                for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [redact(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        return re.sub(r"gsk_[A-Za-z0-9]{20,}", "[REDACTED]", value)
    return value


class ExperimentLogger:
    """Do not change root/MVP logging; close owned handlers with a context manager."""

    def __init__(self, path: Path, experiment_id: str, *, level="INFO", secrets=(), stream=None):
        self.experiment_id = experiment_id
        self.secrets = tuple(secrets)
        self.closed = False
        self.logger = logging.Logger(f"research.{experiment_id}", level=level)
        self.logger.propagate = False
        file_handler = logging.FileHandler(path, mode="a", encoding="utf-8")
        console_handler = logging.StreamHandler(sys.stderr if stream is None else stream)
        for handler in (file_handler, console_handler):
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

    def emit(self, event: str, *, level="INFO", **fields):
        if self.closed:
            raise RuntimeError("Logger is closed")
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported log level")
        if not event.strip():
            raise ValueError("Event must be nonempty")
        record = {"schema_version": "1.0", "timestamp": datetime.now(timezone.utc).isoformat(),
                  "experiment_id": self.experiment_id, "level": level, "event": event, "fields": fields}
        message = canonical_json(redact(record, self.secrets))
        self.logger.log(getattr(logging, level), message)

    def close(self):
        for handler in list(self.logger.handlers):
            handler.flush()
            handler.close()
            self.logger.removeHandler(handler)
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
