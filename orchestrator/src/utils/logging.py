"""
Configure logging for the application.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, has_request_context, request


class RequestFormatter(logging.Formatter):
    """
    Formatter that adds request information to log records.
    """

    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
            record.method = request.method
        else:
            record.url = None
            record.remote_addr = None
            record.method = None

        return super().format(record)


def configure_logging(app=None):
    """
    Configure logging for the application.

    Args:
        app: Flask application to configure logging for (optional)
    """
    # Get configuration from app or use default values
    if app and isinstance(app, Flask):
        log_level = app.config.get("LOG_LEVEL", "INFO")
        log_format = app.config.get(
            "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_file = app.config.get("LOG_FILE", "logs/app.log")
        max_bytes = app.config.get("LOG_MAX_BYTES", 10485760)  # 10MB
        backup_count = app.config.get("LOG_BACKUP_COUNT", 5)
    else:
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_file = os.getenv("LOG_FILE", "logs/app.log")
        max_bytes = 10485760  # 10MB
        backup_count = 5

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers to prevent duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatters
    standard_formatter = logging.Formatter(log_format)
    request_formatter = RequestFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(remote_addr)s] - %(method)s %(url)s - %(message)s"
    )

    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(standard_formatter)
    logger.addHandler(console_handler)

    # Configure file handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(standard_formatter)
    logger.addHandler(file_handler)

    # Configure request logger if app is provided
    if app and isinstance(app, Flask):
        app_logger = app.logger
        app_logger.setLevel(log_level)

        # Remove existing handlers to prevent duplicate logs
        for handler in app_logger.handlers[:]:
            app_logger.removeHandler(handler)

        # Configure request handler
        request_handler = RotatingFileHandler(
            log_file.replace(".log", "-requests.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        request_handler.setLevel(log_level)
        request_handler.setFormatter(request_formatter)
        app_logger.addHandler(request_handler)

    logging.info("Logging configured")
