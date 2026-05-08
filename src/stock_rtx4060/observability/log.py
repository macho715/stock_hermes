"""Structured logging via loguru with JSONL sink and stdlib bridge."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

try:
    from loguru import logger as _loguru_logger

    _HAS_LOGURU = True
except ImportError:  # pragma: no cover - dev environments
    _loguru_logger = None
    _HAS_LOGURU = False


_CONFIGURED = False


def _intercept_stdlib() -> None:
    if not _HAS_LOGURU:
        return

    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = _loguru_logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            _loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


def configure_logging(
    *,
    level: str | None = None,
    log_dir: str | os.PathLike[str] | None = None,
    json_sink: bool = True,
) -> None:
    """Configure loguru sinks. Idempotent across calls."""
    global _CONFIGURED
    if _CONFIGURED or not _HAS_LOGURU:
        return
    level = level or os.environ.get("STOCK1901_LOG_LEVEL", "INFO")
    _loguru_logger.remove()
    _loguru_logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    if json_sink:
        log_dir_path = Path(log_dir or "logs")
        log_dir_path.mkdir(parents=True, exist_ok=True)
        _loguru_logger.add(
            log_dir_path / "app.jsonl",
            level=level,
            serialize=True,
            rotation="100 MB",
            retention="30 days",
            enqueue=True,
        )
    _intercept_stdlib()
    _CONFIGURED = True


def get_logger(name: str | None = None) -> Any:
    """Return a logger bound to ``name``. Falls back to stdlib if loguru missing."""
    if _HAS_LOGURU:
        configure_logging()
        return _loguru_logger.bind(component=name or "stock_rtx4060") if name else _loguru_logger
    return logging.getLogger(name or "stock_rtx4060")
