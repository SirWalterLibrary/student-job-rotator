"""Shared helpers for API routes."""
import functools
from datetime import date

from flask import current_app, request

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
    """No-op PIN guard for mutating routes (T08 makes it real)."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper
