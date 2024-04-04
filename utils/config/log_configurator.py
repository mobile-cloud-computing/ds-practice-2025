from logging.config import dictConfig


def configure(info_log_path, error_log_path):
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
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
