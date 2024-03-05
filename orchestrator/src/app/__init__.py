from flask import Flask
from flask_cors import CORS
from utils.logger import logger 
logs = logger.get_module_logger("init.py")


def create_app():
    app = Flask(__name__)
    CORS(app)
    logs.info("create_app triggered")

    from .routes import init_routes
    init_routes(app)

    return app