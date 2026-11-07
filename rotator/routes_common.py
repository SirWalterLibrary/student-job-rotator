"""Shared helpers for API routes."""
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
