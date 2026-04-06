"""Logging support for debugging."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from miru.config_manager import LOG_DIR, ensure_config_dir


class Logger:
    """Logger for miru operations."""

    def __init__(self, enabled: bool = False, verbose: bool = False):
        self.enabled = enabled
        self.verbose = verbose
        self.log_file: Path | None = None

    def enable_file_logging(self) -> None:
        """Enable logging to file."""
        ensure_config_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"miru_{timestamp}.log"

    def log(self, level: str, message: str, data: dict[str, Any] | None = None) -> None:
        """Log a message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
            data: Optional data to include
        """
        if not self.enabled:
            return

        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
        }
        if data:
            log_entry["data"] = data

        if self.verbose:
            to_stderr = f"[{level}] {message}"
            if data:
                to_stderr += f" {json.dumps(data)}"
            print(to_stderr, file=sys.stderr)

        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception:
                pass

    def debug(self, message: str, data: dict[str, Any] | None = None) -> None:
        """Log debug message."""
        self.log("DEBUG", message, data)

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        """Log info message."""
        self.log("INFO", message, data)

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        """Log warning message."""
        self.log("WARNING", message, data)

    def error(self, message: str, data: dict[str, Any] | None = None) -> None:
        """Log error message."""
        self.log("ERROR", message, data)

    def request(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Log HTTP request."""
        self.debug(
            f"HTTP {method} {url}",
            {
                "method": method,
                "url": url,
                "body": body,
                "headers": headers,
            },
        )

    def response(
        self,
        status: int,
        url: str,
        body: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Log HTTP response."""
        self.debug(
            f"HTTP {status} {url}",
            {
                "status": status,
                "url": url,
                "body": body,
                "duration_ms": duration_ms,
            },
        )


_logger: Logger | None = None


def get_logger(enabled: bool = False, verbose: bool = False) -> Logger:
    """Get or create global logger."""
    global _logger
    if _logger is None:
        _logger = Logger(enabled=enabled, verbose=verbose)
    else:
        _logger.enabled = enabled or _logger.enabled
        _logger.verbose = verbose or _logger.verbose
    return _logger


def enable_logging(verbose: bool = False) -> None:
    """Enable logging globally."""
    global _logger
    _logger = Logger(enabled=True, verbose=verbose)
    _logger.enable_file_logging()
