import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime

# Thread-safe and async-safe request-scoped storage for the active Trace ID
trace_var: ContextVar[str] = ContextVar("trace_id", default="no-trace")


def get_trace_id() -> str:
    return trace_var.get()


def set_trace_id(trace_id: str) -> str:
    return trace_var.set(trace_id)


class StructuredFormatter(logging.Formatter):
    """
    State-of-the-art dual-mode formatter:
    - Production (LOG_FORMAT=json or ENV=production): valid, structured single-line JSON log.
    - Development: highly readable ANSI color-coded logs.
    """

    def __init__(self):
        super().__init__()
        env = os.getenv("ENV", "development")
        log_format = os.getenv("LOG_FORMAT", "text")
        self.is_json = log_format == "json" or env == "production"

    def format(self, record):
        trace_id = trace_var.get()
        record.trace_id = trace_id

        if self.is_json:
            log_record = {
                "time": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname.lower(),
                "trace_id": trace_id,
                "message": record.getMessage(),
                "module": record.module,
                "filename": record.filename,
                "lineno": record.lineno,
            }
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_record)
        else:
            time_str = f"\033[90m[{datetime.now().strftime('%H:%M:%S')}]\033[0m"
            trace_str = f"\033[36m[{trace_id[:13]}]\033[0m"

            level_colors = {
                "DEBUG": "\033[34m[DEBUG]\033[0m",
                "INFO": "\033[32m[INFO] \033[0m",
                "WARNING": "\033[33m[WARN] \033[0m",
                "ERROR": "\033[31m[ERROR]\033[0m",
                "CRITICAL": "\033[35m[CRIT] \033[0m",
            }

            lvl = level_colors.get(record.levelname, f"[{record.levelname}]")
            msg = record.getMessage()

            if record.levelname in ["WARNING", "ERROR", "CRITICAL"]:
                color = "\033[33m" if record.levelname == "WARNING" else "\033[31m"
                msg = f"{color}{msg}\033[0m"

            exc = ""
            if record.exc_info:
                exc = "\n" + self.formatException(record.exc_info)

            return f"{time_str} {lvl} {trace_str} {msg}{exc}"


def setup_logging():
    """
    Configures the root logging handler to capture standard and library logs.
    """
    root = logging.getLogger()

    # Remove existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    # Set global log level
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    root.setLevel(log_level)

    # Suppress noise from dependencies
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("db").setLevel(logging.WARNING)
