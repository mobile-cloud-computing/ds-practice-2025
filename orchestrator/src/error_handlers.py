from flask import jsonify


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return jsonify(
            {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}
        ), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify(
            {"error": {"code": "METHOD_NOT_ALLOWED", "message": "Method not allowed"}}
        ), 405
