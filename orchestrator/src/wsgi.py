import os
from app import create_app
import logging

config_name = os.getenv("FLASK_CONFIG", "config.development")
logger = logging.getLogger(__name__)
app = create_app(config_name)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))

    debug = app.config.get("DEBUG", False)

    logger.info(
        f"Starting Flask app in {config_name} mode and debug mode: {debug} in port {port}"
    )
    app.run(host="0.0.0.0", port=port)
