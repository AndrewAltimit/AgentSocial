"""Structured logging configuration for bulletin board"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

import structlog
from structlog import get_logger


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logs"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(log_level: str = "INFO", json_logs: bool = True):
    """Configure structured logging for the application"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if json_logs
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)

    if json_logs:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def get_request_logger(request_id: str = None) -> structlog.BoundLogger:
    """Get a logger bound with request context"""
    logger = get_logger()
    if request_id:
        logger = logger.bind(request_id=request_id)
    return logger


def log_api_request(method: str, path: str, **kwargs):
    """Log API request details"""
    logger = get_logger()
    logger.info("api_request", method=method, path=path, **kwargs)


def log_api_response(
    method: str, path: str, status_code: int, duration_ms: float, **kwargs
):
    """Log API response details"""
    logger = get_logger()
    logger.info(
        "api_response",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_database_operation(operation: str, table: str, duration_ms: float, **kwargs):
    """Log database operation details"""
    logger = get_logger()
    logger.debug(
        "database_operation",
        operation=operation,
        table=table,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_external_api_call(
    service: str, endpoint: str, duration_ms: float, status_code: int = None, **kwargs
):
    """Log external API call details"""
    logger = get_logger()
    logger.info(
        "external_api_call",
        service=service,
        endpoint=endpoint,
        duration_ms=duration_ms,
        status_code=status_code,
        **kwargs,
    )
