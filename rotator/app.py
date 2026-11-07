"""Flask application factory."""
import os
import threading

from flask import Flask, current_app, g, jsonify, request, send_from_directory

from .config import load_config
from .db import connect, init_db
from .errors import RotatorError

# The freeze step writes rows, so two concurrent /api requests could both try to
# store the same auto assignment (UNIQUE date, student). Serialize /api requests;
# for a single classroom this costs nothing.
_API_LOCK = threading.Lock()


def create_app(config: dict | None = None) -> Flask:
    """Build the Khidmah Roster Flask app from config (dict of env overrides)."""
    cfg = load_config(config)
    if cfg["APP_ENV"] == "production" and not cfg["ADMIN_PIN"]:
        raise RuntimeError("ADMIN_PIN must be set when APP_ENV=production")
    os.makedirs(cfg["DATA_DIR"], exist_ok=True)

    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(cfg)

    bootstrap = connect(os.path.join(cfg["DATA_DIR"], "rotator.db"))
    try:
        init_db(bootstrap)
    finally:
        bootstrap.close()

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

    @app.before_request
    def acquire_api_lock():
        """Hold the request lock for every /api request so DB writes never race."""
        if request.path.startswith("/api"):
            _API_LOCK.acquire()
            g.api_lock = True

    @app.teardown_appcontext
    def close_conn(err):
        """Close the per-request database connection and release the request lock."""
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()
        if getattr(g, "api_lock", False):
            g.api_lock = False
            _API_LOCK.release()

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

    from .routes_actions import bp as actions_bp   # lazy: routes import get_conn from here
    from .routes_admin import bp as admin_bp
    from .routes_roster import bp as roster_bp
    from .routes_schedule import bp as schedule_bp

    app.register_blueprint(roster_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(actions_bp)
    app.register_blueprint(admin_bp)

    if cfg["TRUST_PROXY"]:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    return app


def get_conn():
    """Return the current request's database connection, creating it on first use."""
    if not hasattr(g, "conn"):
        path = os.path.join(current_app.config["DATA_DIR"], "rotator.db")
        g.conn = connect(path)
    return g.conn
