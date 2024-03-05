from pathlib import Path
import sys

# Add parent path to Python path to be able to import modules
current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))

from app import create_app
from utils.logger import logger 

logs = logger.get_module_logger("Run.py")
logs.info("Run.py started")
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0')