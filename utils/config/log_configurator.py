from logging.config import dictConfig
from pathlib import Path

def configure(info_log_path, error_log_path, service_name=None):
    service_name_fmt = f"[{service_name}]" if service_name else ""
    Path(info_log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(error_log_path).parent.mkdir(parents=True, exist_ok=True)
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "default": {
                    "format": f"[%(asctime)s] {service_name_fmt} %(levelname)s in %(module)s: %(message)s",
                },
                "access": {
                    "format": "%(message)s",
                },
            },
            "handlers": {
                "console": {
                    "level": "INFO",
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": error_log_path,
                    "maxBytes": 10000,
                    "backupCount": 10,
                    "delay": "True",
                    "level": "ERROR",
                },
                "info_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "access",
                    "filename": info_log_path,
                    "maxBytes": 10000,
                    "backupCount": 10,
                    "delay": "True",
                    "level": "INFO",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console", "info_file", "error_file"],
            },
        }
    )
