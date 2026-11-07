"""Shared helpers for API routes."""
import functools
from datetime import date

from flask import current_app, jsonify, request

from .auth import limiter, pin_ok
from .dates import central_today, parse_iso
from .errors import RotatorError


def request_today() -> date:
    """Today for the current request (?today= override when enabled, else Central)."""
    raw = request.args.get("today")
    if raw is not None and current_app.config.get("ALLOW_TODAY_OVERRIDE"):
        try:
            return parse_iso(raw)
        except ValueError:
            raise RotatorError("Invalid today parameter", 400)
    return central_today()


def json_body() -> dict:
    """The request's JSON body (400 if missing, invalid, or not an object)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise RotatorError("Body must be a JSON object.", 400)
    return data


def require_pin(fn):
    """Admin PIN guard: X-Admin-Pin header (401 if missing/wrong, 429 if blocked).

    Passes through when no ADMIN_PIN is configured. Wrong PINs count as
    failures against the shared per-IP FailureLimiter.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        key = request.remote_addr or "unknown"
        lim = limiter()
        if lim.blocked(key):
            return jsonify({"error": "Too many failed attempts, try again later"}), 429
        provided = request.headers.get("X-Admin-Pin")
        if not pin_ok(current_app.config, provided if provided is not None else ""):
            if provided is not None:
                lim.record(key)
            return jsonify({"error": "Teacher PIN required"}), 401
        return fn(*args, **kwargs)

    return wrapper
