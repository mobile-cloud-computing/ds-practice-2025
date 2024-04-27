import os
import sys
from pathlib import Path

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
APP_DIR = Path(FILE).resolve().parents[2]

sys.path.append(str(APP_DIR / "utils/config"))
sys.path.append(str(APP_DIR / "datastore/src"))
sys.path.append(str(APP_DIR / "utils/pb/order_executor"))
sys.path.append(str(APP_DIR / "utils/pb/datastore"))
sys.path.append(str(APP_DIR / "utils/pb/order_mq"))
sys.path.append(str(APP_DIR / "utils/pb"))
sys.path.append(str(APP_DIR / "utils/clients"))
sys.path.append(str(APP_DIR / "utils/linearizable"))

import log_configurator
import info

log_configurator.configure(
    info._INFO_LOG_PATH, info._ERROR_LOG_PATH, info._SERVICE_NAME
)
