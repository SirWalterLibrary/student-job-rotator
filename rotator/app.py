"""Flask application factory."""
import os

from flask import Flask, jsonify, request, send_from_directory

from .config import load_config
from .errors import RotatorError


def create_app(config: dict | None = None) -> Flask:
    """Build the Khidmah Roster Flask app from config (dict of env overrides)."""
    cfg = load_config(config)
    if cfg["APP_ENV"] == "production" and not cfg["ADMIN_PIN"]:
        raise RuntimeError("ADMIN_PIN must be set when APP_ENV=production")
    os.makedirs(cfg["DATA_DIR"], exist_ok=True)

    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(cfg)

    @app.errorhandler(RotatorError)
    def handle_rotator_error(err: RotatorError):
        """Return RotatorError as JSON with its status code."""
        return jsonify({"error": err.message}), err.status

    @app.errorhandler(404)
    def handle_not_found(err):
        """Return unknown /api/* routes as a JSON 404; leave others to Flask."""
        if request.path.startswith("/api"):
            return jsonify({"error": "Not found"}), 404
        return err, 404

    @app.errorhandler(500)
    def handle_server_error(err):
        """Return a JSON 500."""
        return jsonify({"error": "Server error"}), 500

    @app.after_request
    def no_cache(response):
        """Mark every /api/ response as non-cacheable."""
        if request.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        """Liveness probe."""
        return jsonify({"ok": True})

    @app.get("/")
    def index():
        """Serve the single-page frontend."""
        return send_from_directory(app.static_folder, "index.html")

    return app
