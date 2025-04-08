"""
Default configuration that other configurations inherit from.
"""

import os

# flask settings
DEBUG = False
TESTING = False
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
LOG_MAX_BYTES = 10485760  # 10MB
LOG_BACKUP_COUNT = 5

# gRPC settings
GRPC_DEFAULT_TIMEOUT = int(os.getenv("GRPC_DEFAULT_TIMEOUT", "10"))
